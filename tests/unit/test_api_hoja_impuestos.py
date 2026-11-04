"""Tarea 5b del rediseño F4: la vista `presupuesto` del borrador trae el IVA sobre su total.

El IVA se calcula con `aplicacion.impuestos.con_iva` sobre el total EXACTO de la vista, en la capa
de la API (`aplicacion/hoja.py` está congelado por el experimento). El APU no cambia y `total` sigue
siendo el costo sin IVA. Los oráculos están escritos a mano.
"""

from __future__ import annotations

from decimal import Decimal

from api.esquemas_hoja import vista_presupuesto_a_respuesta
from aplicacion.hoja_vista import VistaPresupuesto, monto

FUENTE = (
    "Ley del IVA, alícuota general: Decreto 3.584, G.O. 6.395 Ext., 17-08-2018 (16 %) "
    "— a cotejar con la Gaceta vigente"
)


def _vista(total: str) -> VistaPresupuesto:
    return VistaPresupuesto(filas=(), total=monto(Decimal(total)), moneda="Bs", vacio_mensaje=None)


def test_mil_bolivares_dan_160_de_iva_y_1160_con_iva() -> None:
    cuerpo = vista_presupuesto_a_respuesta(_vista("1000")).model_dump()

    assert cuerpo["total"]["texto"] == "1000.00"
    assert cuerpo["impuestos"] == {
        "subtotal": "1000.00",
        "iva": "160.00",
        "total": "1160.00",
        "alicuota": "0.16",
        "fuente_alicuota": FUENTE,
    }


def test_medio_centimo_del_iva_sube_y_se_calcula_sobre_el_total_exacto() -> None:
    # 0,03125 x 0,16 = 0,005 -> 0,01 (mitad hacia arriba); la base es 0,03 y el total 0,04.
    cuerpo = vista_presupuesto_a_respuesta(_vista("0.03125")).model_dump()

    assert cuerpo["impuestos"]["subtotal"] == "0.03"
    assert cuerpo["impuestos"]["iva"] == "0.01"
    assert cuerpo["impuestos"]["total"] == "0.04"


def test_el_iva_va_sobre_el_total_exacto_y_no_sobre_el_texto_redondeado() -> None:
    # 0,034: el texto es 0,03 (0,03 x 0,16 = 0,0048 -> 0,00) pero el exacto da 0,00544 -> 0,01.
    cuerpo = vista_presupuesto_a_respuesta(_vista("0.034")).model_dump()

    assert cuerpo["total"]["texto"] == "0.03"
    assert cuerpo["impuestos"]["iva"] == "0.01"
    assert cuerpo["impuestos"]["total"] == "0.04"
