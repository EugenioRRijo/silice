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
import threading
from collections.abc import Callable, Iterator
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


def _dos_a_la_vez(
    monkeypatch: pytest.MonkeyPatch, objeto: object, nombre: str, peticion: Callable[[], object]
) -> list[int]:
    """Corre `peticion` en dos hilos. `objeto.nombre` es una funcion que se llama DESPUES de leer
    lo que decide y ANTES de escribir: la primera en llegar espera (hasta un segundo) a la
    segunda."""
    original = getattr(objeto, nombre)
    llegadas, lock = [], threading.Lock()
    primera_leyo, segunda_leyo = threading.Event(), threading.Event()

    def gancho(*args, **kwargs):
        with lock:
            llegadas.append(1)
            es_la_primera = len(llegadas) == 1
        if es_la_primera:
            primera_leyo.set()
            segunda_leyo.wait(timeout=1)
        else:
            segunda_leyo.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(objeto, nombre, gancho)
    estados: list[int] = []

    def hilo(es_la_segunda: bool) -> None:
        if es_la_segunda:
            primera_leyo.wait(timeout=10)
        estados.append(peticion().status_code)

    hilos = [threading.Thread(target=hilo, args=(n == 1,)) for n in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=30)
    return sorted(estados)


def test_dos_generaciones_de_la_clave_dejan_una_sola_activa(monkeypatch) -> None:
    with sesion_de_instalacion() as bd:
        empresas.guardar_empresa_propia(bd, "Demo, C.A.", "J-00000000-0", "", "admin", AHORA)
    navegador, cab = _admin()
    otro, cab_otro = _admin()
    clientes = iter([(navegador, cab), (otro, cab_otro)])
    lock = threading.Lock()

    def peticion():
        with lock:
            c, h = next(clientes)
        return c.post("/v1/admin/empresa/clave", json={"contrasena": FRASE}, headers=h)

    estados = _dos_a_la_vez(monkeypatch, empresas, "exigir_contrasena_de_clave", peticion)
    assert estados == [200, 400]
    assert _filas("SELECT estado FROM clave_empresa") == [("activa",)]
