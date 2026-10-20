"""VB-16: la prosa de R11 que muestran Revisar y Precios (concordancia y lista vacia).

Oraculos escritos a mano; los insumos son ficticios. Ninguna palabra del usuario cambia.
"""

from __future__ import annotations

import time

import pytest

from api.redaccion import pulir

R11 = (
    "{n} insumos no contrastables: {a} sin referencia MaPreX ({la}), {b} sin tasa a su fecha ({lb})"
)


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


def test_un_grupo_con_cuenta_y_lista_vacia_conserva_la_cuenta_para_que_la_suma_cuadre() -> None:
    texto = R11.format(n=2, a=1, la="", b=1, lb="Z")
    assert pulir(texto) == (
        "2 insumos no contrastables: 1 sin referencia MaPreX, 1 sin tasa a su fecha (Z)"
    )


@pytest.mark.parametrize(
    "texto",
    [
        "CEMENTO NO CUMPLE NORMA",
        "TUBO CUMPLE-01",
        "ARENA INDICIO",
        "INDICIO: los reajustes superan el 10 %",
        "Resultado: NO CUMPLE",
        R11.format(n=2, a=1, la="TUBO CUMPLE-01", b=1, lb="ARENA INDICIO"),
        "la cantidad de EJ-P1 es manual",
    ],
)
def test_las_palabras_del_usuario_salen_intactas(texto: str) -> None:
    esperado = (
        texto
        if "insumos no" not in texto
        else (
            "2 insumos no contrastables: 1 sin referencia MaPreX (TUBO CUMPLE-01), "
            "1 sin tasa a su fecha (ARENA INDICIO)"
        )
    )
    assert pulir(texto) == esperado


CABEZA = "1 insumos no contrastables: 1 sin referencia MaPreX ("
MEDIO = "), 1 sin tasa a su fecha ("


@pytest.mark.parametrize(
    "texto",
    [
        CABEZA + MEDIO * 3800,
        CABEZA + "x" * 100_000,
        "x" * 100_000,
        "1 insumos no contrastables: 1 sin referencia MaPreX (" + "(" * 100_000,
    ],
    ids=["delimitadores", "x_tras_cabeza", "solo_x", "parentesis"],
)
def test_un_texto_adversarial_de_100000_caracteres_tarda_menos_de_un_segundo(texto: str) -> None:
    t0 = time.perf_counter()
    salida = pulir(texto)
    assert time.perf_counter() - t0 < 1.0
    assert salida == texto  # por encima del tope de longitud el texto queda intacto
