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


# --- 5. Nombre definido que se refiere a sí mismo ------------------------------------------------

#: El calculador marca así una referencia circular entre celdas (`Evaluador.celda`); un nombre que
#: se usa a sí mismo es la misma referencia circular.
CIRCULAR = Err("#CIRC")


@pytest.mark.parametrize(
    "nombres",
    [{"DSEM": "=DSEM+1"}, {"IDA": "=VUELTA+1", "VUELTA": "=IDA*2"}],
    ids=["directo", "por-otro-nombre"],
)
def test_nombre_que_se_usa_a_si_mismo_es_referencia_circular(nombres):
    """`programacion.py` evalúa el texto de DSEM con `Evaluador.formula`: el `RecursionError`
    tumbaba la devolución entera."""
    primero = next(iter(nombres))
    assert _evaluar(f"={primero}", nombres) == CIRCULAR


def test_nombre_repetido_sin_ciclo_se_sigue_calculando():
    nombres = {"DOS": "=2", "CUATRO": "=DOS+DOS"}
    assert _evaluar("=CUATRO*DOS", nombres) == 8


# --- 6. FIND con un inicio fuera del texto -------------------------------------------------------


@pytest.mark.parametrize(
    "formula", ['=FIND("a","cba",0)', '=FIND("a","cba",-1)', '=FIND("","cba",5)']
)
def test_find_con_inicio_fuera_del_texto_da_value(formula):
    """Excel: el inicio va de 1 al largo del texto + 1; fuera de eso, #VALUE!."""
    assert _evaluar(formula) == VALOR


@pytest.mark.parametrize(
    ("formula", "esperado"),
    [('=FIND("a","cba")', 3), ('=FIND("a","cba",3)', 3), ('=FIND("","cba",4)', 4)],
)
def test_find_con_inicio_dentro_del_texto_no_cambia(formula, esperado):
    assert _evaluar(formula) == esperado


# --- 7. TEXT de un texto que vale cero -----------------------------------------------------------


@pytest.mark.parametrize(
    ("formula", "esperado"),
    [('=TEXT("0","0000")', "0000"), ('=TEXT(0,"0000")', "0000"), ('=TEXT("1","0000")', "0001")],
)
def test_text_de_un_texto_numerico_cero_se_formatea(formula, esperado):
    """`Decimal('0')` es falso: el texto "0" no se tomaba por número y salía tal cual."""
    assert _evaluar(formula) == esperado


# --- 8. TEXT con separador de miles y ceros a la izquierda ---------------------------------------


@pytest.mark.parametrize(
    ("formula", "esperado"),
    [
        ('=TEXT(5,"#,0000")', "0,005"),
        ('=TEXT(5,"0,000")', "0,005"),
        ('=TEXT(12,"#,000000")', "000,012"),
        ('=TEXT(-5,"0,000")', "-0,005"),
        ('=TEXT(5.5,"0,000.0")', "0,005.5"),
    ],
)
def test_text_con_miles_agrupa_tambien_los_ceros_de_relleno(formula, esperado):
    """Excel agrupa de tres en tres desde la derecha el número ya rellenado con ceros. Aquí se
    emula el formato del libro (el de Excel, coma de miles), no la convención de la interfaz."""
    assert _evaluar(formula) == esperado


@pytest.mark.parametrize(
    ("formula", "esperado"),
    [
        ('=TEXT(1234,"#,0000")', "1,234"),
        ('=TEXT(1234567,"#,##0")', "1,234,567"),
        ('=TEXT(1234567.891,"#,##0.00")', "1,234,567.89"),
        ('=TEXT(5,"0000")', "0005"),
    ],
)
def test_text_sin_relleno_o_sin_miles_no_cambia(formula, esperado):
    assert _evaluar(formula) == esperado
