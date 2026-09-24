"""UC‑08: escenarios de sensibilidad sobre un presupuesto base (RF‑30, RF‑31).

Cierra el hallazgo 1 de la bitácora de F.2: UC‑08 era lo único de la ERS sin prueba. El contrato
que estas pruebas exigen (flujo principal y 2a de docs/ERS.md §2.2):

- un escenario recalcula el presupuesto completo variando `ParametrosCosto` **o** precios de
  insumos, con el motor de costos como verdad de terreno;
- el presupuesto base y las composiciones de entrada quedan intactos (RF‑30);
- la comparación es una tabla exportable con una fila por escenario, su total y su variación
  respecto del base (RF‑31), más el detalle por partida que pide el paso 3 del flujo.

Los importes esperados no salen del propio mecanismo: el incremento del vaciado de concreto con
cemento a 18 y arena a 33 es el mismo 30,17025 USD/m3 calculado a mano para UC‑02
(tests/integration/test_actualizacion_precios.py): 7,5 × 3 + 0,45 × 3 = 23,85 de material,
en cascada 23,85 × 1,15 × 1,10.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from core.budget import (
    COLUMNAS_ESCENARIOS,
    comparar_escenarios,
    comparar_por_partida,
    generar_escenario,
    generar_presupuesto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.costing import calcular_apu
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import INCREMENTO_PU_CONCRETO
from tests.fixtures.actualizacion_uc02 import PRECIOS_NUEVOS as PRECIOS_UC02

COMPOSICIONES = {apu.codigo_partida: apu for apu in linea_base.APUS_LINEA_BASE}
CONCRETO = linea_base.APU_CONCRETO.codigo_partida

# Escenario de precios del caso UC‑02: solo cemento y arena suben, solo el concreto los usa.


def _items():
    """Un renglón por APU de la línea base, cantidad 1: los deltas por partida son los del PU."""
    return [
        ItemComputo(
            codigo_partida=apu.codigo_partida,
            descripcion=apu.descripcion,
            unidad=apu.unidad,
            cantidad=Decimal(1),
            origen_id=f"uc08:{apu.codigo_partida}",
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
        )
        for apu in linea_base.APUS_LINEA_BASE
    ]


def _base():
    return generar_presupuesto(
        _items(),
        COMPOSICIONES,
        linea_base.PARAMETROS_LINEA_BASE,
        codigo="001",
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
    )


def test_escenario_de_parametros_recalcula_cada_partida_contra_el_motor():
    base = _base()
    parametros = replace(linea_base.PARAMETROS_LINEA_BASE, administracion=Decimal("0.20"))

    escenario = generar_escenario("admin 20%", base, COMPOSICIONES, parametros)

    for partida in escenario.presupuesto.partidas:
        esperado = calcular_apu(COMPOSICIONES[partida.item.codigo_partida], parametros)
        assert partida.resultado.precio_unitario == esperado.precio_unitario
    assert escenario.presupuesto.total > base.total
    assert escenario.parametros == parametros


def test_escenario_de_precios_sube_solo_las_partidas_afectadas():
    base = _base()

    escenario = generar_escenario(
        "cemento y arena",
        base,
        COMPOSICIONES,
        linea_base.PARAMETROS_LINEA_BASE,
        precios=PRECIOS_UC02,
    )

    por_codigo = {p.item.codigo_partida: p for p in escenario.presupuesto.partidas}
    base_por_codigo = {p.item.codigo_partida: p for p in base.partidas}
    for codigo, partida in por_codigo.items():
        anterior = base_por_codigo[codigo].resultado.precio_unitario
        delta = partida.resultado.precio_unitario - anterior
        assert delta == (INCREMENTO_PU_CONCRETO if codigo == CONCRETO else Decimal(0))
    assert escenario.insumos_variados == 2


def test_el_presupuesto_base_y_las_composiciones_quedan_intactos():
    base = _base()
    total_antes = base.total
    partidas_antes = base.partidas
    cemento_antes = next(
        linea.precio
        for linea in COMPOSICIONES[CONCRETO].materiales
        if linea.descripcion == "Cemento Portland"
    )

    generar_escenario(
        "no toca nada",
        base,
        COMPOSICIONES,
        linea_base.PARAMETROS_LINEA_BASE,
        precios=PRECIOS_UC02,
    )

    assert base.total == total_antes
    assert base.partidas == partidas_antes
    cemento_despues = next(
        linea.precio
        for linea in COMPOSICIONES[CONCRETO].materiales
        if linea.descripcion == "Cemento Portland"
    )
    assert cemento_despues == cemento_antes


def test_tabla_comparativa_una_fila_por_escenario_con_total_y_variacion():
    base = _base()
    caro = generar_escenario(
        "insumos UC-02", base, COMPOSICIONES, linea_base.PARAMETROS_LINEA_BASE, precios=PRECIOS_UC02
    )
    admin = generar_escenario(
        "admin 20%",
        base,
        COMPOSICIONES,
        replace(linea_base.PARAMETROS_LINEA_BASE, administracion=Decimal("0.20")),
    )

    tabla = comparar_escenarios(base, [caro, admin])

    assert tuple(tabla.columns) == COLUMNAS_ESCENARIOS
    assert len(tabla) == 3  # el base más una fila por escenario
    filas = {fila["escenario"]: fila for _, fila in tabla.iterrows()}
    assert filas["001"]["variacion"] == Decimal(0)
    assert filas["insumos UC-02"]["total"] == base.total + INCREMENTO_PU_CONCRETO
    assert filas["insumos UC-02"]["variacion"] == INCREMENTO_PU_CONCRETO
    assert filas["admin 20%"]["variacion"] == admin.presupuesto.total - base.total
    esperado_pct = INCREMENTO_PU_CONCRETO / base.total * Decimal(100)
    assert filas["insumos UC-02"]["variacion_pct"] == esperado_pct


def test_tabla_comparativa_es_exportable():
    base = _base()
    escenario = generar_escenario(
        "exportable", base, COMPOSICIONES, linea_base.PARAMETROS_LINEA_BASE, precios=PRECIOS_UC02
    )

    csv = comparar_escenarios(base, [escenario]).to_csv(index=False)

    assert "exportable" in csv
    assert str(base.total) in csv


def test_comparativo_por_partida_del_escenario():
    base = _base()
    escenario = generar_escenario(
        "detalle", base, COMPOSICIONES, linea_base.PARAMETROS_LINEA_BASE, precios=PRECIOS_UC02
    )

    comparativo = comparar_por_partida(base, escenario)

    assert len(comparativo.tabla) == len(base.partidas)
    fila_concreto = next(
        fila for _, fila in comparativo.tabla.iterrows() if fila["codigo_partida"] == CONCRETO
    )
    assert fila_concreto["pu_nuevo"] - fila_concreto["pu_anterior"] == INCREMENTO_PU_CONCRETO
    assert comparativo.total_nuevo - comparativo.total_anterior == INCREMENTO_PU_CONCRETO
    assert comparativo.insumos_afectados == 2


def test_un_escenario_exige_composicion_para_todo_renglon_del_base():
    """INV‑013 no relaja UC‑08: un escenario que perdiera un renglón en silencio dejaría de ser
    comparable con su base. `generar_escenario` exige composición antes de elaborar."""
    incompletas = {codigo: apu for codigo, apu in COMPOSICIONES.items() if codigo != CONCRETO}
    with pytest.raises(ValueError, match=CONCRETO):
        generar_escenario(
            "sin-concreto", _base(), incompletas, linea_base.PARAMETROS_LINEA_BASE
        )
