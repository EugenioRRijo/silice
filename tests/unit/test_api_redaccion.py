"""VB-16: la prosa de los hallazgos que muestran Revisar y Precios (concordancia y mayusculas).

Oraculos escritos a mano; los insumos son ficticios.
"""

from __future__ import annotations

import pytest

from api.redaccion import pulir

R11 = "{n} insumos no contrastables: {a} sin referencia MaPreX ({la}), {b} sin tasa a su fecha ({lb})"


def test_un_insumo_sin_tasa_va_en_singular_y_sin_el_grupo_vacio() -> None:
    texto = R11.format(n=1, a=0, la="", b=1, lb="X-1")
    assert pulir(texto) == "1 insumo no contrastable: 1 sin tasa a su fecha (X-1)"


def test_un_insumo_sin_referencia_va_en_singular_y_sin_el_grupo_vacio() -> None:
    texto = R11.format(n=1, a=1, la="Y-2", b=0, lb="")
    assert pulir(texto) == "1 insumo no contrastable: 1 sin referencia MaPreX (Y-2)"


def test_varios_insumos_de_los_dos_grupos_conservan_ambos() -> None:
    texto = R11.format(n=3, a=2, la="A, B", b=1, lb="C")
    assert pulir(texto) == (
        "3 insumos no contrastables: 2 sin referencia MaPreX (A, B), 1 sin tasa a su fecha (C)"
    )


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("INDICIO: los reajustes superan el 10 %", "Indicio: los reajustes superan el 10 %"),
        ("Resultado: NO CUMPLE", "Resultado: No cumple"),
        ("Resultado: CUMPLE", "Resultado: Cumple"),
        ("la cantidad de EJ-P1 es manual", "la cantidad de EJ-P1 es manual"),
    ],
)
def test_las_mayusculas_de_indicio_y_cumple_pasan_a_inicial(crudo: str, esperado: str) -> None:
    assert pulir(crudo) == esperado
