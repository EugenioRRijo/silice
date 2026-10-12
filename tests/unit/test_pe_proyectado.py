# tests/unit/test_pe_proyectado.py
"""SL-E5: punto de equilibrio proyectado (spec S2 §4.7; RF-77) y `equilibrio` extraído (SL-E5).

Los dos escenarios de la memoria `control_ob_s2.md` (sin reajuste y con el reajuste reconocido de
75,90), la frontera `PE' = V'` exacta, la coherencia con SF-E3 (una obra que va según el plan da el
mismo PE y la misma ubicación) y que la extracción de `equilibrio` no movió TI-001.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from core.budget import punto_equilibrio
from core.budget.control import construir_estado
from core.budget.curva import generar_curva
from core.budget.equilibrio import EstadoEquilibrio
from core.budget.valor_ganado import equilibrio_proyectado, indicadores, reproyectar
from tests.fixtures import control_ob_s2 as ob

D = Decimal
MONTOS = D("0.01")
CF = D(600)
VENTA = D(5060)
EAC = D(4480)
SIN_REAJUSTE, CON_REAJUSTE = D(0), D("75.90")


def _pe(*, cv, dias, reajuste, plan=ob.PLAN):
    presupuesto = ob.elaborar_ob_s2().presupuesto
    return equilibrio_proyectado(
        venta=VENTA,
        costo_variable=cv,
        costo_fijo=CF,
        dias_plan=20,
        dias_proyectados=dias,
        reajuste_reconocido=reajuste,
        curva=generar_curva(presupuesto, plan),
    )


def _reproyectado():
    return reproyectar(
        construir_estado(
            ob.instantanea(ob.v01_v02()), costo_real=ob.COSTO_REAL, precios=ob.precios_del_corte()
        )
    )


def test_aceptar_el_retraso_sin_reajuste_no_se_alcanza_en_6_019_66():
    pe = _pe(cv=EAC, dias=23, reajuste=SIN_REAJUSTE, plan=_reproyectado().plan)
    assert pe.estado is EstadoEquilibrio.NO_SE_ALCANZA
    assert abs(pe.punto - D("6019.66")) <= MONTOS
    assert (pe.venta, pe.costo_fijo) == (VENTA, D(690))


def test_aceptar_el_retraso_con_el_reajuste_reconocido_no_se_alcanza_en_5_402_91():
    pe = _pe(cv=EAC, dias=23, reajuste=CON_REAJUSTE, plan=_reproyectado().plan)
    assert pe.estado is EstadoEquilibrio.NO_SE_ALCANZA
    assert abs(pe.punto - D("5402.91")) <= MONTOS
    assert pe.venta == D("5135.90")


PLAN_DE_CUADRILLAS = [
    ("Semana 1", [("OB-A", D("0.4"))]),
    ("Semana 2", [("OB-A", D("0.5")), ("OB-B", D("0.3"))]),
    ("Semana 3", [("OB-A", D("0.1")), ("OB-B", D("0.54")), ("OB-C", D("0.72"))]),
    ("Semana 4", [("OB-B", D("0.16")), ("OB-C", D("0.28"))]),
]


def test_mas_cuadrillas_sin_reajuste_no_se_alcanza_con_cv_4600_y_cf_510():
    pe = _pe(cv=D(4600), dias=17, reajuste=SIN_REAJUSTE, plan=PLAN_DE_CUADRILLAS)
    assert pe.estado is EstadoEquilibrio.NO_SE_ALCANZA
    assert pe.costo_fijo == D(510) and abs(pe.punto - D("5610.00")) <= MONTOS


def test_mas_cuadrillas_con_el_reajuste_se_alcanza_en_4_887_68_y_se_ubica_en_s4():
    pe = _pe(cv=D(4600), dias=17, reajuste=CON_REAJUSTE, plan=PLAN_DE_CUADRILLAS)
    assert pe.estado is EstadoEquilibrio.CALCULADO
    assert abs(pe.punto - D("4887.68")) <= MONTOS
    assert abs(pe.porcentaje - D("95.17")) <= MONTOS
    assert pe.periodo.startswith("Semana 4")  # el acumulado llega a 82 % en S3 y a 100 % en S4


def test_pe_igual_a_v_exacto_se_alcanza_con_un_reajuste_de_50():
    """V' = 5110 = CV' + CF' = 4600 + 510: PE' = 5110 = V' exacto, se alcanza (frontera)."""
    pe = _pe(cv=D(4600), dias=17, reajuste=D(50), plan=PLAN_DE_CUADRILLAS)
    assert (pe.estado, pe.punto, pe.venta) == (EstadoEquilibrio.CALCULADO, D(5110), D(5110))
    assert pe.periodo.startswith("Semana 4")
    sin_un_centavo = _pe(cv=D(4600), dias=17, reajuste=D("49.99"), plan=PLAN_DE_CUADRILLAS)
    assert sin_un_centavo.estado is EstadoEquilibrio.NO_SE_ALCANZA


def test_cada_opcion_necesita_un_reajuste_minimo_igual_a_cv_mas_cf_menos_v():
    """Comprobación cruzada de la memoria: aceptar 110,00; cuadrillas 50,00; horas 165,3125."""
    minimos = {"aceptar": (EAC, 690), "cuadrillas": (D(4600), 510), "horas": (D("4595.3125"), 630)}
    esperados = {"aceptar": D("110.00"), "cuadrillas": D("50.00"), "horas": D("165.3125")}
    for nombre, (cv, cf) in minimos.items():
        assert cv + cf - VENTA == esperados[nombre]


def test_el_costo_fijo_se_causa_en_el_tiempo_cf_prima_es_cf_por_d_prima_sobre_d():
    assert _pe(cv=EAC, dias=20, reajuste=SIN_REAJUSTE).costo_fijo == CF
    assert _pe(cv=EAC, dias=10, reajuste=SIN_REAJUSTE).costo_fijo == D(300)


def test_sin_margen_el_pe_proyectado_no_existe():
    pe = _pe(cv=D(5060), dias=20, reajuste=SIN_REAJUSTE)
    assert pe.estado is EstadoEquilibrio.NO_EXISTE


def test_dias_del_plan_invalidos_se_rechazan():
    with pytest.raises(ValueError, match="1 o mas"):
        equilibrio_proyectado(
            venta=VENTA, costo_variable=EAC, costo_fijo=CF, dias_plan=0, dias_proyectados=1,
            reajuste_reconocido=SIN_REAJUSTE, curva=(),
        )  # fmt: skip


def test_una_obra_que_va_segun_el_plan_da_el_pe_de_sf_e3_con_su_misma_ubicacion():
    """EAC = BAC, D' = D, curva reproyectada = plan, sin reajuste: PE' = PE de SF-E3."""
    segun_el_plan = [
        ob.valuacion(
            dict(
                numero=f"V-0{n}", desde=desde, hasta=hasta, fecha=hasta, inspector=ob.INSPECTOR,
                lineas=lineas,
            ),
            n,
        )
        for n, (desde, hasta, lineas) in enumerate(
            [
                (date(2026, 11, 2), date(2026, 11, 6), [ob.LineaValuacion("OB-A", D(50))]),
                (
                    date(2026, 11, 9),
                    date(2026, 11, 13),
                    [ob.LineaValuacion("OB-A", D(50)), ob.LineaValuacion("OB-B", D(100))],
                ),
            ],
            start=1,
        )
    ]  # fmt: skip
    precios_base = ob.precios_del_corte().__class__("comprobacion", "base", ob.UNITARIOS_BASE)
    estado = construir_estado(
        ob.instantanea(segun_el_plan), costo_real=D(1500), precios=precios_base
    )
    ind = indicadores(estado)
    reproyeccion = reproyectar(estado)
    assert (ind.spi, ind.cpi, ind.eac_sistema, ind.ev == ind.pv) == (D(1), D(1), D(4000), True)
    assert reproyeccion.termino == 20
    presupuesto = ob.elaborar_ob_s2().presupuesto
    curva = generar_curva(presupuesto, reproyeccion.plan)
    assert curva == presupuesto.curva
    proyectado = equilibrio_proyectado(
        venta=presupuesto.total,
        costo_variable=ind.eac_sistema,
        costo_fijo=CF,
        dias_plan=20,
        dias_proyectados=reproyeccion.termino,
        reajuste_reconocido=D(0),
        curva=curva,
    )
    base = punto_equilibrio(presupuesto, ob.PARAMETROS)
    assert (proyectado.estado, proyectado.punto, proyectado.porcentaje) == (
        base.estado,
        base.punto,
        base.porcentaje,
    )
    assert (proyectado.periodo, proyectado.fraccion_periodo) == (
        base.periodo,
        base.fraccion_periodo,
    )
    assert abs(base.punto - D("2864.15")) <= MONTOS  # el PE base de OB-S2 (S3 §7.1)
