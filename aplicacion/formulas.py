"""Neutralizar el texto de la persona que una hoja de cálculo leería como fórmula.

Excel evalúa una celda que empieza por «=», «+», «-» o «@» (también tras espacios o un salto de
línea, que recorta) y trata como fórmula una que empieza por un tabulador o un retorno: se le
antepone un apóstrofo (OWASP, «CSV Injection»). Lo usan el CSV de escenarios
(`aplicacion/escenarios_csv.py`) y la ruta que lo arma; el libro del núcleo tiene su propia regla
(`core/budget/excel.py`).
"""

from __future__ import annotations

__all__ = ["neutralizar_formula"]

_INICIO_DE_FORMULA = ("=", "+", "-", "@")
_INICIO_DE_CONTROL = ("\t", "\r", "\n")


def neutralizar_formula(texto: str) -> str:
    """`texto` con un apóstrofo delante si una hoja de cálculo lo leería como fórmula."""
    if texto.startswith(_INICIO_DE_CONTROL) or texto.lstrip(" \t\r\n").startswith(
        _INICIO_DE_FORMULA
    ):
        return f"'{texto}"
    return texto
