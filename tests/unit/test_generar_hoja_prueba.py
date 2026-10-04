"""El generador determinista de puntos de la hoja (RNF-11 y prueba corta de spec 11.3)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.budget import elaborar
from core.contracts.dominio import Dominio
from core.contracts.item_computo import OrigenTipo
from scripts.generar_hoja_prueba import (
    PARAMETROS_PRUEBA,
    composiciones_de_prueba,
    generar_items,
)


def test_generador_es_determinista_y_del_tamano_pedido():
    a = generar_items(500, semilla=7)
    b = generar_items(500, semilla=7)
    assert len(a) == 500
    assert a == b
    assert generar_items(500, semilla=8) != a


def test_todas_las_cantidades_son_decimal_y_el_origen_es_manual_civil():
    items = generar_items(50)
    assert all(isinstance(i.cantidad, Decimal) and i.cantidad > 0 for i in items)
    assert all(i.origen_tipo is OrigenTipo.MANUAL for i in items)
    assert all(i.dominio is Dominio.CIVIL for i in items)
    assert [i.origen_id for i in items] == [f"gen-{n}" for n in range(50)]


def test_las_partidas_generadas_tienen_composicion_y_se_elabora_sin_pendientes():
    composiciones = composiciones_de_prueba()
    items = generar_items(500)
    assert {i.codigo_partida for i in items} <= set(composiciones)
    resultado = elaborar(
        items, composiciones, PARAMETROS_PRUEBA, codigo="PRUEBA", fecha=date(2026, 10, 4)
    )
    assert resultado.pendientes == ()
    assert len(resultado.presupuesto.partidas) == 500


def test_las_cantidades_tienen_exactamente_dos_decimales():
    for item in generar_items(2000, semilla=3):
        assert item.cantidad.as_tuple().exponent == -2, item.cantidad
