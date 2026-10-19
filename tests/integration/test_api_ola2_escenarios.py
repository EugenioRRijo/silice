"""Ola 2 de la migración, Escenarios (UC-08): el base de la página y la tabla de RF-31 en CSV.

Oráculos a mano: el incremento de la muestra de precios (30,17025 × 1,66 = 50,082615 USD, de
`tests/fixtures/actualizacion_uc02.py`) y los parámetros por defecto de la línea base
(NORMAS.md §4: FCAS 6,00; bono 1,00; administración 0,15; utilidad 0,10).
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal

import pytest

from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from scripts.seed import NOMBRE_PROYECTO
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import INCREMENTO_TOTAL
from tests.fixtures.base_con_pendiente import PENDIENTE_T99

ESCENARIOS = {
    "escenarios": [
        {"nombre": "cemento y arena", "precios": {"Cemento Portland": "18", "Arena lavada": "33"}},
        {"nombre": "utilidad 20", "utilidad": "0.20"},
    ]
}


@pytest.fixture
def presupuesto_001(cliente, items_payload):
    respuesta = cliente.post(
        "/presupuestos",
        json={
            "codigo": "001",
            "fecha": linea_base.FECHA_LINEA_BASE.isoformat(),
            "moneda": linea_base.MONEDA,
            "proyecto": NOMBRE_PROYECTO,
            "items": items_payload,
        },
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def test_el_base_trae_sus_parametros_congelados_exactos(cliente, presupuesto_001):
    respuesta = cliente.get("/presupuestos/001/escenarios/base")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "codigo": "001",
        "proyecto": NOMBRE_PROYECTO,
        "moneda": linea_base.MONEDA,
        "total": presupuesto_001["total"],
        "parametros": {
            "fcas": "6.00",
            "bono_alimentacion": "1.00",
            "administracion": "0.15",
            "utilidad": "0.10",
        },
        "pendientes_base": [],
    }


def test_el_base_declara_sus_pendientes_con_la_cantidad_exacta(cliente_con_pendiente):
    respuesta = cliente_con_pendiente.get(
        f"/presupuestos/{linea_base.CODIGO_PRESUPUESTO}/escenarios/base"
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["pendientes_base"] == [
        {
            "codigo_partida": PENDIENTE_T99.codigo_partida,
            "descripcion": PENDIENTE_T99.descripcion,
            "unidad": PENDIENTE_T99.unidad,
            "cantidad": str(PENDIENTE_T99.cantidad),
            "origen_id": PENDIENTE_T99.origen_id,
        }
    ]
    assert cuerpo["total"] == formatear_decimal(
        linea_base.TOTAL_EXACTO_LINEA_BASE, DECIMALES_PRESENTACION
    )


def test_el_base_de_un_presupuesto_inexistente_es_404(cliente):
    assert cliente.get("/presupuestos/NO-EXISTE/escenarios/base").status_code == 404


def test_el_csv_lleva_la_tabla_de_rf31_con_valores_exactos(cliente, presupuesto_001):
    respuesta = cliente.post("/presupuestos/001/escenarios/csv", json=ESCENARIOS)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"].startswith("text/csv")
    assert 'filename="escenarios_001.csv"' in respuesta.headers["content-disposition"]
    filas = list(csv.DictReader(io.StringIO(respuesta.text)))
    assert [f["escenario"] for f in filas] == ["001", "cemento y arena", "utilidad 20"]
    assert list(filas[0]) == ["escenario", "total", "variacion", "variacion_pct"]
    # El base: variación cero. El escenario del cemento y la arena: 50,082615 exactos, no 50,08.
    assert Decimal(filas[0]["variacion"]) == 0
    assert Decimal(filas[1]["variacion"]) == INCREMENTO_TOTAL
    assert Decimal(filas[1]["total"]) - Decimal(filas[0]["total"]) == INCREMENTO_TOTAL
    # 100 x (1,20/1,10 - 1) no se redondea a dos decimales en el CSV.
    assert len(filas[2]["variacion_pct"].split(".")[1]) > 2


def test_el_csv_con_un_parametro_fuera_de_rango_es_422(cliente, presupuesto_001):
    respuesta = cliente.post(
        "/presupuestos/001/escenarios/csv",
        json={"escenarios": [{"nombre": "malo", "utilidad": "-0.10"}]},
    )

    assert respuesta.status_code == 422
    assert "utilidad" in respuesta.json()["detalle"]


def test_el_csv_no_guarda_nada(cliente, presupuesto_001):
    cliente.post("/presupuestos/001/escenarios/csv", json=ESCENARIOS)

    assert [p["codigo"] for p in cliente.get("/presupuestos").json()] == ["001"]


def test_el_csv_exige_al_menos_un_escenario(cliente, presupuesto_001):
    assert (
        cliente.post("/presupuestos/001/escenarios/csv", json={"escenarios": []}).status_code == 422
    )
