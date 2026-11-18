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


def test_el_inicio_se_puede_elegir_y_las_fechas_se_corren_con_el():
    from datetime import date

    inicio = date(2026, 10, 5)  # lunes
    obra = generador.generar(12, 10, 5, semilla=7, inicio=inicio)
    assert obra.calendario.fecha_inicio == inicio
    assert obra.valuaciones[0].desde == inicio
    assert obra.valuaciones[-1].fecha == inicio + timedelta(weeks=5)
    # misma obra que con el inicio de siempre, solo corrida en el tiempo
    base = generador.generar(12, 10, 5, semilla=7)
    assert [v.lineas for v in obra.valuaciones] == [v.lineas for v in base.valuaciones]


def test_la_demo_de_control_siembra_valuaciones_y_costos_que_no_pasan_de_hoy(tmp_path):
    # Prueba en vivo del 2026-11-18, hallazgo 1: la demo sembraba valuaciones hasta el 04/12.
    from datetime import date

    import start
    from core.budget.valuaciones import valuaciones_registradas
    from core.catalog import abrir_sesion, crear_motor

    hoy = date(2026, 11, 18)
    destino = tmp_path / "obra_control.db"
    start.sembrar_obra_control(destino, hoy=hoy)
    motor = crear_motor(f"sqlite:///{destino.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            valuaciones = valuaciones_registradas(sesion, generador.NOMBRE)
            assert len(valuaciones) == 5
            assert all(v.hasta <= hoy and v.fecha <= hoy for v in valuaciones)
            # la última se firmó esta misma semana: la demo queda al día
            assert hoy - valuaciones[-1].fecha < timedelta(weeks=1)
            from sqlalchemy import select

            from core import models

            assert all(c.fecha <= hoy for c in sesion.scalars(select(models.CostoReal)))
    finally:
        motor.dispose()


def test_la_demo_de_control_trae_historia_didactica_de_la_tasa_para_riesgo(tmp_path):
    # Prueba en vivo del 2026-11-18, hallazgo 4: Riesgo no corría en ningún caso de la demo
    # («solo hay 0 meses completos; se necesitan 12»). La tasa es ficticia y lo dice (NORMAS §1).
    from datetime import date

    from sqlalchemy import select

    import start
    from aplicacion.riesgo.proyeccion import (
        MINIMO_DE_MESES,
        SERIE_TASA,
        ParametrosProyeccion,
        historia_para_proyectar,
        meses_completos,
    )
    from aplicacion.riesgo.series import MapaSeries
    from core import models
    from core.catalog import abrir_sesion, crear_motor

    hoy = date(2026, 11, 18)
    destino = tmp_path / "obra_control.db"
    start.sembrar_obra_control(destino, hoy=hoy)
    motor = crear_motor(f"sqlite:///{destino.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            p = ParametrosProyeccion(inicio=start.inicio_de_la_demo(hoy))
            historia = historia_para_proyectar(sesion, MapaSeries({}), p)
            completos = meses_completos(historia, [SERIE_TASA], p)
            assert len(completos) >= int(MINIMO_DE_MESES.valor)
            (importacion,) = sesion.scalars(select(models.ImportacionIndice))
            assert "ficticia" in importacion.fuente and "didáctica" in importacion.fuente
            # ninguna observación es del futuro
            assert all(v.fecha <= hoy for v in sesion.scalars(select(models.ValorIndice)))
    finally:
        motor.dispose()
