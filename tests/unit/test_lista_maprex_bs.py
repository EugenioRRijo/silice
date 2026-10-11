# tests/unit/test_lista_maprex_bs.py
from decimal import Decimal

from scripts.lista_maprex_bs import COLUMNAS_SALIDA, RUTA_SALIDA, filas_canonicas


def test_las_111_filas_llevan_precio_bs_fecha_y_ref_tal_cual():
    filas = filas_canonicas()
    assert len(filas) == 111  # verificadas a mano en M0.2 (S1 §6.2)
    assert all(tuple(f) == COLUMNAS_SALIDA for f in filas)
    tubo = next(f for f in filas if f["referencia"] == "PLOA38")
    assert (tubo["precio"], tubo["fecha"]) == ("8822.17", "2026-07-09")  # referencia_civil.csv
    assert next(f for f in filas if f["referencia"] == "1-1.2")["fecha"] == "2026-07-01"


def test_todo_precio_es_decimal_positivo_desde_texto_y_la_salida_existe():
    assert all(Decimal(f["precio"]) > 0 for f in filas_canonicas())
    assert RUTA_SALIDA.name == "lista_maprex_bs.csv"
