"""`GET /v1/casos` con `empresa` y `es_demostracion`, y `DELETE /v1/casos/actual` (MOD-3a; diseño
`2026-10-25-modulos-design.md` §7 y §12).

La carpeta de la empresa es la del proceso (aquí `silice.db`, la de omisión de la instalación).
Oráculos a mano: nombres de las carpetas de la fixture, los roles de `CUENTAS` y los mensajes
copiados del código de `POST /v1/casos/actual`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import casos as rutas_casos
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.carpetas_trabajo import copiar
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    entrar,
    plantilla_con_cuentas,
    protegida,
)

MENSAJE_CON_CLAVE = (
    "Con la clave de API se trabaja en el caso del proceso (APU_BASE); el caso se elige por "
    "sesión desde la interfaz."
)
MENSAJE_CSRF = "Falta la comprobación anti-CSRF de la sesión o no coincide."
MENSAJE_ORIGEN = "La petición no viene de la interfaz de esta instalación."
EMPRESA = {"nombre": "silice.db", "ruta_relativa": "casos/silice.db"}
CARPETAS = ("s1.db", "silice.db")
SIN_ELECCION = {"caso": None, "proyecto": None, "aviso": None}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_casos_empresa")
    casos = {}
    for nombre in CARPETAS:
        casos[nombre] = carpeta / nombre
        preparar_base(casos[nombre])
    with closing(sqlite3.connect(casos["s1.db"])) as conexion:
        conexion.execute(
            "INSERT INTO proyecto (id, nombre, descripcion, dominio) VALUES (7, 'Torre B', '', '')"
        )
        conexion.commit()
    return {"instalacion": plantilla_con_cuentas(carpeta), **casos}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in CARPETAS:
        (carpeta / nombre).write_bytes(_plantillas[nombre].read_bytes())
    caso_web.olvidar_todo()
    yield carpeta
    caso_web.olvidar_todo()
    app.dependency_overrides.pop(rutas_casos.ejecutor_de_demostracion, None)
    dependencias.cerrar_motores()


def _elegir(navegador: TestClient, ficha: str, nombre: str):
    return navegador.post("/v1/casos/actual", json={"nombre": nombre}, headers=protegida(ficha))


def _volver(navegador: TestClient, ficha: str, **extra):
    return navegador.delete("/v1/casos/actual", headers={**protegida(ficha), **extra})


# --- GET /v1/casos: empresa y es_demostracion --------------------------------------------------


def test_la_lista_trae_la_empresa_y_no_es_demostracion() -> None:
    navegador, _ = con_cuenta(app, "ana")
    cuerpo = navegador.get("/v1/casos").json()
    assert set(cuerpo) == {"actual", "casos", "empresa", "es_demostracion"}
    assert cuerpo["empresa"] == EMPRESA
    assert cuerpo["actual"] == EMPRESA
    assert cuerpo["es_demostracion"] is False


def test_la_empresa_no_cambia_al_elegir_otra_carpeta() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    cuerpo = navegador.get("/v1/casos").json()
    assert cuerpo["actual"]["nombre"] == "s1.db"
    assert cuerpo["empresa"] == EMPRESA
    assert cuerpo["es_demostracion"] is False


def test_la_empresa_es_la_del_proceso_aunque_este_fuera_de_la_lista(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, _plantillas: dict[str, Path]
) -> None:
    fuera = tmp_path / "otra" / "empresa_x.db"
    fuera.parent.mkdir()
    fuera.write_bytes(_plantillas["silice.db"].read_bytes())
    monkeypatch.setenv(dependencias.VARIABLE_BASE, dependencias.url_de_ruta(fuera))
    navegador, _ = con_cuenta(app, "ana")
    cuerpo = navegador.get("/v1/casos").json()
    assert cuerpo["empresa"] == {"nombre": "empresa_x.db", "ruta_relativa": "empresa_x.db"}
    assert cuerpo["actual"] == cuerpo["empresa"]


def test_es_demostracion_con_la_carpeta_de_demostracion_elegida(
    _plantillas: dict[str, Path],
) -> None:
    app.dependency_overrides[rutas_casos.ejecutor_de_demostracion] = lambda: (
        lambda salida: copiar(_plantillas["silice.db"], salida)
    )
    navegador, ficha = con_cuenta(app, "ana")
    assert navegador.post("/v1/casos/demostracion", headers=protegida(ficha)).status_code == 201
    assert navegador.get("/v1/casos").json()["es_demostracion"] is False
    assert _elegir(navegador, ficha, "demostracion.db").status_code == 200
    cuerpo = navegador.get("/v1/casos").json()
    assert cuerpo["es_demostracion"] is True
    assert cuerpo["actual"]["nombre"] == "demostracion.db"
    assert cuerpo["empresa"] == EMPRESA
    assert _volver(navegador, ficha).status_code == 200
    assert navegador.get("/v1/casos").json()["es_demostracion"] is False


def test_con_la_clave_la_lista_trae_la_empresa() -> None:
    cuerpo = cliente(app).get("/v1/casos", headers={CABECERA: crear_clave_de_prueba()}).json()
    assert cuerpo["empresa"] == EMPRESA
    assert cuerpo["es_demostracion"] is False


# --- DELETE /v1/casos/actual -------------------------------------------------------------------


@pytest.mark.parametrize("login", ["ana", "admin"])
def test_volver_a_la_empresa_devuelve_su_carpeta_y_olvida_lo_recordado(login: str) -> None:
    navegador, ficha = con_cuenta(app, login)
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    if login == "ana":
        asignada = navegador.put(
            "/v1/sesion/proyecto", json={"proyecto": "7"}, headers=protegida(ficha)
        )
        assert asignada.status_code == 204

    respuesta = _volver(navegador, ficha)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == EMPRESA
    cuerpo = navegador.get("/v1/casos").json()
    assert cuerpo["actual"] == cuerpo["empresa"] == EMPRESA
    assert navegador.get("/v1/sesion").json()["eleccion"] == SIN_ELECCION
    # y sigue así tras salir y volver a entrar: la carpeta recordada es la de la empresa
    assert navegador.delete("/v1/sesion", headers=protegida(ficha)).status_code == 204
    assert entrar(navegador, login).json()["eleccion"] == SIN_ELECCION
    assert navegador.get("/v1/casos").json()["actual"] == EMPRESA


def test_volver_estando_ya_en_la_empresa_es_idempotente() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _volver(navegador, ficha).json() == EMPRESA
    assert _volver(navegador, ficha).json() == EMPRESA


def test_volver_no_pasa_si_la_instalacion_falla() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200

    def falla(*_args, **_kwargs) -> None:
        raise RuntimeError("falla simulada")

    with pytest.MonkeyPatch.context() as parche:  # solo esta sustitución, no el entorno
        parche.setattr(rutas_casos, "recordar_caso", falla)
        assert _volver(navegador, ficha).status_code == 500
    # la ficha conserva su carpeta: la memoria cambia solo después de confirmar
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "s1.db"
    assert navegador.get("/v1/sesion").json()["eleccion"]["caso"] == "s1.db"


def test_rita_no_vuelve() -> None:
    navegador, ficha = con_cuenta(app, "rita")
    respuesta = _volver(navegador, ficha)
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_PERMISO})


def test_sin_csrf_u_origen_propio_es_403() -> None:
    navegador, ficha = con_cuenta(app, "ana")
    assert _elegir(navegador, ficha, "s1.db").status_code == 200
    sin_csrf = navegador.delete("/v1/casos/actual", headers={"Origin": "http://127.0.0.1:8000"})
    assert (sin_csrf.status_code, sin_csrf.json()) == (403, {"detalle": MENSAJE_CSRF})
    ajeno = _volver(navegador, ficha, Origin="http://evil.invalid")
    assert (ajeno.status_code, ajeno.json()) == (403, {"detalle": MENSAJE_ORIGEN})
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "s1.db"


def test_sin_sesion_es_401_y_con_clave_409() -> None:
    assert cliente(app).delete("/v1/casos/actual").status_code == 401
    respuesta = cliente(app).delete("/v1/casos/actual", headers={CABECERA: crear_clave_de_prueba()})
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": MENSAJE_CON_CLAVE}


def test_con_la_contrasena_temporal_no_vuelve() -> None:
    navegador, ficha = con_cuenta(app, "tomas")
    assert _volver(navegador, ficha).status_code == 403


def test_sin_archivo_en_disco_volver_da_503_con_su_propio_mensaje(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    monkeypatch.setenv(dependencias.VARIABLE_BASE, "sqlite:///:memory:")
    respuesta = _volver(navegador, ficha)
    assert respuesta.status_code == 503
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "detalle": "Esta instalación no usa una carpeta de trabajo en disco: no hay carpeta de "
        "la empresa a la que volver."
    }
