# tests/unit/test_generar_obra_control.py
"""El generador determinista de la obra grande del control (spec S2 §3.3, RNF-15)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from core.budget.control import construir_estado
from core.budget.curva import generar_curva
from core.budget.valor_ganado import indicadores, reproyectar, separar_desvio
from core.verification import auditar
from core.verification.valuaciones import InstantaneaDeControl, PartidaBase, reglas_de_control
from scripts import generar_obra_control as generador
from tests.fixtures import control_ob_s2 as ob

D = Decimal


def test_la_misma_semilla_da_la_misma_obra_y_otra_semilla_otra():
    primera = generador.generar(40, 12, 6, semilla=3)
    repetida = generador.generar(40, 12, 6, semilla=3)
    otra = generador.generar(40, 12, 6, semilla=4)
    assert primera.plan == repetida.plan and primera.valuaciones == repetida.valuaciones
    assert primera.presupuesto.total == repetida.presupuesto.total
    assert primera.presupuesto.total != otra.presupuesto.total


def test_el_tamano_de_la_spec_son_500_partidas_52_periodos_y_26_valuaciones_semanales():
    obra = generador.generar()
    assert len(obra.presupuesto.partidas) == 500 and len(obra.plan) == 52
    assert len(obra.valuaciones) == len(obra.costos) == 26
    assert obra.valuaciones[0].desde == generador.INICIO
    assert (
        obra.corte == obra.valuaciones[-1].hasta == generador.INICIO + timedelta(weeks=25, days=4)
    )


def test_el_plan_de_cada_partida_suma_exactamente_uno_y_la_curva_cierra_en_el_total():
    obra = generador.generar(60, 20, 10, semilla=1)
    curva = generar_curva(obra.presupuesto, obra.plan)
    assert curva[-1].acumulado == obra.presupuesto.total


def test_las_valuaciones_son_consecutivas_sin_huecos_ni_solapes_y_sin_excesos():
    obra = generador.generar(80, 20, 10, semilla=2)
    for anterior, siguiente in zip(obra.valuaciones, obra.valuaciones[1:], strict=False):
        assert siguiente.desde == anterior.desde + timedelta(weeks=1)
    partidas = tuple(
        PartidaBase(
            p.item.codigo_partida, p.item.cantidad, p.resultado.costo_directo, p.item.origen_id
        )
        for p in obra.presupuesto.partidas
    )
    instantanea = InstantaneaDeControl(
        obra.corte, generador.INICIO, partidas, obra.valuaciones, lambda a, b: 0
    )
    informe = auditar(obra.presupuesto, reglas_de_control(instantanea))
    graves = [h for h in informe.hallazgos if h.severidad.name == "ERROR"]
    assert graves == []  # R13 y R14 no encuentran errores en lo generado


def test_la_obra_generada_se_puede_controlar_y_reproyectar():
    obra = generador.generar(60, 20, 10, semilla=5)
    instantanea = ob.instantanea(obra.valuaciones, corte=obra.corte, costos=obra.costos)
    instantanea = replace(
        instantanea,
        presupuesto=obra.presupuesto,
        plan=obra.plan,
        linea_base=replace(instantanea.linea_base, calendario=obra.calendario),
    )
    costo = sum((c.monto for c in obra.costos), D(0))
    estado = construir_estado(instantanea, costo_real=costo, precios=obra.precios)
    ind = indicadores(estado)
    reproyeccion = reproyectar(estado)
    assert ind.spi is not None and ind.cpi is not None and ind.eac_sistema is not None
    assert reproyeccion.termino is not None and reproyeccion.termino >= estado.dia
    curva = generar_curva(obra.presupuesto, reproyeccion.plan)
    assert curva[-1].acumulado == obra.presupuesto.total  # el plan reproyectado es valido


def test_la_identidad_cv_igual_precio_mas_consumo_se_cumple_en_la_obra_del_generador():
    obra = generador.generar(partidas=60, periodos=20, valuaciones=10, semilla=7)
    instantanea = ob.instantanea(obra.valuaciones, corte=obra.corte, costos=[])
    instantanea = replace(
        instantanea,
        presupuesto=obra.presupuesto,
        plan=obra.plan,
        linea_base=replace(instantanea.linea_base, calendario=obra.calendario),
        costos=obra.costos,
    )
    costo = sum((c.monto for c in obra.costos), D(0))
    estado = construir_estado(instantanea, costo_real=costo, precios=obra.precios)
    ind = indicadores(estado)
    sep = separar_desvio(estado, ind)
    assert ind.spi is not None and 0 < ind.spi
    assert sep.precio + sep.consumo == ind.cv
    assert sep.vac_precio + sep.vac_consumo == ind.vac
