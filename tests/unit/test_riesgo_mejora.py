"""Tarea 15 del plan vial: informe de mejora de la estimación. Cifras FICTICIAS.

Oráculo a mano. Con costo final real 130, presupuesto original 100 y estimación de Sílice 125:

- error del original = |100 − 130| ÷ 130 × 100 = 30 ÷ 130 × 100 = 23,0769… → 23,08;
- error de Sílice = |125 − 130| ÷ 130 × 100 = 5 ÷ 130 × 100 = 3,8461… → 3,85;
- mejora en puntos porcentuales = 23,08 − 3,85 = 19,23 (los dos errores ya redondeados, que son los
  que ve la persona; sin redondear daría 19,2307… → 19,23 también).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from aplicacion.riesgo.mejora import Mejora, mejora_de_estimacion

D = Decimal


def test_oraculo_del_plan() -> None:
    assert mejora_de_estimacion(D("130"), D("100"), D("125")) == Mejora(
        D("23.08"), D("3.85"), D("19.23")
    )


def test_la_mejora_es_la_resta_de_los_errores_que_se_muestran() -> None:
    """real 3: |1 − 3| ÷ 3 = 66,666… → 66,67 y |2 − 3| ÷ 3 = 33,333… → 33,33; la resta de lo
    mostrado es 33,34 (sin redondear sería 33,333… → 33,33): se muestra lo que suma."""
    m = mejora_de_estimacion(D("3"), D("1"), D("2"))
    assert (m.error_original_pct, m.error_silice_pct, m.mejora_pp) == (
        D("66.67"),
        D("33.33"),
        D("33.34"),
    )


def test_sobreestimar_tambien_es_error() -> None:
    """El error es en valor absoluto: 150 sobre 100 reales es 50 %, igual que 50."""
    arriba = mejora_de_estimacion(D("100"), D("150"), D("110"))
    abajo = mejora_de_estimacion(D("100"), D("50"), D("90"))
    assert arriba == abajo == Mejora(D("50.00"), D("10.00"), D("40.00"))


def test_silice_peor_que_el_original_da_mejora_negativa() -> None:
    """Original 120 (error 20 %) y Sílice 70 (error 30 %): la mejora es −10, no se esconde."""
    m = mejora_de_estimacion(D("100"), D("120"), D("70"))
    assert m == Mejora(D("20.00"), D("30.00"), D("-10.00"))


def test_empate_da_mejora_cero() -> None:
    m = mejora_de_estimacion(D("100"), D("90"), D("110"))
    assert m.mejora_pp == D("0.00")


def test_estimacion_exacta_da_error_cero() -> None:
    m = mejora_de_estimacion(D("80"), D("100"), D("80"))
    assert m == Mejora(D("25.00"), D("0.00"), D("25.00"))


def test_redondea_mitad_hacia_arriba() -> None:
    """|100,5 − 200| ÷ 200 × 100 = 49,75 exacto y |100,25 − 200| ÷ 200 × 100 = 49,875 → 49,88."""
    assert mejora_de_estimacion(D("200"), D("100.5"), D("100.25")).error_silice_pct == D("49.88")
    assert mejora_de_estimacion(D("200"), D("100.5"), D("100.25")).error_original_pct == D("49.75")


@pytest.mark.parametrize("real", [D("0"), D("-130")])
def test_real_cero_o_negativo_se_rechaza(real: Decimal) -> None:
    with pytest.raises(ValueError, match="costo final real"):
        mejora_de_estimacion(real, D("100"), D("125"))


@pytest.mark.parametrize("original, silice", [(D("-1"), D("125")), (D("100"), D("-1"))])
def test_estimaciones_negativas_se_rechazan(original: Decimal, silice: Decimal) -> None:
    with pytest.raises(ValueError, match="no puede ser negativ"):
        mejora_de_estimacion(D("130"), original, silice)
