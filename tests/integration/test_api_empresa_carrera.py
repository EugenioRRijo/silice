"""Dos peticiones que escriben el estado de la empresa a la vez no se pisan.

Generar la clave de firma lee «no hay una activa» y luego escribe la nueva; registrar la clave de
otra empresa lee «no esta registrada» y luego escribe. Con `BEGIN` diferido dos peticiones leen lo
mismo y las dos escriben (dos claves activas; la misma empresa dos veces). Con `BEGIN IMMEDIATE`
la segunda espera, lo ve ya confirmado y responde 400. Sin esperas largas: hilos con
`threading.Event`; la primera, ya leido el estado, espera a que la segunda lea (tope de un segundo:
con la sesion de escritura la segunda no puede leer hasta que la primera confirme).
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
from api.rutas import entregas as ruta_entregas
from operacion import config
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, empresas
from tests.fixtures.carrera import dos_a_la_vez
from tests.fixtures.instalacion import AHORA
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

FRASE = "frase de firma larga y propia"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("empresa_carrera"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    caso_web.olvidar_todo()
    ruta_entregas.FRENO_FIRMA.reiniciar()
    cuentas.FRENO.reiniciar()
    yield
    caso_web.olvidar_todo()
    ruta_entregas.FRENO_FIRMA.reiniciar()
    dependencias.cerrar_motores()


def _admin() -> tuple[TestClient, dict[str, str]]:
    navegador, ficha = con_cuenta(app, "admin")
    return navegador, protegida(ficha)


def _filas(sql: str) -> list[tuple]:
    with closing(sqlite3.connect(config.ruta_instalacion())) as bd:
        return list(bd.execute(sql))


def test_dos_generaciones_de_la_clave_dejan_una_sola_activa(monkeypatch) -> None:
    with sesion_de_instalacion() as bd:
        empresas.guardar_empresa_propia(bd, "Demo, C.A.", "J-00000000-0", "", "admin", AHORA)
    navegador, cab = _admin()
    otro, cab_otro = _admin()

    def peticion(c: TestClient, h: dict[str, str]):
        return lambda: c.post("/v1/admin/empresa/clave", json={"contrasena": FRASE}, headers=h)

    respuestas = dos_a_la_vez(
        monkeypatch,
        empresas,
        "exigir_contrasena_de_clave",
        peticion(navegador, cab),
        peticion(otro, cab_otro),
    )
    estados = sorted(r.status_code for r in respuestas)
    assert estados == [200, 400]
    assert _filas("SELECT estado FROM clave_empresa") == [("activa",)]
