"""Calculador de fórmulas del calcado (`escritor/calculos.py`): depuración del lector, 2026-11-15.

Cada prueba apunta a un defecto verificado y compara con lo que da Excel (oráculo: la función de
Excel con los mismos argumentos). Las fórmulas se evalúan sobre un libro de salida vacío y
construido aquí; ningún dato real.
"""

from __future__ import annotations

import pytest

from adapters.hoja_empresa.escritor.calculos import Err, Evaluador
from adapters.hoja_empresa.escritor.hoja import HojaSalida, LibroSalida

VALOR = Err("#VALUE!")


def _evaluar(formula: str, nombres: dict[str, str] | None = None) -> object:
    libro = LibroSalida({"H": HojaSalida("H", {})}, ["H"])
    return Evaluador(libro, nombres or {}).formula(formula, "H")


# --- 4. Funciones con menos argumentos de los que piden ------------------------------------------


@pytest.mark.parametrize(
    "formula",
    [
        "=IF()",
        "=MOD(1)",
        '=MID("a",1)',
        "=TEXT(1)",
        "=LEFT()",
        "=SUMIF(A1:A2)",
        "=VLOOKUP(1,A1:B2)",
    ],
)
def test_funcion_con_argumentos_de_menos_da_value_y_no_tumba_la_devolucion(formula):
    assert _evaluar(formula) == VALOR
