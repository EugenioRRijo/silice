"""Subir un `.db` como carpeta de trabajo por la API (BCP-2; diseño §4.4, §9 C2; B12 a B15, S5, S6,
S8 y S9).

`POST /v1/casos/subida`, `multipart/form-data` con `archivo` (obligatorio, uno solo) y `nombre`
(opcional, hasta 200 caracteres); `CAMBIAR_CASO`; 201 `{nombre, ruta_relativa, aviso}`. Todo o nada:
un archivo rechazado no deja ni un byte en la carpeta de datos (árbol con `os.walk` antes y
después). Oráculos a mano: mensajes del diseño con sus tildes, el de 413 del tope de la API
(`api/proteccion.py`), la ficha de la base 0.5.0 y los roles de `tests/fixtures/sesion_web.py`.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from operacion import config
from tests.fixtures import bases_prueba
from tests.fixtures.carpetas_trabajo import HOSTILES, arbol, base_minima
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

RUTA = "/v1/casos/subida"
MENSAJE_CON_CLAVE = (
    "Con la clave de API se trabaja en el caso del proceso (APU_BASE); el caso se elige por "
    "sesión desde la interfaz."
)
MENSAJE_CSRF = "Falta la comprobación anti-CSRF de la sesión o no coincide."
MENSAJE_NO_VALIDO = "El archivo no es una carpeta de trabajo de Sílice válida: no se guardó."
MENSAJE_RESERVADO = "Ese nombre está reservado para la demostración."
FORMA_SUBIDA = (
    "Envíe un solo archivo .db en el campo «archivo» y, si quiere, un nombre de hasta 200 "
    "caracteres."
)
AVISO_MIGRADA = "Se actualizó el archivo a la versión actual de Sílice; quedó un respaldo previo."
#: El del tope del cuerpo de la API (`LimiteDeCuerpo._rechazar`), copiado a mano.
MENSAJE_CUERPO = "El cuerpo de la peticion excede el maximo de 20 MiB."


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_api_subida")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "minima": base_minima(carpeta / "minima.db"),
    }


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    caso_web.olvidar_todo()
    yield config.carpeta_datos()
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _sin_instalacion(vista: dict[str, int]) -> dict[str, int]:
    return {k: v for k, v in vista.items() if not k.startswith("instalacion.db")}


def _subir(navegador: TestClient, ficha: str, contenido: bytes, archivo="obra.db", **datos):
    return navegador.post(
        RUTA,
        files={"archivo": (archivo, contenido, "application/octet-stream")},
        data=datos,
        headers=protegida(ficha),
    )


def _nombres() -> list[str]:
    carpeta = config.carpeta_casos()
    return sorted(p.name for p in carpeta.iterdir()) if carpeta.is_dir() else []


# --- éxito (B13, B14) --------------------------------------------------------------------------


@pytest.mark.parametrize("login", ["ana", "admin"])
def test_subir_una_base_valida_la_publica(
    login: str, _plantillas: dict[str, Path], _entorno: Path
) -> None:
    navegador, ficha = con_cuenta(app, login)
    respuesta = _subir(navegador, ficha, _plantillas["minima"].read_bytes())
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json() == {
        "nombre": "obra.db",
        "ruta_relativa": "casos/obra.db",
        "aviso": None,
    }
    assert respuesta.headers["cache-control"] == "no-store"
    lista = navegador.get("/v1/casos").json()["casos"]
    assert {"nombre": "obra.db", "ruta_relativa": "casos/obra.db"} in lista
    assert set(_sin_instalacion(arbol(_entorno))) == {"casos", "casos/obra.db"}  # sin cuarentena


def test_el_nombre_del_formulario_gana_al_del_archivo(_plantillas: dict[str, Path]) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _subir(navegador, ficha, _plantillas["minima"].read_bytes(), nombre="Obra Sur")
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["nombre"] == "Obra Sur.db"


def test_el_nombre_del_archivo_con_rutas_solo_aporta_su_ultima_parte(
    _plantillas: dict[str, Path], _entorno: Path
) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _subir(navegador, ficha, _plantillas["minima"].read_bytes(), "..\\..\\evil.db")
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["nombre"] == "evil.db"
    assert _nombres() == ["evil.db"]
    assert not (_entorno.parent / "evil.db").exists() and not (_entorno / "evil.db").exists()


def test_subir_una_base_0_5_0_avisa_que_la_migro(tmp_path: Path) -> None:
    origen = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _subir(navegador, ficha, origen.read_bytes(), "antigua.db")
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["aviso"] == AVISO_MIGRADA
    esperado = bases_prueba.ficha("0.5.0")["bases"]["demo.db"]
    ruta = config.carpeta_casos() / "antigua.db"
    assert bases_prueba.diferencias_con_ficha(ruta, esperado) == []
    assert any(config.carpeta_respaldos().iterdir())


# --- rechazos sin rastro (B15, S5, S6) ------------------------------------------------------------


@pytest.mark.parametrize("hostil", sorted(HOSTILES))
def test_un_archivo_hostil_no_deja_rastro(
    hostil: str, _plantillas: dict[str, Path], tmp_path: Path, _entorno: Path
) -> None:
    contenido = HOSTILES[hostil](tmp_path / "hostil.db", _plantillas["minima"]).read_bytes()
    navegador, ficha = con_cuenta(app, "ana")
    antes = arbol(_entorno)
    respuesta = _subir(navegador, ficha, contenido, "hostil.db")
    assert respuesta.status_code == 422, respuesta.text
    if hostil == "revision_desconocida":
        assert respuesta.json() == {
            "detalle": "Esta base (hostil.db) es de una versión más nueva de Sílice (revisión "
            "zzz). Instale esa versión o restaure el respaldo previo; no se modificó."
        }
    elif hostil == "texto":
        assert respuesta.json() == {
            "detalle": "«hostil.db» no es una base de Sílice (SQLite): no se guardó."
        }
    else:
        assert respuesta.json() == {"detalle": MENSAJE_NO_VALIDO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert arbol(_entorno) == antes


def test_un_archivo_de_mas_de_20_mib_es_413_sin_rastro(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    antes = arbol(_entorno)
    respuesta = _subir(navegador, ficha, b"\x00" * (20 * 1024 * 1024 + 1), "grande.db")
    assert respuesta.status_code == 413
    assert respuesta.json() == {"detalle": MENSAJE_CUERPO}
    assert arbol(_entorno) == antes


def test_un_content_length_mentiroso_es_413_sin_escribir(_entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    cuerpo = (
        b'--limite\r\nContent-Disposition: form-data; name="archivo"; filename="g.db"\r\n'
        b"Content-Type: application/octet-stream\r\n\r\n"
        + b"\x00" * (21 * 1024 * 1024)
        + b"\r\n--limite--\r\n"
    )
    antes = arbol(_entorno)
    respuesta = navegador.post(
        RUTA,
        content=cuerpo,
        headers={
            **protegida(ficha),
            "Content-Type": "multipart/form-data; boundary=limite",
            "Content-Length": "10",
        },
    )
    assert respuesta.status_code == 413
    assert arbol(_entorno) == antes


@pytest.mark.parametrize("nombre", ["..\\x", "C:\\x", "con", "x:y", "a/b"])
def test_un_nombre_elegido_hostil_es_422(
    nombre: str, _plantillas: dict[str, Path], _entorno: Path
) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    antes = arbol(_entorno)
    respuesta = _subir(navegador, ficha, _plantillas["minima"].read_bytes(), nombre=nombre)
    assert respuesta.status_code == 422, respuesta.text
    assert arbol(_entorno) == antes


def test_el_nombre_de_la_demostracion_esta_reservado(_plantillas: dict[str, Path]) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _subir(navegador, ficha, _plantillas["minima"].read_bytes(), "Demostracion.db")
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_RESERVADO})


def test_sin_parte_archivo_o_con_dos_es_422(_plantillas: dict[str, Path]) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    contenido = _plantillas["minima"].read_bytes()
    sin_archivo = navegador.post(RUTA, data={"nombre": "x"}, headers=protegida(ficha))
    assert (sin_archivo.status_code, sin_archivo.json()) == (422, {"detalle": FORMA_SUBIDA})
    dos = navegador.post(
        RUTA,
        files=[("archivo", ("a.db", contenido)), ("archivo", ("b.db", contenido))],
        headers=protegida(ficha),
    )
    assert (dos.status_code, dos.json()) == (422, {"detalle": FORMA_SUBIDA})
    texto = navegador.post(RUTA, data={"archivo": "no es un archivo"}, headers=protegida(ficha))
    assert texto.status_code == 422
    assert _nombres() == []


def test_un_nombre_largo_es_422_sin_eco(_plantillas: dict[str, Path]) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    largo = "secreto" * 40
    respuesta = _subir(navegador, ficha, _plantillas["minima"].read_bytes(), nombre=largo)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": FORMA_SUBIDA})
    assert "secreto" not in respuesta.text


def test_un_nombre_ya_usado_es_409_y_no_pisa(_plantillas: dict[str, Path]) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    contenido = _plantillas["minima"].read_bytes()
    assert _subir(navegador, ficha, contenido, "Obra.db").status_code == 201
    huella = (config.carpeta_casos() / "Obra.db").read_bytes()
    respuesta = _subir(navegador, ficha, b"SQLite format 3\x00" + b"x" * 100, "OBRA.db")
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "Ya hay una carpeta de trabajo llamada Obra.db: cambie el nombre antes de "
        "subirla."
    }
    assert (config.carpeta_casos() / "Obra.db").read_bytes() == huella


def test_dos_subidas_simultaneas_del_mismo_nombre_dan_201_y_409(
    _plantillas: dict[str, Path],
) -> None:
    contenido = _plantillas["minima"].read_bytes()
    navegadores = [con_cuenta(app, "ana") for _ in range(2)]
    barrera = threading.Barrier(2)
    estados: list[int] = []

    def subir(navegador: TestClient, ficha: str) -> None:
        barrera.wait()
        estados.append(_subir(navegador, ficha, contenido, "Gemela.db").status_code)

    hilos = [threading.Thread(target=subir, args=par) for par in navegadores]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert sorted(estados) == [201, 409]
    assert _nombres() == ["Gemela.db"]
    assert not (config.carpeta_datos() / "cuarentena").exists()


# --- acceso (B12, S8) ----------------------------------------------------------------------------


def test_quien_revisa_no_sube(_plantillas: dict[str, Path], _entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "rita")
    antes = arbol(_entorno)
    respuesta = _subir(navegador, ficha, _plantillas["minima"].read_bytes())
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_PERMISO})
    assert arbol(_entorno) == antes


def test_sin_sesion_401_con_clave_409_y_sin_csrf_403(_plantillas: dict[str, Path]) -> None:
    contenido = _plantillas["minima"].read_bytes()
    archivos = {"archivo": ("obra.db", contenido)}
    assert cliente(app).post(RUTA, files=archivos).status_code == 401
    con_clave = cliente(app).post(RUTA, files=archivos, headers={CABECERA: crear_clave_de_prueba()})
    assert (con_clave.status_code, con_clave.json()) == (409, {"detalle": MENSAJE_CON_CLAVE})
    navegador, _ = con_cuenta(app, "ana")
    sin_csrf = navegador.post(RUTA, files=archivos, headers={"Origin": "http://127.0.0.1:8000"})
    assert (sin_csrf.status_code, sin_csrf.json()) == (403, {"detalle": MENSAJE_CSRF})
    assert _nombres() == []
