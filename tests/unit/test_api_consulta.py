"""`GET /v1/consulta/{tabla}`: autocompletado con tablas venezolanas (plan vial, Tarea 20).

Acceso `LEER_PROYECTO` como las rutas vecinas de solo lectura (`/v1/buscar/partidas`); el
administrador recibe 403. Tabla desconocida -> 404; `Cache-Control: no-store`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import manejar_http_exception
from api.proteccion import proteger
from api.rutas import consulta, sesion
from core.catalog import abrir_sesion, crear_motor
from core.models import Insumo
from operacion.base_datos import preparar_base
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
)


def _aplicacion() -> FastAPI:
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(HTTPException, manejar_http_exception)
    aplicacion.include_router(sesion.router)
    aplicacion.include_router(consulta.router)
    proteger(aplicacion)
    return aplicacion


APLICACION = _aplicacion()


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("api_consulta"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    copiar_instalacion(_plantilla)
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            s.add(Insumo(codigo="MAT-1", tipo="material", descripcion="Cemento gris ficticio", unidad="saco"))
            s.commit()
    finally:
        motor.dispose()
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def ana() -> TestClient:
    return con_cuenta(APLICACION, "ana")[0]


def test_carpeta_con_y_sin_mayusculas_ni_acentos_da_lo_mismo(ana: TestClient) -> None:
    a = ana.get("/v1/consulta/partidas_viales", params={"q": "carpeta"})
    b = ana.get("/v1/consulta/partidas_viales", params={"q": "CARPÉTA"})
    assert a.status_code == b.status_code == 200
    assert a.json()["resultados"][0] == b.json()["resultados"][0]
    assert a.json()["resultados"][0]["valor"] == "C-000.000.008"
    assert a.headers.get("cache-control") == "no-store"


def test_cada_sugerencia_trae_su_fuente(ana: TestClient) -> None:
    cuerpo = ana.get("/v1/consulta/insumos", params={"q": "cemento"}).json()
    assert cuerpo["tabla"] == "insumos" and cuerpo["hay_mas"] is False
    assert cuerpo["resultados"] == [
        {
            "valor": "MAT-1",
            "etiqueta": "Cemento gris ficticio (MAT-1, saco)",
            "fuente": "Catálogo de la carpeta de trabajo: material",
        }
    ]


def test_tabla_desconocida_es_404_sin_repetir_lo_enviado(ana: TestClient) -> None:
    r = ana.get("/v1/consulta/no_existe_xyz", params={"q": "algo"})
    assert r.status_code == 404
    assert "no_existe_xyz" not in r.text
    assert r.headers.get("cache-control") == "no-store"


def test_hay_mas_cuando_sobran_coincidencias(ana: TestClient) -> None:
    cuerpo = ana.get("/v1/consulta/partidas_viales", params={"q": "granular", "limite": 1}).json()
    assert len(cuerpo["resultados"]) == 1 and cuerpo["hay_mas"] is True


@pytest.mark.parametrize("params", [{"q": "x" * 81}, {"q": "ab", "limite": 0}, {"q": "ab", "limite": 51}])
def test_forma_invalida_es_422(ana: TestClient, params: dict) -> None:
    r = ana.get("/v1/consulta/insumos", params=params)
    assert r.status_code == 422
    assert r.headers.get("cache-control") == "no-store"


def test_menos_de_dos_letras_responde_vacio(ana: TestClient) -> None:
    assert ana.get("/v1/consulta/insumos", params={"q": "c"}).json()["resultados"] == []


def test_el_administrador_recibe_403_y_sin_sesion_401() -> None:
    admin = con_cuenta(APLICACION, "admin")[0]
    r = admin.get("/v1/consulta/insumos", params={"q": "cemento"})
    assert r.status_code == 403 and MENSAJE_PERMISO in r.text
    assert cliente(APLICACION).get("/v1/consulta/insumos", params={"q": "cemento"}).status_code == 401
