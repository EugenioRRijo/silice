"""Oráculo: tests/fixtures/memorias/s1_conversion.md (S1 §9.1.1)."""
from datetime import date
from decimal import Decimal, localcontext

import pytest

from core.catalog.moneda import TasaDeclarada, convertir, erosion, erosion_por_indice

D = Decimal

T0, T1 = D("633.3644"), D("860.18")


def test_memoria_de_conversion_con_28_digitos():
    with localcontext(prec=6):  # el resultado no depende del contexto global
        e = erosion(D("1000"), "Bs", T0, T1)
        assert convertir(D("1000"), "Bs", "USD", T0) == D("1.578869920696521623255111907")
        assert convertir(D("1000"), "Bs", "USD", T1) == D("1.162547373805482573414866656")
    assert e.usd == D("0.416322546891039049840245251")
    assert e.bs == D("358.112328384733969891582160")
    assert e.porcentaje.quantize(D("0.0001")) == D("0.2637")
    assert e.porcentaje.quantize(D("0.0001")) != D("0.3581")  # no es 358,11 / 1 000


def test_usd_erosion_cero_declarada_y_misma_moneda_no_convierte():
    e = erosion(D("30"), "USD", T0, T1)
    assert (e.usd, e.bs) == (D(0), D(0)) and "USD" in e.nota
    assert convertir(D("7.5"), "USD", "USD", T1) == D("7.5")
    assert convertir(D("1"), "USD", "Bs", T1) == T1


def test_erosion_por_indice_es_columna_aparte():
    assert erosion_por_indice(D("1000"), D("200"), D("230")) == D("150")


@pytest.mark.parametrize("valor, fuente", [(D("0"), "importacion:1"), (D("860.18"), " ")])
def test_sin_tasa_o_sin_fuente_se_rechaza(valor, fuente):
    with pytest.raises(ValueError):
        TasaDeclarada(valor, date(2026, 10, 1), fuente)
