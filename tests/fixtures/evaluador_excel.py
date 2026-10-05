"""Evaluador de formulas de Excel para las pruebas (SF3): unica copia (DRY).

Lo usan las pruebas del Excel del nucleo y las de la hoja. El paquete `formulas` (grupo `dev`)
calcula cada celda del libro; las pruebas comparan con el `Decimal` del sistema con tolerancia.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path


def evaluar(ruta: Path) -> dict[tuple[str, str], float]:
    """Todas las celdas del libro calculadas: `{(HOJA EN MAYUSCULAS, "C7"): valor}`."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # `formulas` emite SyntaxWarning al compilar sus modulos
        import formulas

        modelo = formulas.ExcelModel().loads(str(ruta)).finish()
        solucion = modelo.calculate()
    celdas: dict[tuple[str, str], float] = {}
    for clave, valor in solucion.items():
        coincide = re.fullmatch(r"'\[[^\]]+\]([^']+)'!([A-Z]+[0-9]+)", clave)
        if not coincide:
            continue
        try:
            celdas[(coincide.group(1), coincide.group(2))] = float(valor.value[0][0])
        except (TypeError, ValueError, IndexError):
            continue
    return celdas


def _celda(libro, hoja: str, etiqueta: str, columna: str = "B") -> str:
    """La direccion de la celda de `columna` en la fila cuya columna A es `etiqueta`."""
    for fila in libro[hoja].iter_rows(min_col=1, max_col=1):
        if fila[0].value == etiqueta:
            return f"{columna}{fila[0].row}"
    raise AssertionError(f"{etiqueta!r} no esta en {hoja}")
