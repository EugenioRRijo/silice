"""Una peticion que escribe en `instalacion.db` no espera a una sesion suya (BEGIN IMMEDIATE).

La sesion de la ruta toma el bloqueo de escritura al empezar. Si otra dependencia o el codigo de la
MISMA peticion abriera otra sesion de la instalacion y escribiera mientras esa sigue abierta (la
clave de API anota su ultimo uso, la sesion web renueva su vigencia), esperaria el `busy_timeout`
contra si misma y daria un error a los 5 s. Con la autenticacion REAL (sin anularla), cada POST
termina en menos de un segundo y ninguna sesion de instalacion se abre con una de escritura viva.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

import operacion.instalacion as modulo
from api.main import app
from seguridad import cuentas
from tests.fixtures.produccion_api import Web, cliente_con_clave
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

LIMITE_S = 1.0
MATERIAL = {"codigo": "ARENA", "nombre": "Arena", "unidad_venta": "m3", "existencia_minima": "0"}
MOVIMIENTO = {
    "material_codigo": "ARENA",
    "tipo": "entrada",
    "fecha": "2026-10-01",
    "cantidad": "100",
}


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_autoespera"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    copiar_instalacion(_instalacion_migrada)
    yield
    cuentas.FRENO.reiniciar()


@pytest.fixture
def solapes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Registra cada sesion de la instalacion que se abre mientras una de escritura sigue viva."""
    vivas: list[object] = []
    hallados: list[str] = []
    abrir, abrir_escritura = modulo.abrir_sesion, modulo.abrir_sesion_de_escritura

    def envolver(fabrica, es_de_escritura: bool):
        def abrir_vigilada(motor):
            if vivas:
                hallados.append("sesion abierta con una de escritura viva")
            sesion = fabrica(motor)
            cerrar = sesion.close

            def cerrar_y_olvidar() -> None:
                if sesion in vivas:
                    vivas.remove(sesion)
                cerrar()

            sesion.close = cerrar_y_olvidar
            if es_de_escritura:
                vivas.append(sesion)
            return sesion

        return abrir_vigilada

    monkeypatch.setattr(modulo, "abrir_sesion", envolver(abrir, False))
    monkeypatch.setattr(modulo, "abrir_sesion_de_escritura", envolver(abrir_escritura, True))
    return hallados


def _rapido(respuesta_de) -> None:
    modulo.motor_de_instalacion()  # abrir y migrar la base no cuenta: se mide la peticion
    t0 = time.perf_counter()
    respuesta = respuesta_de()
    assert time.perf_counter() - t0 < LIMITE_S
    assert respuesta.status_code == 201, respuesta.text


def test_post_con_clave_de_api_real_no_se_espera_a_si_mismo(solapes: list[str]) -> None:
    http = cliente_con_clave()  # la primera peticion anota `ultimo_uso` de la clave (escribe)
    assert http.get("/salud").status_code == 200  # el arranque del cliente no se mide
    _rapido(lambda: http.post("/v1/produccion/materiales", json=MATERIAL))
    _rapido(lambda: http.post("/v1/produccion/movimientos", json=MOVIMIENTO))
    assert solapes == []


def test_post_con_sesion_web_real_no_se_espera_a_si_mismo(solapes: list[str]) -> None:
    web = Web("ana")
    assert web.get("/salud").status_code == 200
    _rapido(lambda: web.post("/v1/produccion/materiales", json=MATERIAL))
    _rapido(lambda: web.post("/v1/produccion/movimientos", json=MOVIMIENTO))
    assert solapes == []


def test_la_guardia_ve_el_solape(solapes: list[str]) -> None:
    with modulo.sesion_de_instalacion(escritura=True), modulo.sesion_de_instalacion():
        pass
    assert solapes == ["sesion abierta con una de escritura viva"]
    assert app is not None
