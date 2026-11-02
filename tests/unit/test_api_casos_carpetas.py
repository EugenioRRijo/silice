"""Carpetas de trabajo por la API: resumen, crear y demostración (BCP-2; diseño §4, §9 C0, C1 y C3;
B11, B12, B16 a B18, S5, S8 y S9).

Contrato (§9): `GET /v1/casos/actual` (cualquier rol o clave), `POST /v1/casos` (`CAMBIAR_CASO`) y
`POST /v1/casos/demostracion` (`EDITAR_HOJA`); `Cache-Control: no-store`; 422 sin eco; con la clave
de API, crear y la demostración dan 409. Oráculos a mano: los roles de `CUENTAS`
(`tests/fixtures/sesion_web.py`), los mensajes del diseño copiados con sus tildes, los conteos con
`sqlite3` directo y la ficha de la base de prueba. La demostración usa un doble del proceso hijo
salvo en una prueba (B17), que corre la orden real una vez.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import casos as rutas_casos
from aplicacion import casos
from operacion import base_datos, config, demostracion
from operacion.base_datos import Destino, revision_head
from tests.fixtures import bases_prueba
from tests.fixtures.carpetas_trabajo import arbol, base_minima, copiar
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

MENSAJE_CON_CLAVE = (
    "Con la clave de API se trabaja en el caso del proceso (APU_BASE); el caso se elige por "
    "sesión desde la interfaz."
)
MENSAJE_CSRF = "Falta la comprobación anti-CSRF de la sesión o no coincide."
MENSAJE_ORIGEN = "La petición no viene de la interfaz de esta instalación."
MENSAJE_CAMBIAR_CLAVE = "Su contraseña es temporal: elija una propia antes de seguir."
MENSAJE_TOPE = "Ya hay 100 carpetas de trabajo: retire alguna antes de crear otra."
MENSAJE_EN_CURSO = "Hay otra creación de carpeta en curso: espere unos segundos y repita."
MENSAJE_RESERVADO = "Ese nombre está reservado para la demostración."
MENSAJE_PREPARACION = (
    "No se pudo preparar la carpeta de trabajo: no se guardó. Pruebe de nuevo; si sigue, avise al "
    "administrador."
)
MENSAJE_DEMOSTRACION = (
    "No se pudo preparar la demostración. Pruebe de nuevo; si sigue, avise al administrador."
)
FORMA_CREAR = "Escriba el nombre de la carpeta de trabajo como texto de hasta 200 caracteres."
CLAVES_DEL_RESUMEN = {
    "nombre",
    "ruta_relativa",
    "ubicacion",
    "partidas",
    "insumos",
    "lista_vigente",
    "proyectos",
    "proyectos_con_version",
    "es_demostracion",
    "por_migrar",
    "error",
}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_api_carpetas")
    with pytest.MonkeyPatch.context() as parche:  # migrar respalda: nunca en `data/`
        parche.setenv("SILICE_DATOS", str(carpeta / "datos"))
        parche.setenv("SILICE_USUARIO", str(carpeta / "datos"))
        demo = bases_prueba.copiar_base("1.0.0", "demo.db", carpeta / "demo_head.db")
        base_datos.preparar_base(demo)
        minima = base_minima(carpeta / "minima.db")
    return {"instalacion": plantilla_con_cuentas(carpeta), "demo": demo, "minima": minima}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    caso_web.olvidar_todo()
    yield config.carpeta_datos()
    caso_web.olvidar_todo()
    app.dependency_overrides.pop(rutas_casos.ejecutor_de_demostracion, None)
    dependencias.cerrar_motores()


def _doble(plantilla: Path, llamadas: list[Path] | None = None):
    def construir(salida: Path) -> None:
        if llamadas is not None:
            llamadas.append(salida)
        copiar(plantilla, salida)

    return construir


def _con_doble(construir) -> None:
    app.dependency_overrides[rutas_casos.ejecutor_de_demostracion] = lambda: construir


def _crear(navegador: TestClient, ficha: str, nombre, **extra):
    return navegador.post(
        "/v1/casos", json={"nombre": nombre}, headers={**protegida(ficha), **extra}
    )


def _demo(navegador: TestClient, ficha: str):
    return navegador.post("/v1/casos/demostracion", headers=protegida(ficha))


def _nombres() -> list[str]:
    carpeta = config.carpeta_casos()
    return sorted(p.name for p in carpeta.iterdir()) if carpeta.is_dir() else []


def _caso(nombre: str) -> dict[str, str]:
    return {"nombre": nombre, "ruta_relativa": f"casos/{nombre}"}


# --- C1: POST /v1/casos ------------------------------------------------------------------------


@pytest.mark.parametrize("login", ["ana", "admin"])
def test_quien_cambia_de_caso_crea_una_carpeta(login: str) -> None:
    navegador, ficha = con_cuenta(app, login)
    respuesta = _crear(navegador, ficha, "Obra*1")
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json() == _caso("Obra_1.db")
    assert respuesta.headers["cache-control"] == "no-store"
    assert _caso("Obra_1.db") in navegador.get("/v1/casos").json()["casos"]
    ruta = config.carpeta_casos() / "Obra_1.db"
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as conexion:
        revision = conexion.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert revision == revision_head(Destino.CASO)
    # crear no abre: la ficha sigue en su caso (dos pasos, DV-BCP-6)
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")


def test_quien_revisa_no_crea() -> None:
    navegador, ficha = con_cuenta(app, "rita")
    respuesta = _crear(navegador, ficha, "Obra")
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert _nombres() == []


def test_con_la_contrasena_temporal_no_crea() -> None:
    navegador, ficha = con_cuenta(app, "tomas")
    respuesta = _crear(navegador, ficha, "Obra")
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_CAMBIAR_CLAVE}


def test_sin_sesion_es_401_y_con_clave_409() -> None:
    assert cliente(app).post("/v1/casos", json={"nombre": "Obra"}).status_code == 401
    respuesta = cliente(app).post(
        "/v1/casos", json={"nombre": "Obra"}, headers={CABECERA: crear_clave_de_prueba()}
    )
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": MENSAJE_CON_CLAVE}
    assert _nombres() == []


def test_sin_csrf_u_origen_propio_es_403() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    sin_csrf = navegador.post(
        "/v1/casos", json={"nombre": "Obra"}, headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert (sin_csrf.status_code, sin_csrf.json()) == (403, {"detalle": MENSAJE_CSRF})
    ajeno = _crear(navegador, ficha, "Obra", Origin="http://evil.invalid")
    assert (ajeno.status_code, ajeno.json()) == (403, {"detalle": MENSAJE_ORIGEN})
    assert _nombres() == []


@pytest.mark.parametrize("repetido", ["Obra", "OBRA", "obra.db"])
def test_un_nombre_repetido_es_409(repetido: str) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _crear(navegador, ficha, "Obra").status_code == 201
    respuesta = _crear(navegador, ficha, repetido)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "Ya existe la carpeta de trabajo Obra.db: ábrala de la lista o elija otro "
        "nombre."
    }
    assert _nombres() == ["Obra.db"]


def test_dos_creaciones_simultaneas_dan_201_y_409() -> None:
    navegadores = [con_cuenta(app, "ana") for _ in range(2)]
    barrera = threading.Barrier(2)
    estados: list[int] = []

    def crear(navegador: TestClient, ficha: str) -> None:
        barrera.wait()
        estados.append(_crear(navegador, ficha, "Gemela").status_code)

    hilos = [threading.Thread(target=crear, args=par) for par in navegadores]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert sorted(estados) == [201, 409]
    assert _nombres() == ["Gemela.db"]


def test_al_tope_es_409() -> None:
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True)
    for numero in range(100):
        (carpeta / f"c{numero:03}.db").write_bytes(b"")
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, "otra")
    assert (respuesta.status_code, respuesta.json()) == (409, {"detalle": MENSAJE_TOPE})


def test_otra_creacion_en_curso_es_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(casos, "PLAZO_CERROJO_S", 0.05)
    navegador, ficha = con_cuenta(app, "ana")
    with casos._cerrojo:  # otra creación tiene el cerrojo
        respuesta = _crear(navegador, ficha, "Obra")
    assert (respuesta.status_code, respuesta.json()) == (409, {"detalle": MENSAJE_EN_CURSO})


@pytest.mark.parametrize("nombre", ["demostracion", "Demostración", "DEMOSTRACION.db"])
def test_el_nombre_de_la_demostracion_es_422(nombre: str) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _crear(navegador, ficha, nombre)
    assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": MENSAJE_RESERVADO})


#: S5 por la API (la misma lista que la prueba de `aplicacion`).
HOSTILES_DE_NOMBRE = [
    "..\\x",
    "../x",
    "a/b",
    "a\\b",
    "C:\\x",
    "\\\\srv\\share\\x",
    "//srv/x",
    "con",
    "NUL.db",
    "COM1",
    "COM¹",
    "x:y",
    "x.db::$DATA",
    "   ",
    "....",
    ".",
    "x.",
    "n" * 200,
    "Ñandú",
    "x<y>",
    "%2e%2e/x",
]


@pytest.mark.parametrize("nombre", HOSTILES_DE_NOMBRE)
def test_ningun_nombre_hostil_sale_de_casos(nombre: str, _entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    fuera_antes = {k: v for k, v in arbol(_entorno).items() if not k.startswith("casos")}
    respuesta = _crear(navegador, ficha, nombre)
    assert respuesta.status_code in (201, 422), respuesta.text
    if respuesta.status_code == 201:
        creado = config.carpeta_casos() / respuesta.json()["nombre"]
        assert creado.resolve().parent == config.carpeta_casos().resolve()
        assert respuesta.json()["ruta_relativa"] == f"casos/{creado.name}"
    else:
        assert _nombres() == []
    fuera = {k: v for k, v in arbol(_entorno).items() if not k.startswith("casos")}
    assert fuera == fuera_antes


@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"nombre": 5}, {"nombre": None}, {"nombre": "n" * 201}, {"otro": "x"}],
    ids=["vacio", "numero", "nulo", "largo", "sin_nombre"],
)
def test_un_cuerpo_invalido_es_422_sin_eco(cuerpo: dict) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post("/v1/casos", json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA_CREAR}
    assert respuesta.headers["cache-control"] == "no-store"
    assert "n" * 201 not in respuesta.text


def test_un_fallo_al_preparar_es_503_sin_rastro(
    monkeypatch: pytest.MonkeyPatch, _entorno: Path
) -> None:
    def falla(ruta: Path, *args, **kwargs):
        raise base_datos.MigracionFallida(f"no se pudo crear {ruta}")

    monkeypatch.setattr(casos, "preparar_base", falla)
    navegador, ficha = con_cuenta(app, "ana")
    antes = arbol(_entorno)
    respuesta = _crear(navegador, ficha, "Rota")
    assert (respuesta.status_code, respuesta.json()) == (503, {"detalle": MENSAJE_PREPARACION})
    assert str(_entorno) not in respuesta.text
    assert arbol(_entorno) == antes


# --- C0: GET /v1/casos/actual -----------------------------------------------------------------


@pytest.mark.parametrize("login", ["admin", "ana", "rita"])
def test_cualquier_rol_ve_el_resumen_sin_crear_el_archivo(login: str, _entorno: Path) -> None:
    navegador, _ = con_cuenta(app, login)
    antes = arbol(_entorno)
    respuesta = navegador.get("/v1/casos/actual")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "nombre": "silice.db",
        "ruta_relativa": "casos/silice.db",
        "ubicacion": "En la carpeta de datos de Sílice: casos/silice.db",
        "partidas": 0,
        "insumos": 0,
        "lista_vigente": None,
        "proyectos": 0,
        "proyectos_con_version": 0,
        "es_demostracion": False,
        "por_migrar": False,
        "error": None,
    }
    assert arbol(_entorno) == antes  # no crea `silice.db`
    assert str(_entorno) not in respuesta.text and _entorno.as_posix() not in respuesta.text


def test_el_resumen_de_la_demostracion_abierta(
    _plantillas: dict[str, Path], _entorno: Path
) -> None:
    ruta = copiar(_plantillas["demo"], config.carpeta_casos() / "demostracion.db")
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as conexion:
        partidas, insumos, proyectos = (
            conexion.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]
            for tabla in ("partida", "insumo", "proyecto")
        )
    navegador, ficha = con_cuenta(app, "ana")
    eleccion = navegador.post(
        "/v1/casos/actual", json={"nombre": "demostracion.db"}, headers=protegida(ficha)
    )
    assert eleccion.status_code == 200, eleccion.text
    resumen = navegador.get("/v1/casos/actual").json()
    assert set(resumen) == CLAVES_DEL_RESUMEN
    assert (resumen["partidas"], resumen["insumos"], resumen["proyectos"]) == (
        partidas,
        insumos,
        proyectos,
    )
    assert partidas == 8 and resumen["proyectos_con_version"] == 1
    assert resumen["es_demostracion"] is True and resumen["error"] is None
    assert resumen["nombre"] == "demostracion.db"


def test_el_resumen_sin_sesion_es_401_y_con_clave_es_el_del_proceso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert cliente(app).get("/v1/casos/actual").status_code == 401
    otro = config.carpeta_casos() / "anexo.db"
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{otro.as_posix()}")
    respuesta = cliente(app).get("/v1/casos/actual", headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "anexo.db"
    assert not otro.exists()


def test_el_resumen_de_un_proceso_sin_archivo_es_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencias.VARIABLE_BASE, "sqlite:///:memory:")
    respuesta = cliente(app).get("/v1/casos/actual", headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.status_code == 503
    assert set(respuesta.json()) == {"detalle"}


# --- C3: POST /v1/casos/demostracion -------------------------------------------------------------


def test_quien_arma_estrena_la_demostracion_y_es_idempotente(
    _plantillas: dict[str, Path], _entorno: Path
) -> None:
    llamadas: list[Path] = []
    _con_doble(_doble(_plantillas["demo"], llamadas))
    navegador, ficha = con_cuenta(app, "ana")
    primera = _demo(navegador, ficha)
    assert primera.status_code == 201, primera.text
    assert primera.json() == _caso("demostracion.db")
    assert primera.headers["cache-control"] == "no-store"
    segunda = _demo(navegador, ficha)
    assert (segunda.status_code, segunda.json()) == (200, _caso("demostracion.db"))
    assert len(llamadas) == 1
    assert llamadas[0].is_absolute() and llamadas[0].parent.parent.name == "cuarentena"
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")  # no la abre
    sin_instalacion = {k for k in arbol(_entorno) if not k.startswith("instalacion.db")}
    assert sin_instalacion == {"casos", "casos/demostracion.db"}


@pytest.mark.parametrize("login", ["admin", "rita"])
def test_sin_editar_hoja_no_se_estrena(login: str, _plantillas: dict[str, Path]) -> None:
    _con_doble(lambda salida: pytest.fail("no debe construir"))
    navegador, ficha = con_cuenta(app, login)
    respuesta = _demo(navegador, ficha)
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_PERMISO})
    assert _nombres() == []


def test_la_demostracion_con_clave_es_409() -> None:
    _con_doble(lambda salida: pytest.fail("no debe construir"))
    respuesta = cliente(app).post(
        "/v1/casos/demostracion", headers={CABECERA: crear_clave_de_prueba()}
    )
    assert (respuesta.status_code, respuesta.json()) == (409, {"detalle": MENSAJE_CON_CLAVE})


@pytest.mark.parametrize("modo", ["falla", "basura"])
def test_una_demostracion_fallida_es_503_sin_rastro(modo: str, _entorno: Path) -> None:
    def construir(salida: Path) -> None:
        if modo == "falla":
            raise demostracion.DemostracionFallida("el hijo terminó con 1")
        salida.write_bytes(b"no soy una base")

    _con_doble(construir)
    navegador, ficha = con_cuenta(app, "ana")
    antes = arbol(_entorno)
    respuesta = _demo(navegador, ficha)
    assert (respuesta.status_code, respuesta.json()) == (503, {"detalle": MENSAJE_DEMOSTRACION})
    assert arbol(_entorno) == antes


def test_la_demostracion_con_otra_creacion_en_curso_es_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _con_doble(lambda salida: pytest.fail("no debe construir"))
    monkeypatch.setattr(casos, "PLAZO_CERROJO_S", 0.05)
    navegador, ficha = con_cuenta(app, "ana")
    with casos._cerrojo:
        respuesta = _demo(navegador, ficha)
    assert (respuesta.status_code, respuesta.json()) == (503, {"detalle": MENSAJE_EN_CURSO})


def test_la_demostracion_real_siembra_la_clinica_y_las_tres_partidas_demo() -> None:
    """B17, una sola vez: el proceso hijo de verdad (`python -m operacion demostracion --salida`).
    Oráculo: el docstring de `scripts/seed_demo.py` (cinco `LB-*`, tres `DEMO-*`, `DEMO-001`)."""
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _demo(navegador, ficha)
    assert respuesta.status_code == 201, respuesta.text
    ruta = config.carpeta_casos() / "demostracion.db"
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as conexion:
        codigos = sorted(f[0] for f in conexion.execute("SELECT codigo FROM partida"))
        presupuestos = [f[0] for f in conexion.execute("SELECT codigo FROM presupuesto")]
    assert codigos == [
        "DEMO-01-INST",
        "DEMO-02-VALV",
        "DEMO-03-PRUEBA",
        "LB-01-EXC",
        "LB-02-TUB",
        "LB-03-ENC",
        "LB-04-CON",
        "LB-05-REL",
    ]
    assert presupuestos == ["DEMO-001"]
    assert navegador.get("/v1/casos").json()["actual"] == _caso("silice.db")
    assert not (config.carpeta_datos() / "cuarentena").exists()
