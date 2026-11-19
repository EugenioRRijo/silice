"""`POST /v1/produccion/conteos/{movimiento_id}/anular` y el conteo vigente en `/existencias`
(tanda 2026-11-19: un conteo fisico mal hecho se anula sin borrar nada).

Serie FICTICIA de PIEDRA (en t), oraculos a mano: entrada 150,5 el 03/11; conteo 148 el 06/11
(ajuste -2,5); entrada 10 el 08/11; conteo 160 el 10/11 (teorico 158: ajuste +2). Anular el del
10/11 deja 158 y el conteo vigente pasa a ser el del 06/11.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.dependencias import USUARIO_API
from produccion.modelo import Movimiento
from seguridad import cuentas
from tests.fixtures.produccion_api import Web, cliente_con_clave, contar
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

MOTIVO = "Se contó la pila de la otra planta."


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_anular_conteo"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    copiar_instalacion(_instalacion_migrada)
    yield
    cuentas.FRENO.reiniciar()


@pytest.fixture
def http() -> TestClient:
    return cliente_con_clave()


def _mover(http, tipo: str, fecha: str, cantidad: str) -> dict:
    r = http.post(
        "/v1/produccion/movimientos",
        json={"material_codigo": "PIEDRA", "tipo": tipo, "fecha": fecha, "cantidad": cantidad},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _serie(http) -> tuple[dict, dict]:
    r = http.post(
        "/v1/produccion/materiales",
        json={
            "codigo": "PIEDRA",
            "nombre": "Piedra",
            "unidad_venta": "t",
            "existencia_minima": "0",
        },
    )
    assert r.status_code == 201, r.text
    _mover(http, "entrada", "2026-11-03", "150.5")
    primero = _mover(http, "ajuste", "2026-11-06", "148")
    _mover(http, "entrada", "2026-11-08", "10")
    segundo = _mover(http, "ajuste", "2026-11-10", "160")
    return primero, segundo


def _piedra(http) -> dict:
    r = http.get("/v1/produccion/existencias")
    assert r.status_code == 200, r.text
    return next(f for f in r.json() if f["codigo"] == "PIEDRA")


def _anular(http, movimiento_id: int, motivo: str = MOTIVO):
    return http.post(f"/v1/produccion/conteos/{movimiento_id}/anular", json={"motivo": motivo})


def test_la_existencia_trae_el_conteo_vigente(http) -> None:
    _, segundo = _serie(http)
    conteo = _piedra(http)["ultimo_conteo"]
    assert set(conteo) == {"id", "fecha", "diferencia", "usuario"}
    assert (conteo["id"], conteo["fecha"], conteo["usuario"]) == (
        segundo["id"],
        "2026-11-10",
        USUARIO_API,
    )
    assert isinstance(conteo["diferencia"], str) and Decimal(conteo["diferencia"]) == Decimal("2")


def test_un_material_sin_conteo_lo_trae_nulo(http) -> None:
    http.post(
        "/v1/produccion/materiales",
        json={"codigo": "ARENA", "nombre": "Arena", "unidad_venta": "m3", "existencia_minima": "0"},
    )
    filas = http.get("/v1/produccion/existencias").json()
    assert filas[0]["codigo"] == "ARENA" and filas[0]["ultimo_conteo"] is None


def test_anular_el_ultimo_conteo_lo_compensa_y_el_vigente_es_el_anterior(http) -> None:
    primero, segundo = _serie(http)
    r = _anular(http, segundo["id"])
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert (cuerpo["tipo"], cuerpo["fecha"]) == ("ajuste", "2026-11-10")
    assert Decimal(cuerpo["cantidad"]) == Decimal("-2")
    assert (cuerpo["anula_id"], cuerpo["motivo"], cuerpo["usuario"]) == (
        segundo["id"],
        MOTIVO,
        USUARIO_API,
    )
    datetime.fromisoformat(cuerpo["registrado"])  # la hora del servidor, ISO
    fila = _piedra(http)
    assert Decimal(fila["existencia"]) == Decimal("158")
    assert fila["ultimo_conteo"]["id"] == primero["id"]
    assert contar(Movimiento) == 5  # nada se borra: los cuatro de la serie y la anulacion
    # el pasado entre los dos conteos vuelve a estar abierto
    _mover(http, "despacho", "2026-11-09", "8")
    assert Decimal(_piedra(http)["existencia"]) == Decimal("150")


def test_solo_el_ultimo_conteo_vigente_se_anula(http) -> None:
    primero, _ = _serie(http)
    r = _anular(http, primero["id"])
    assert r.status_code == 409
    assert "último conteo vigente de PIEDRA, que es el del 10/11/2026" in r.json()["detalle"]
    assert contar(Movimiento) == 4


def test_anular_dos_veces_responde_409(http) -> None:
    _, segundo = _serie(http)
    assert _anular(http, segundo["id"]).status_code == 201
    r = _anular(http, segundo["id"])
    assert r.status_code == 409 and r.json()["detalle"] == "Ese conteo físico ya fue anulado."
    assert contar(Movimiento) == 5


def test_lo_que_no_es_un_conteo_responde_404(http) -> None:
    _serie(http)
    entrada = _mover(http, "entrada", "2026-11-11", "1")
    for movimiento_id in (entrada["id"], 9999):
        r = _anular(http, movimiento_id)
        assert r.status_code == 404
        assert r.json()["detalle"] == "No existe ese conteo físico. Actualice la existencia."
    assert contar(Movimiento) == 5


@pytest.mark.parametrize("motivo", ["", "   "])
def test_sin_motivo_responde_422_y_no_escribe(http, motivo: str) -> None:
    _, segundo = _serie(http)
    r = _anular(http, segundo["id"], motivo)
    assert r.status_code == 422
    assert r.json()["detalle"] == "Escriba el motivo de la anulación del conteo."
    assert contar(Movimiento) == 4


def test_con_sesion_la_anulacion_queda_a_nombre_de_la_cuenta() -> None:
    ana = Web("ana")
    _, segundo = _serie(ana)
    r = _anular(ana, segundo["id"])
    assert r.status_code == 201, r.text
    assert r.json()["usuario"] == "Ana <ana>"
    assert _piedra(ana)["ultimo_conteo"]["usuario"] == "Ana <ana>"


def test_con_sesion_sin_anti_csrf_se_rechaza_y_no_escribe() -> None:
    ana = Web("ana")
    _, segundo = _serie(ana)
    r = ana.cliente.post(f"/v1/produccion/conteos/{segundo['id']}/anular", json={"motivo": MOTIVO})
    assert r.status_code == 403
    assert contar(Movimiento) == 4
