"""Integridad de la línea base: la transcripción del PDF es coherente consigo misma y con el caso.

No prueba el motor de costos (eso es test_costing.py); prueba que los DATOS contra los que se medirá
el motor y el verificador son los del presupuesto auditado. Permanece verde todo el proyecto.
"""

from decimal import Decimal

import pytest

from tests.fixtures import apu_linea_base as lb


def _codigo(apu):
    return apu.codigo_partida


def test_hay_cinco_apu_con_codigos_unicos(apus_linea_base):
    codigos = {apu.codigo_partida for apu in apus_linea_base}
    assert len(apus_linea_base) == 5
    assert len(codigos) == 5
    assert set(lb.PRECIO_UNITARIO_ESPERADO) == codigos
    assert set(lb.SUBTOTALES_ESPERADOS) == codigos


@pytest.mark.parametrize("apu", lb.APUS_LINEA_BASE, ids=_codigo)
def test_las_lineas_suman_los_subtotales_del_pdf(apu):
    esperado = lb.SUBTOTALES_ESPERADOS[apu.codigo_partida]
    assert sum((m.total for m in apu.materiales), Decimal(0)) == esperado["materiales"]
    assert sum((e.total for e in apu.equipos), Decimal(0)) == esperado["equipos_total"]
    assert sum((o.total for o in apu.mano_obra), Decimal(0)) == esperado["sueldos"]
    assert apu.total_obreros == esperado["obreros"]


def test_el_presupuesto_auditado_suma_1586_61(presupuesto_auditado):
    assert sum((linea.total for linea in presupuesto_auditado), Decimal(0)) == Decimal("1586.61")
    assert lb.TOTAL_PRESUPUESTO_AUDITADO == Decimal("1586.61")


def test_cada_linea_del_presupuesto_usa_el_pu_de_su_apu(presupuesto_auditado):
    for linea in presupuesto_auditado:
        assert linea.precio_unitario == lb.PRECIO_UNITARIO_ESPERADO[linea.codigo_partida]


def test_la_curva_auditada_cierra_al_99_30_por_ciento(curva_auditada):
    """Hallazgo 3: la curva acumula 1 575,50 frente a un presupuesto de 1 586,61."""
    acumulado = Decimal(0)
    for punto in curva_auditada:
        acumulado += punto.monto
        assert punto.acumulado == acumulado, punto.periodo
    assert acumulado == lb.TOTAL_CURVA_AUDITADA == Decimal("1575.50")
    porcentaje = (acumulado / lb.TOTAL_PRESUPUESTO_AUDITADO * 100).quantize(Decimal("0.01"))
    assert porcentaje == lb.PORCENTAJE_CIERRE_CURVA == Decimal("99.30")
    assert lb.TOTAL_PRESUPUESTO_AUDITADO - acumulado == Decimal("11.11")


def test_las_unidades_del_computo_no_coinciden_con_las_del_apu(presupuesto_auditado):
    """Hallazgo 4 (tubería) y hallazgo adicional 8 (encofrado): material para la regla R3."""
    unidad_apu = {apu.codigo_partida: apu.unidad for apu in lb.APUS_LINEA_BASE}
    discrepantes = {
        linea.codigo_partida
        for linea in presupuesto_auditado
        if linea.unidad_computo != unidad_apu[linea.codigo_partida]
    }
    assert discrepantes == {"LB-02-TUB", "LB-03-ENC"}


def test_geometria_de_tanquilla_y_cantidades_corregidas():
    """Hallazgos 1 y 2: lo que la memoria calcula por tanquilla vs lo que el cómputo multiplicó."""
    for codigo, por_tanquilla in lb.CANTIDAD_POR_TANQUILLA_MEMORIA.items():
        assert por_tanquilla * lb.N_TANQUILLAS == lb.COMPUTO_CORREGIDO[codigo]
        assert lb.CANTIDAD_POR_TANQUILLA_USADA[codigo] != por_tanquilla
    usado = {linea.codigo_partida: linea.cantidad for linea in lb.PRESUPUESTO_AUDITADO}
    for codigo, por_tanquilla in lb.CANTIDAD_POR_TANQUILLA_USADA.items():
        assert por_tanquilla * lb.N_TANQUILLAS == usado[codigo]
    assert lb.COMPUTO_CORREGIDO == {"LB-03-ENC": Decimal("17.92"), "LB-04-CON": Decimal("0.896")}


def test_la_memoria_de_excavacion_cuadra():
    zanja = lb.LONGITUD_TUBERIA_M * lb.ZANJA["ancho"] * lb.ZANJA["profundidad"]
    assert zanja == lb.ZANJA["volumen"] == Decimal("7.68")
    assert sum(lb.TRAMOS_TUBERIA_M, Decimal(0)) == lb.LONGITUD_TUBERIA_M
    fosos = lb.N_TANQUILLAS * lb.VOLUMEN_FOSO_TANQUILLA
    cantidades = {linea.codigo_partida: linea.cantidad for linea in lb.PRESUPUESTO_AUDITADO}
    excavacion = cantidades["LB-01-EXC"]
    assert zanja + fosos == excavacion == Decimal("9.74")


def test_hay_siete_inconsistencias_numeradas_con_regla_asignada():
    assert [i.numero for i in lb.INCONSISTENCIAS] == [1, 2, 3, 4, 5, 6, 7]
    assert {i.regla for i in lb.INCONSISTENCIAS} == {"R1", "R2", "R3", "R4", "R5", "R6"}
    assert {i.regla for i in lb.HALLAZGOS_ADICIONALES} == {"R3", "R7"}
    codigos = {apu.codigo_partida for apu in lb.APUS_LINEA_BASE}
    for inconsistencia in lb.INCONSISTENCIAS + lb.HALLAZGOS_ADICIONALES:
        assert inconsistencia.codigo_partida is None or inconsistencia.codigo_partida in codigos


def test_la_depreciacion_del_vehiculo_es_inconsistente_entre_apu():
    """Hallazgo 7: material para la regla R6."""
    factores = {
        apu.codigo_partida: equipo.depreciacion
        for apu in lb.APUS_LINEA_BASE
        for equipo in apu.equipos
        if equipo.descripcion == "Vehículo de transporte"
    }
    assert len(factores) == 5
    assert factores.pop("LB-02-TUB") == Decimal("0.03")
    assert set(factores.values()) == {Decimal("1.00")}


def test_el_total_exacto_redondeado_es_el_del_pdf():
    """`TOTAL_EXACTO_LINEA_BASE` es el total del motor; a dos decimales, el 1 586,61 auditado."""
    from core.verification.informe import DECIMALES_PRESENTACION
    from core.verification.texto import formatear_decimal

    total = formatear_decimal(lb.TOTAL_EXACTO_LINEA_BASE, DECIMALES_PRESENTACION)
    assert total == str(lb.TOTAL_PRESUPUESTO_AUDITADO)


def test_precio_de_insumo_lee_la_transcripcion_del_pdf():
    concreto = {linea.descripcion: linea.precio for linea in lb.APU_CONCRETO.materiales}
    assert lb.precio_de_insumo("Cemento Portland") == concreto["Cemento Portland"]
    with pytest.raises(KeyError, match="Cemento blanco"):
        lb.precio_de_insumo("Cemento blanco")


def test_precio_de_insumo_rechaza_un_homonimo_con_precios_distintos():
    """`Pala` vale 10 en un APU y 15 en otro (docs/modelo_datos.md §6): no hay un precio único."""
    with pytest.raises(ValueError, match="Pala"):
        lb.precio_de_insumo("Pala")
