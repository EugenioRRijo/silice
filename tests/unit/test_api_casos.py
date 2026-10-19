"""Caso por sesión web y proyectos del caso (RM-2 y `GET /v1/proyectos`; ola 0a de la sesión 2b).

Contrato del plan (`docs/planes/PLAN_SESION_2B_MIGRACION.md` §4, ola 0a):

- `GET /v1/casos` → `{actual: {nombre, ruta_relativa}, casos: [{nombre, ruta_relativa}]}` sin rutas
  absolutas; cualquier rol con sesión, o la clave de API (que ve el caso del proceso).
- `POST /v1/casos/actual` `{nombre}` → 200 con el actual; 403 sin `CAMBIAR_CASO` o sin CSRF;
  404 si no está en la carpeta de casos; 422 si el nombre lleva rutas o `..`.
- La elección vive en memoria del proceso por ficha; al salir o expirar se olvida; la clave de
  API sigue usando el caso del proceso.
- `GET /v1/proyectos` → `[{codigo, nombre, version_vigente, version_codigo, actualizado}]`.

Oráculos: las carpetas y archivos los arma la prueba (nombres, orden y rutas relativas escritos a
mano); la versión vigente se lee con `sqlite3` directo del archivo, sin SQLAlchemy ni `core`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from aplicacion.proyectos import crear_proyecto_nuevo
from operacion import config
from operacion.base_datos import preparar_base
from operacion.instalacion import sesion_de_instalacion
from scripts.seed import NOMBRE_PROYECTO
from seguridad import sesiones
from seguridad.modelo import Sesion
from tests.fixtures import bases_prueba
from tests.fixtures.base_con_pendiente import guardar_base_con_pendiente
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    entrar,
    ficha_de,
    plantilla_con_cuentas,
    protegida,
)


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    """Una instalación con cuentas y dos casos vacíos al día, creados una vez por módulo."""
    carpeta = tmp_path_factory.mktemp("plantillas_casos")
    casos = {}
    for nombre in ("Obra Norte.db", "anexo.db", "silice.db"):
        casos[nombre] = carpeta / nombre
        preparar_base(casos[nombre])
    return {"instalacion": plantilla_con_cuentas(carpeta), **casos}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalación de la prueba, la carpeta de casos con tres casos y ningún caso elegido."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in ("Obra Norte.db", "anexo.db", "silice.db"):
        (carpeta / nombre).write_bytes(_plantillas[nombre].read_bytes())
    (carpeta / "notas.txt").write_text("no es un caso", encoding="utf-8")
    caso_web.olvidar_todo()
    yield carpeta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _caso(nombre: str) -> dict[str, str]:
    return {"nombre": nombre, "ruta_relativa": f"casos/{nombre}"}


#: Por nombre, sin distinguir mayúsculas.
TODOS = [_caso("anexo.db"), _caso("Obra Norte.db"), _caso("silice.db")]


def _elegir(navegador: TestClient, ficha: str, nombre: str, **extra):
    cabeceras = {**protegida(ficha), **extra.pop("headers", {})}
    return navegador.post("/v1/casos/actual", json={"nombre": nombre}, headers=cabeceras, **extra)


# --- GET /v1/casos ---------------------------------------------------------------------------


def test_sin_sesion_ni_clave_da_401() -> None:
    assert cliente(app).get("/v1/casos").status_code == 401


@pytest.mark.parametrize("login", ["admin", "ana", "rita"])
def test_cualquier_rol_ve_la_lista_y_el_caso_por_defecto(login: str, _entorno: Path) -> None:
    navegador, _ = con_cuenta(app, login)
    respuesta = navegador.get("/v1/casos")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"actual": _caso("silice.db"), "casos": TODOS}
    assert str(config.carpeta_datos()) not in respuesta.text  # sin rutas absolutas
    assert _entorno.as_posix() not in respuesta.text


def test_con_clave_de_api_ve_el_caso_del_proceso(monkeypatch: pytest.MonkeyPatch) -> None:
    respuesta = cliente(app).get("/v1/casos", headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.status_code == 200
    assert respuesta.json()["actual"] == _caso("silice.db")
    otro = config.carpeta_casos() / "anexo.db"
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{otro.as_posix()}")
    respuesta = cliente(app).get("/v1/casos", headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.json()["actual"] == _caso("anexo.db")


def test_un_caso_fuera_de_la_carpeta_de_datos_solo_muestra_su_nombre(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fuera = tmp_path / "otra carpeta" / "externo.db"
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{fuera.as_posix()}")
    respuesta = cliente(app).get("/v1/casos", headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.json()["actual"] == {"nombre": "externo.db", "ruta_relativa": "externo.db"}
    assert tmp_path.as_posix() not in respuesta.text and str(tmp_path) not in respuesta.text


def test_sin_carpeta_de_casos_la_lista_queda_vacia(_entorno: Path) -> None:
    for archivo in _entorno.iterdir():
        archivo.unlink()
    _entorno.rmdir()
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get("/v1/casos").json() == {"actual": _caso("silice.db"), "casos": []}


# --- POST /v1/casos/actual -------------------------------------------------------------------


@pytest.mark.parametrize("login", ["ana", "admin"])
def test_quien_puede_cambiar_de_caso_lo_elige_para_su_ficha(login: str) -> None:
    navegador, ficha = con_cuenta(app, login)
    respuesta = _elegir(navegador, ficha, "anexo.db")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == _caso("anexo.db")
    assert navegador.get("/v1/casos").json()["actual"] == _caso("anexo.db")


def test_el_nombre_sin_extension_tambien_vale() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "Obra Norte").json() == _caso("Obra Norte.db")


def test_revisa_no_puede_cambiar_de_caso() -> None:
    navegador, ficha = con_cuenta(app, "rita")
    respuesta = _elegir(navegador, ficha, "anexo.db")
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")


def test_sin_csrf_no_cambia() -> None:
    navegador, _ = con_cuenta(app, "ana")
    respuesta = navegador.post(
        "/v1/casos/actual", json={"nombre": "anexo.db"}, headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert respuesta.status_code == 403
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")


def test_un_caso_que_no_esta_en_la_carpeta_da_404() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    for nombre in ("no-existe.db", "notas.txt", "notas"):
        respuesta = _elegir(navegador, ficha, nombre)
        assert respuesta.status_code == 404, (nombre, respuesta.text)
        assert "detalle" in respuesta.json()
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")


@pytest.mark.parametrize(
    "nombre",
    ["../instalacion.db", "..", "casos/anexo.db", "casos\\anexo.db", "C:\\x\\anexo.db",
     "/tmp/anexo.db", "\\\\servidor\\c\\anexo.db", "anexo.db:flujo", "", "   "],
)
def test_un_nombre_con_rutas_da_422_sin_cambiar(nombre: str, _entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _elegir(navegador, ficha, nombre)
    assert respuesta.status_code == 422, respuesta.text
    assert str(_entorno) not in respuesta.text and _entorno.as_posix() not in respuesta.text
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")


def test_un_cuerpo_invalido_da_422() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    for cuerpo in ({}, {"nombre": 7}, {"nombre": "x" * 300}):
        respuesta = navegador.post("/v1/casos/actual", json=cuerpo, headers=protegida(ficha))
        assert respuesta.status_code == 422, cuerpo


def test_un_caso_que_no_se_puede_preparar_da_503_y_no_queda_elegido(_entorno: Path) -> None:
    bases_prueba.crear_base_futura(_entorno / "futura.db")
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _elegir(navegador, ficha, "futura.db")
    assert respuesta.status_code == 503
    assert "versión más nueva" in respuesta.json()["detalle"]
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")


def test_con_clave_de_api_no_se_elige_caso() -> None:
    respuesta = cliente(app).post(
        "/v1/casos/actual", json={"nombre": "anexo.db"}, headers={CABECERA: crear_clave_de_prueba()}
    )
    assert respuesta.status_code == 409
    assert "detalle" in respuesta.json()


# --- un caso por ficha -----------------------------------------------------------------------


def test_cada_ficha_trabaja_en_su_caso_y_la_clave_en_el_del_proceso(_entorno: Path) -> None:
    crear_proyecto_nuevo(_entorno / "anexo.db", "Torre del anexo")
    crear_proyecto_nuevo(_entorno / "silice.db", "Torre por defecto")
    uno, ficha_uno = con_cuenta(app, "ana")
    dos, _ = con_cuenta(app, "ana")  # la misma persona en otro navegador
    assert _elegir(uno, ficha_uno, "anexo.db").status_code == 200
    nombres = lambda navegador, **extra: [  # noqa: E731
        p["nombre"] for p in navegador.get("/v1/proyectos", **extra).json()
    ]
    assert nombres(uno) == ["Torre del anexo"]
    assert nombres(dos) == ["Torre por defecto"]
    assert nombres(cliente(app), headers={CABECERA: crear_clave_de_prueba()}) == [
        "Torre por defecto"
    ]
    assert uno.get("/v1/casos").json()["actual"] == _caso("anexo.db")
    assert dos.get("/v1/casos").json()["actual"] == _caso("silice.db")


def test_una_clave_de_api_con_la_cookie_de_un_navegador_usa_el_caso_del_proceso(
    _entorno: Path,
) -> None:
    crear_proyecto_nuevo(_entorno / "anexo.db", "Torre del anexo")
    navegador, ficha = con_cuenta(app, "ana")
    _elegir(navegador, ficha, "anexo.db")
    respuesta = navegador.get("/v1/proyectos", headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.status_code == 200 and respuesta.json() == []


def test_salir_olvida_el_caso_elegido() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    _elegir(navegador, ficha, "anexo.db")
    assert caso_web.elegido(sesiones.huella_de(ficha)) is not None
    assert navegador.delete("/v1/sesion", headers=protegida(ficha)).status_code == 204
    assert caso_web.elegido(sesiones.huella_de(ficha)) is None
    respuesta = entrar(navegador, "ana")
    assert ficha_de(respuesta) != ficha
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")


def test_volver_a_entrar_no_hereda_el_caso_de_la_ficha_anterior() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    _elegir(navegador, ficha, "anexo.db")
    entrar(navegador, "rita")  # otra persona en el mismo navegador
    assert caso_web.elegido(sesiones.huella_de(ficha)) is None
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")


def test_una_ficha_expirada_olvida_su_caso() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    _elegir(navegador, ficha, "anexo.db")
    with sesion_de_instalacion() as sesion:
        fila = sesion.get(Sesion, sesiones.huella_de(ficha))
        fila.ultima_actividad -= timedelta(minutes=31)
        sesion.commit()
    assert navegador.get("/v1/casos").status_code == 401
    assert caso_web.elegido(sesiones.huella_de(ficha)) is None


def test_el_motor_se_guarda_uno_por_caso(_entorno: Path) -> None:
    anexo = f"sqlite:///{(_entorno / 'anexo.db').as_posix()}"
    norte = f"sqlite:///{(_entorno / 'Obra Norte.db').as_posix()}"
    primero = dependencias.obtener_motor(anexo)
    assert dependencias.obtener_motor(anexo) is primero
    assert dependencias.obtener_motor(norte) is not primero


# --- GET /v1/proyectos -----------------------------------------------------------------------


def _vigente_por_sqlite(ruta: Path, proyecto: str) -> tuple[int, str, str]:
    """La versión vigente según el SF: el presupuesto de mayor `id` no descartado."""
    with closing(sqlite3.connect(ruta)) as conexion:
        return conexion.execute(
            "SELECT p.id, p.codigo, p.fecha FROM presupuesto p "
            "JOIN proyecto r ON r.id = p.proyecto_id WHERE r.nombre = ? "
            "AND p.id NOT IN (SELECT presupuesto_id FROM descarte_version) "
            "ORDER BY p.id DESC LIMIT 1",
            (proyecto,),
        ).fetchone()


def _id_por_sqlite(ruta: Path, proyecto: str) -> int:
    with closing(sqlite3.connect(ruta)) as conexion:
        fila = conexion.execute("SELECT id FROM proyecto WHERE nombre = ?", (proyecto,)).fetchone()
    return fila[0]


def test_proyectos_con_y_sin_version_vigente(_entorno: Path) -> None:
    ruta = _entorno / "Obra Norte.db"
    ruta.unlink()
    guardar_base_con_pendiente(ruta)  # el proyecto de la siembra con su presupuesto 001
    preparar_base(ruta)
    crear_proyecto_nuevo(ruta, "anexo sin versiones")
    navegador, ficha = con_cuenta(app, "ana")
    _elegir(navegador, ficha, "Obra Norte.db")
    respuesta = navegador.get("/v1/proyectos")
    assert respuesta.status_code == 200, respuesta.text
    identificador, codigo, fecha = _vigente_por_sqlite(ruta, NOMBRE_PROYECTO)
    esperado = [
        {
            "codigo": str(_id_por_sqlite(ruta, "anexo sin versiones")),
            "nombre": "anexo sin versiones",
            "version_vigente": None,
            "version_codigo": None,
            "actualizado": None,
        },
        {
            "codigo": str(_id_por_sqlite(ruta, NOMBRE_PROYECTO)),
            "nombre": NOMBRE_PROYECTO,
            "version_vigente": identificador,
            "version_codigo": codigo,
            "actualizado": fecha,
        },
    ]
    assert sorted(respuesta.json(), key=lambda p: p["nombre"].casefold()) == esperado
    assert [p["nombre"] for p in respuesta.json()] == [p["nombre"] for p in esperado]


def test_proyectos_de_un_caso_vacio_es_una_lista_vacia() -> None:
    navegador, _ = con_cuenta(app, "rita")
    respuesta = navegador.get("/v1/proyectos")
    assert (respuesta.status_code, respuesta.json()) == (200, [])


def test_el_administrador_solo_no_lee_proyectos() -> None:
    navegador, _ = con_cuenta(app, "admin")
    respuesta = navegador.get("/v1/proyectos")
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_PERMISO})
