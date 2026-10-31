"""FCAS por componentes (plan vial, Tarea 17). Casos y cifras FICTICIOS salvo el oráculo publicado.

Oráculo a mano (Dodi y Salas, 2019, §4.2, su caso 1): 365 días calendario, 23,13 días de bonificación
y 217,28 días trabajados dan días pagados 388,13 y FCAS por días (388,13 − 217,28) ÷ 217,28 = 0,7863
(78,63 %, el valor que publican). Con un aporte patronal de 2 % del salario pagado:
(388,13 ÷ 217,28) × 1,02 − 1 = 0,8220 (0,822038…).
Con los componentes por defecto (80 + 100 + 36 + 72 = 288 días y aportes 2 + 2 + 2 + 11 + 9 = 26 %):
dias_pagados 653; (653 ÷ 217,28) × 1,26 − 1 = 2,7867 (3,005339… × 1,26 = 3,786727…).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from aplicacion.fcas import (
    COMPONENTES_FCAS,
    DIAS_CALENDARIO,
    ComponenteFCAS,
    calcular_fcas,
)

D = Decimal
CUATRO = D("0.0001")
BONIFICACION = ComponenteFCAS(
    "bonificaciones", "Bonificaciones (Dodi y Salas)", "dias", D("23.13"), "Dodi y Salas (2019), caso 1"
)
APORTE_2 = ComponenteFCAS("aporte_demo", "Aporte de demostración", "porcentaje", D("2"), "ficticio")


def _por_id(identificador: str) -> ComponenteFCAS:
    return next(c for c in COMPONENTES_FCAS if c.id == identificador)


def test_dodi_y_salas_sin_aportes() -> None:
    r = calcular_fcas((BONIFICACION,), D("365"), D("217.28"))
    assert r.dias_pagados == D("388.13")
    assert r.fcas_por_dias.quantize(CUATRO) == D("0.7863")
    assert abs(r.fcas_por_dias - D("0.786312")) < D("0.000001")
    assert r.fcas == r.fcas_por_dias  # sin aportes, el total es el de los días


def test_dodi_y_salas_con_un_aporte_de_2_por_ciento() -> None:
    r = calcular_fcas((BONIFICACION, APORTE_2), D("365"), D("217.28"))
    assert r.fcas.quantize(CUATRO) == D("0.8220")
    assert abs(r.fcas - D("0.822038")) < D("0.000001")
    assert r.fcas_por_dias.quantize(CUATRO) == D("0.7863")  # los aportes no cambian el de los días


def test_el_desglose_suma_el_total() -> None:
    r = calcular_fcas((BONIFICACION, APORTE_2), D("365"), D("217.28"))
    assert abs(sum(valor for _, valor in r.desglose) - r.fcas) < D("1E-20")
    identificadores = [i for i, _ in r.desglose]
    assert identificadores == ["dias_no_trabajados", "bonificaciones", "aporte_demo"]
    # a mano: (365 − 217,28) ÷ 217,28 = 0,6799… y 23,13 ÷ 217,28 = 0,1064…
    assert dict(r.desglose)["dias_no_trabajados"].quantize(CUATRO) == D("0.6799")
    assert dict(r.desglose)["bonificaciones"].quantize(CUATRO) == D("0.1065")


def test_el_bono_de_alimentacion_se_rechaza_con_su_motivo() -> None:
    with pytest.raises(ValueError, match="bono de alimentación"):
        ComponenteFCAS("bono_alimentacion", "Bono", "dias", D("10"), "ficticio")
    with pytest.raises(ValueError, match="dos veces"):
        ComponenteFCAS("bono_alimentacion", "Bono", "porcentaje", D("10"), "ficticio")


def test_un_componente_a_cotejar_se_avisa() -> None:
    dudoso = ComponenteFCAS("aporte_dudoso", "Aporte dudoso", "porcentaje", D("5"), "Decreto X — a cotejar")
    r = calcular_fcas((BONIFICACION, APORTE_2, dudoso), D("365"), D("217.28"))
    assert r.a_cotejar == ("aporte_dudoso",)
    assert calcular_fcas((BONIFICACION,), D("365"), D("217.28")).a_cotejar == ()


def test_los_componentes_por_defecto() -> None:
    ids = [c.id for c in COMPONENTES_FCAS]
    assert len(ids) == len(set(ids))
    assert "bono_alimentacion" not in ids
    assert {"paro_forzoso", "utilidades", "ivss", "pensiones"} <= set(ids)
    assert all(c.fuente.strip() and c.base in ("dias", "porcentaje") for c in COMPONENTES_FCAS)
    assert (_por_id("utilidades").base, _por_id("utilidades").valor) == ("dias", D("100"))
    assert "cláusula 48" in _por_id("utilidades").fuente
    assert (_por_id("paro_forzoso").base, _por_id("paro_forzoso").valor) == ("porcentaje", D("2"))
    assert "Régimen Prestacional de Empleo" in _por_id("paro_forzoso").fuente
    assert (_por_id("vacaciones_bono").valor, _por_id("garantia_prestaciones").valor) == (D("80"), D("72"))
    # Decisión de Eugenio (2026-10-31): pensiones 9 % activado y el IVSS 11 %, los dos «a cotejar»
    assert (_por_id("pensiones").base, _por_id("pensiones").valor) == ("porcentaje", D("9"))
    assert (_por_id("ivss").base, _por_id("ivss").valor) == ("porcentaje", D("11"))
    r = calcular_fcas(COMPONENTES_FCAS, DIAS_CALENDARIO, D("217.28"))
    assert r.a_cotejar == ("ivss", "pensiones")


def test_los_componentes_por_defecto_suman_a_mano() -> None:
    r = calcular_fcas(COMPONENTES_FCAS, D("365"), D("217.28"))
    assert r.dias_pagados == D("653")
    assert r.fcas.quantize(CUATRO) == D("2.7867")
    assert abs(sum(valor for _, valor in r.desglose) - r.fcas) < D("1E-20")


@pytest.mark.parametrize(
    "calendario,trabajados,motivo",
    [
        ("365", "0", "días trabajados"),
        ("365", "-5", "días trabajados"),
        ("0", "10", "días calendario"),
        ("365", "366", "no pueden pasar"),
    ],
)
def test_dias_imposibles_se_rechazan(calendario: str, trabajados: str, motivo: str) -> None:
    with pytest.raises(ValueError, match=motivo):
        calcular_fcas((BONIFICACION,), D(calendario), D(trabajados))


def test_componentes_repetidos_o_valor_negativo_se_rechazan() -> None:
    with pytest.raises(ValueError, match="repetido"):
        calcular_fcas((BONIFICACION, BONIFICACION), D("365"), D("217.28"))
    with pytest.raises(ValueError, match="negativo"):
        ComponenteFCAS("x", "X", "dias", D("-1"), "ficticio")
    with pytest.raises(ValueError, match="base"):
        ComponenteFCAS("x", "X", "semanas", D("1"), "ficticio")
    with pytest.raises(ValueError, match="fuente"):
        ComponenteFCAS("x", "X", "dias", D("1"), "  ")
