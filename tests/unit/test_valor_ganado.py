# tests/unit/test_valor_ganado.py
"""SL-E5: valor ganado y separación del desvío de control (spec S2 §4.2, §4.3; RF-75, RF-76).

El oráculo es la memoria `control_ob_s2.md` (§7.1), a ± 0,01 en montos y ± 0,0001 en índices;
la identidad `CV = precio + consumo` se exige exacta, con `Decimal`, también sobre la obra grande
del generador de RNF-15. Puras: sin base de datos.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.budget.control import construir_estado
from core.budget.valor_ganado import (
    PERSPECTIVA_PRECIO,
    indicadores,
    precios_por_escalatoria,
    separar_desvio,
)
from tests.fixtures import control_ob_s2 as ob

D = Decimal
MONTOS = D("0.01")
INDICES = D("0.0001")


PRECIOS = ob.precios_del_corte()


def _estado(valuaciones=None, *, corte=ob.CORTE, costo_real=ob.COSTO_REAL, precios=PRECIOS):
    instantanea = ob.instantanea(ob.v01_v02() if valuaciones is None else valuaciones, corte=corte)
    return construir_estado(instantanea, costo_real=costo_real, precios=precios)


def test_la_tabla_de_la_memoria_ob_s2():
    ind = indicadores(_estado())
    assert (ind.bac, ind.pv, ind.ev, ind.ac) == (D(4000), D(1500), D(1200), D(1280))
    assert (ind.sv, ind.cv) == (D(-300), D(-80))
    assert abs(ind.spi - D("0.8000")) <= INDICES
    assert abs(ind.cpi - D("0.9375")) <= INDICES
    assert abs(ind.cpi_corte - D("0.984375")) <= INDICES
    assert abs(ind.eac_sistema - D("4480.00")) <= MONTOS
    assert abs(ind.eac_indice - D("4266.67")) <= MONTOS
    assert abs(ind.vac - D("-480.00")) <= MONTOS
    assert ind.termino_indice == 25  # techo de 20 / 0,80 = dia habil 25 = 2026-12-04
    assert ind.no_disponible == {}


def test_la_separacion_del_desvio_de_la_memoria_y_su_identidad_exacta():
    estado = _estado()
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert (sep.plazo, sep.precio, sep.consumo) == (D(-300), D(-60), D(-20))
    assert sep.precio + sep.consumo == ind.cv  # exacta, no a +- 0,01
    assert (sep.vac_precio, sep.vac_consumo) == (D(-410), D(-70))
    assert sep.vac_precio + sep.vac_consumo == ind.vac
    assert (sep.metodo, sep.fuente) == ("comprobacion", "version revalorada ficticia")


def test_una_valuacion_registrada_cuenta_en_ev_sin_otro_paso():
    assert indicadores(_estado()).ev == D(1200)
    assert indicadores(_estado(ob.v01_v02()[:1])).ev == D(400)  # solo V-01: A 40 x 10


def test_lo_valuado_sobre_lo_presupuestado_no_gana_valor_s2_r8():
    exceso = ob.valuacion(ob.VS, 3)
    estado = _estado([*ob.v01_v02(), exceso], corte=ob.CORTE_DE_VS)
    assert estado.ejecutado["OB-B"] == D(210)
    assert estado.cantidad_ejecutada(next(p for p in estado.partidas if p.codigo == "OB-B")) == D(
        200
    )
    # EV de B: min(210, 200) x 5; A 90 x 10; C 10 x 20; D no presupuestada: nada.
    assert indicadores(estado).ev == D(900) + D(1000) + D(200)


def test_corte_a_mitad_de_periodo_prorratea_el_plan_por_dias_habiles():
    estado = _estado(corte=date(2026, 11, 11))  # dia habil 8: 3 de 5 dias de la semana 2
    assert estado.dia == 8
    ind = indicadores(estado)
    # A: 0,5 + 0,5 x 3/5 = 0,8 -> 800; B: 0,5 x 3/5 = 0,3 -> 300; C: aun no.
    assert ind.pv == D(1100)


def test_antes_de_todo_trabajo_planificado_pv_es_cero_y_spi_no_aplica():
    ind = indicadores(_estado([], corte=date(2026, 11, 1)))
    assert (ind.pv, ind.ev, ind.spi, ind.termino_indice) == (0, 0, None, None)
    assert "PV = 0" in ind.no_disponible["SPI"]


def test_sin_costos_reales_cpi_no_aplica():
    ind = indicadores(_estado(costo_real=D(0)))
    assert ind.ac == 0 and ind.cpi is None and ind.eac_indice is None and ind.eac_sistema is None
    assert "AC = 0" in ind.no_disponible["CPI"]


def test_un_costo_real_sin_tasa_deja_el_ac_y_lo_que_depende_de_el_no_disponible():
    estado = replace(
        _estado(costo_real=None), motivo_costo="sin tasa aplicable para: 500 Bs del 2026-11-13"
    )
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert (ind.ac, ind.cv, ind.cpi, ind.eac_indice, ind.eac_sistema, ind.vac) == (None,) * 6
    assert "sin tasa aplicable" in ind.no_disponible["AC"]
    assert (sep.consumo, sep.vac_consumo) == (None, None)
    assert sep.precio == D(-60) and sep.vac_precio == D(-410)  # solo dependen de los precios
    assert (ind.pv, ind.ev, ind.sv) == (D(1500), D(1200), D(-300))  # PV, EV, SPI intactos
    assert abs(ind.spi - D("0.8")) <= INDICES


def test_sin_precios_del_corte_la_separacion_no_esta_disponible_y_lo_demas_funciona():
    estado = _estado(precios=None)
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert (ind.eac_sistema, ind.vac) == (None, None)
    assert (sep.precio, sep.consumo, sep.vac_precio) == (None, None, None)
    assert "sin precios del corte" in sep.no_disponible["precio"]
    assert ind.cpi == D("0.9375") and ind.spi == D("0.8")


def test_una_partida_ejecutada_sin_precio_del_corte_deja_la_separacion_no_disponible():
    sin_b = replace(
        PRECIOS,
        unitarios={k: v for k, v in PRECIOS.unitarios.items() if k != "OB-B"},
    )
    sep = separar_desvio(_estado(precios=sin_b))
    assert (sep.precio, sep.consumo) == (None, None)
    assert "OB-B" in sep.no_disponible["precio"]


def test_perspectiva_precio_el_consumo_es_cero_por_construccion():
    pu = {codigo: u * D("1.265") for codigo, u in ob.UNITARIOS_DEL_CORTE.items()}
    precios = replace(PRECIOS, unitarios=pu)
    instantanea = ob.instantanea(ob.v01_v02(), perspectiva=PERSPECTIVA_PRECIO)
    estado = construir_estado(instantanea, costo_real=None, precios=precios)
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert ind.ev == D(1200) * D("1.265")
    assert sep.consumo == 0
    assert sep.precio + sep.consumo == ind.cv


def test_los_precios_por_escalatoria_aplican_k_y_r_por_partida():
    unitarios = {"OB-A": D(10), "OB-B": D(5)}
    corte = precios_por_escalatoria(
        unitarios, {"OB-A": D("1.10"), "OB-B": D("1.00")}, D("0.10"), "S1"
    )
    assert corte.metodo == "escalatoria"
    assert corte.unitarios == {"OB-A": D(10) * (1 + D("0.10") * D("0.90")), "OB-B": D(5)}
    with pytest.raises(ValueError, match="falta el coeficiente K de las partidas OB-B"):
        precios_por_escalatoria(unitarios, {"OB-A": D(1)}, D(0), "S1")
    with pytest.raises(ValueError, match="R va en"):
        precios_por_escalatoria(unitarios, {"OB-A": D(1), "OB-B": D(1)}, D(1), "S1")


def test_un_estado_rechaza_perspectiva_y_dias_invalidos():
    base = _estado()
    with pytest.raises(ValueError, match="costo o precio"):
        replace(base, perspectiva="otra")
    with pytest.raises(ValueError, match="1 o mas"):
        replace(base, dias_por_periodo=0)
