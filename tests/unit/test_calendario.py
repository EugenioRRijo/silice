# tests/unit/test_calendario.py
"""SL-E4: el calendario de la obra (spec S2 §4.1, S2-R9): lunes a viernes menos feriados."""

from datetime import date

import pytest

from core.budget.calendario import dia_habil, dias_habiles, es_habil, numero_de_dia, periodo_de

LUNES = date(2026, 11, 2)  # inicio de OB-S2
FERIADOS = frozenset({date(2026, 11, 4)})  # un miercoles ficticio


def test_el_fin_de_semana_y_el_feriado_no_son_habiles():
    assert es_habil(date(2026, 11, 6))  # viernes
    assert not es_habil(date(2026, 11, 7))  # sabado
    assert not es_habil(date(2026, 11, 8))  # domingo
    assert es_habil(date(2026, 11, 4))
    assert not es_habil(date(2026, 11, 4), FERIADOS)


def test_cuatro_semanas_de_cinco_dias_son_veinte_dias_habiles():
    assert dias_habiles(LUNES, date(2026, 11, 27)) == 20
    assert dias_habiles(LUNES, date(2026, 11, 1)) == 0  # desde > hasta


def test_el_dia_habil_veinte_es_el_viernes_27_y_el_veintitres_el_2_de_diciembre():
    assert dia_habil(LUNES, 1) == LUNES
    assert dia_habil(LUNES, 20) == date(2026, 11, 27)
    assert dia_habil(LUNES, 23) == date(2026, 12, 2)
    assert dia_habil(LUNES, 25) == date(2026, 12, 4)


def test_un_feriado_corre_el_calendario_un_dia():
    assert dia_habil(LUNES, 3, FERIADOS) == date(2026, 11, 5)  # el 4 no cuenta
    assert numero_de_dia(LUNES, date(2026, 11, 5), FERIADOS) == 3


def test_el_fin_de_semana_pertenece_al_ultimo_dia_habil_anterior():
    assert numero_de_dia(LUNES, date(2026, 11, 7)) == 5
    assert numero_de_dia(LUNES, date(2026, 11, 8)) == 5
    assert numero_de_dia(LUNES, date(2026, 11, 9)) == 6


def test_el_inicio_en_sabado_arranca_el_lunes():
    sabado = date(2026, 10, 31)
    assert dia_habil(sabado, 1) == LUNES
    assert numero_de_dia(sabado, sabado) == 0


@pytest.mark.parametrize(
    ("fecha", "periodo"),
    [
        (date(2026, 11, 1), 0),  # antes del inicio
        (date(2026, 11, 2), 1),
        (date(2026, 11, 6), 1),  # ultimo dia del periodo 1
        (date(2026, 11, 9), 2),  # primer dia del periodo 2
        (date(2026, 11, 13), 2),
        (date(2026, 11, 27), 4),
        (date(2026, 12, 2), 5),  # pasa del plan
    ],
)
def test_periodo_de_con_semanas_de_cinco_dias(fecha, periodo):
    assert periodo_de(LUNES, 5, fecha) == periodo


def test_numeros_invalidos_se_rechazan():
    with pytest.raises(ValueError, match="1 o mayor"):
        dia_habil(LUNES, 0)
    with pytest.raises(ValueError, match="1 o mas"):
        periodo_de(LUNES, 0, LUNES)
