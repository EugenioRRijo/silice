"""UC‑08 por HTTP: escenarios de sensibilidad sobre un presupuesto guardado (RF‑30, RF‑31).

Cablea el hallazgo 1 de la bitácora del cierre de UC‑08: los escenarios existían solo en
`core.budget`. El contrato que estas pruebas exigen de `POST /presupuestos/{codigo}/escenarios`:

- devuelve el total del base y una entrada por escenario con total, variación (absoluta y
  porcentual), hallazgos de su auditoría y el detalle por partida (flujo principal, paso 3);
- no persiste nada: el base queda como única versión guardada (RF‑30);
- un parámetro fuera de rango se rechaza con 422 por las invariantes del contrato (flujo 1a).

Importes esperados sin circularidad: la subida de cemento y arena reproduce los 50,082615 USD
calculados a mano para UC‑02 (1,66 m3 × 30,17025); y con la utilidad al 20 % la variación
porcentual del total es exactamente 100 × (1,20/1,10 − 1) = 9,0909… % porque la utilidad
encadena en cascada sobre todos los renglones por igual.
"""

from __future__ import annotations

import pytest

from scripts.seed import NOMBRE_PROYECTO
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import items_auditados

RUTA_ESCENARIOS = "/presupuestos/001/escenarios"


@pytest.fixture
def presupuesto_001(cliente, items_payload):
    """El presupuesto de la línea base guardado vía API (mismo cómputo que test_api)."""
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


def test_base_mas_una_entrada_por_escenario_con_detalle(cliente, presupuesto_001):
    respuesta = cliente.post(
        RUTA_ESCENARIOS,
        json={
            "escenarios": [
                {
                    "nombre": "cemento y arena",
                    "precios": {"Cemento Portland": "18", "Arena lavada": "33"},
                },
                {"nombre": "utilidad 20", "utilidad": "0.20"},
            ]
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["codigo_base"] == "001"
    assert cuerpo["total_base"] == presupuesto_001["total"]

    escenarios = {escenario["nombre"]: escenario for escenario in cuerpo["escenarios"]}
    assert len(escenarios) == 2

    caro = escenarios["cemento y arena"]
    assert caro["variacion"] == "50.08"  # 1,66 m3 x 30,17025 USD/m3, a dos decimales
    assert caro["insumos_variados"] == 2
    assert len(caro["partidas"]) == len(items_auditados())

    utilidad = escenarios["utilidad 20"]
    assert utilidad["variacion_pct"] == "9.09"  # 100 x (1,20/1,10 - 1)
    assert utilidad["insumos_variados"] == 0


def test_los_escenarios_no_persisten_ninguna_version(cliente, presupuesto_001):
    respuesta = cliente.post(
        RUTA_ESCENARIOS,
        json={"escenarios": [{"nombre": "efimero", "administracion": "0.20"}]},
    )
    assert respuesta.status_code == 200

    guardados = cliente.get("/presupuestos").json()
    assert [presupuesto["codigo"] for presupuesto in guardados] == ["001"]


def test_parametro_fuera_de_rango_se_rechaza_por_el_contrato(cliente, presupuesto_001):
    respuesta = cliente.post(
        RUTA_ESCENARIOS,
        json={"escenarios": [{"nombre": "invalido", "utilidad": "-0.10"}]},
    )
    assert respuesta.status_code == 422
    assert "utilidad" in respuesta.json()["detalle"]
