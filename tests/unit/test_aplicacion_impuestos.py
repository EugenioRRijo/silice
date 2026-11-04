"""Tarea 18 del plan vial: el IVA va sobre el total, nunca dentro del APU.

Oráculos hechos a mano (no salen del código que se prueba)."""

from __future__ import annotations

from decimal import Decimal

from aplicacion.impuestos import ALICUOTA_IVA, ResumenImpuestos, con_iva

D = Decimal


def test_la_alicuota_general_es_el_16_por_ciento_con_su_fuente_y_la_marca_de_cotejo() -> None:
    assert ALICUOTA_IVA.valor == D("0.16")
    assert "G.O. 6.395" in ALICUOTA_IVA.fuente
    assert "a cotejar con la Gaceta vigente" in ALICUOTA_IVA.fuente


def test_mil_da_iva_160_y_total_1160() -> None:
    assert con_iva(D(1000)) == ResumenImpuestos(D("1000.00"), D("160.00"), D("1160.00"))


def test_cinco_centesimas_dan_iva_un_centimo_mitad_hacia_arriba() -> None:
    # 0,05 x 0,16 = 0,008 -> 0,01
    resumen = con_iva(D("0.05"))
    assert resumen.iva == D("0.01") and resumen.total == D("0.06")


def test_el_redondeo_es_half_up_y_no_el_del_banquero() -> None:
    # 0,03125 x 0,16 = 0,005 exacto -> 0,01 (el redondeo del banquero daria 0,00)
    assert con_iva(D("0.03125")).iva == D("0.01")


def test_con_otra_alicuota_y_cero() -> None:
    assert con_iva(D(1000), D("0.08")).iva == D("80.00")
    assert con_iva(D(0)) == ResumenImpuestos(D("0.00"), D("0.00"), D("0.00"))


def test_el_subtotal_se_presenta_a_dos_decimales() -> None:
    assert con_iva(D("1586.61")) == ResumenImpuestos(D("1586.61"), D("253.86"), D("1840.47"))
