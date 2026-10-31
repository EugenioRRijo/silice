"""Reportes viales, de riesgo y de mejora en Excel (plan vial, Tarea 21). ESQUELETO del rojo.

Las seis funciones devuelven un libro vacío; la implementación llega en el commit siguiente.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook


def _vacio(*_args: object, **_kwargs: object) -> bytes:
    salida = BytesIO()
    Workbook().save(salida)
    return salida.getvalue()


computos_por_tramo = _vacio
apu_con_origen = _vacio
costo_de_produccion = _vacio
informe_de_riesgo = _vacio
informe_de_mejora = _vacio
resumen_con_iva = _vacio


def nombre_de_reporte(*_partes: str) -> str:
    return ""
