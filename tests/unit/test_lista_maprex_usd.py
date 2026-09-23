"""La lista canonica en USD derivada de la referencia MaPreX."""

from __future__ import annotations

from decimal import Decimal

from core.catalog.precios import COLUMNAS_ARCHIVO
from scripts.lista_maprex_usd import RUTA_SALIDA, filas_canonicas


def test_las_columnas_son_las_que_espera_el_cargador():
    filas = filas_canonicas()

    assert tuple(filas[0]) == COLUMNAS_ARCHIVO


def test_todo_precio_es_decimal_positivo_leido_desde_texto():
    for fila in filas_canonicas():
        precio = Decimal(fila["precio"])
        assert precio > 0, fila["insumo"]


def test_no_hay_insumos_duplicados_por_tipo_y_descripcion():
    filas = filas_canonicas()
    claves = [(fila["tipo"], fila["insumo"], fila["unidad"]) for fila in filas]

    assert len(claves) == len(set(claves))


def test_la_ruta_de_salida_esta_dentro_de_la_referencia():
    assert RUTA_SALIDA.parent.name == "maprex_2026-07"
