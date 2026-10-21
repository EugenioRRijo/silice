"""VB-1: `texto_decimal` nunca escribe una cifra que el lector estricto rechace.

Expediente: `docs/bitacora/2026-10-21-VB1-expediente-core.md`. El exportador cuantiza a 28 decimales
(ROUND_HALF_EVEN) lo que traiga mas; lo que ya cabe sale IDENTICO a `format(valor, "f")` (por eso
ninguna huella ni firma existente se mueve).

Oraculo independiente del codigo bajo prueba: aritmetica entera con `fractions.Fraction` (su
`round` es half-even) y literales escritos a mano; no se usa `Decimal.quantize` para esperar.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

import pytest

from core.budget import canonico
from seguridad import json_estricto

D28 = Decimal(1).scaleb(-28)


def _esperado(valor: Decimal) -> str:
    """El texto de `valor` a 28 decimales, half-even, por enteros (sin `Decimal.quantize`)."""
    entero = round(Fraction(valor) * 10**28)  # half-even
    signo = "-" if entero < 0 or (entero == 0 and valor.is_signed()) else ""
    cifras = str(abs(entero)).rjust(29, "0")
    return f"{signo}{cifras[:-28]}.{cifras[-28:]}"


# --- literales a mano --------------------------------------------------------------------------

CASOS = (
    # (valor, texto esperado): el valor se construye desde texto o por division en contexto base.
    (Decimal(1) / Decimal(12), "0.0833333333333333333333333333"),  # 29 decimales: el caso VB-1
    (Decimal(1) / Decimal(15), "0.0666666666666666666666666667"),  # redondea hacia arriba
    (Decimal(1) / Decimal(3), "0.3333333333333333333333333333"),  # ya tiene 28
    (Decimal(2) / Decimal(3), "0.6666666666666666666666666667"),  # ya tiene 28
    (Decimal(1) / Decimal(7), "0.1428571428571428571428571429"),  # ya tiene 28
    (Decimal("1E-27"), "0.000000000000000000000000001"),  # 27 decimales: no se toca
    (Decimal("1E-29"), "0.0000000000000000000000000000"),  # menos que el paso: cero
    (Decimal("-1E-29"), "-0.0000000000000000000000000000"),
    (Decimal("0.00000000000000000000000000005"), "0.0000000000000000000000000000"),  # empate: par
    (Decimal("0.00000000000000000000000000015"), "0.0000000000000000000000000002"),  # empate: par
    (Decimal("0.00000000000000000000000000025"), "0.0000000000000000000000000002"),  # empate: par
    (Decimal("-0.00000000000000000000000000035"), "-0.0000000000000000000000000004"),
    (Decimal("0"), "0"),
    (Decimal("-0"), "-0"),
    (Decimal("836.79750000"), "836.79750000"),
    (Decimal("-1.5"), "-1.5"),
    (
        Decimal("12345678901234567890.12345678901234567890123456789"),
        "12345678901234567890.1234567890123456789012345679",
    ),  # 20 enteros + 29 decimales
    (
        Decimal("-12345678901234567890.12345678901234567890123456781"),
        "-12345678901234567890.1234567890123456789012345678",
    ),
    (Decimal(10**15) / Decimal(12) / Decimal(7), "11904761904761.90476190476190"),
)


@pytest.mark.parametrize(("valor", "texto"), CASOS)
def test_la_cifra_exportada_es_la_esperada_y_el_lector_estricto_la_acepta(
    valor: Decimal, texto: str
) -> None:
    salida = canonico.texto_decimal(valor)
    assert salida is not None
    assert salida == texto
    assert canonico.PATRON_CIFRA.fullmatch(salida)
    assert json_estricto.PATRON_CIFRA.fullmatch(salida)
    assert json_estricto.a_decimal(salida) == Decimal(_esperado(valor))


def test_un_cociente_por_un_valor_grande_sale_como_dice_la_aritmetica_entera() -> None:
    valor = Decimal(1) / Decimal(12) * Decimal("123456789012")
    assert canonico.texto_decimal(valor) == _esperado(valor)


def test_none_sigue_siendo_none() -> None:
    assert canonico.texto_decimal(None) is None


# --- 20 enteros con 28 decimales exactos: no cambian --------------------------------------------


@pytest.mark.parametrize(
    "texto",
    (
        "9" * 20 + "." + "9" * 28,
        "-" + "9" * 20 + "." + "9" * 28,
        "1" + "0" * 19 + "." + "0" * 27 + "1",
    ),
)
def test_el_limite_del_patron_no_cambia(texto: str) -> None:
    assert canonico.texto_decimal(Decimal(texto)) == texto


# --- identidad: lo que ya cabia sale IDENTICO (huellas y firmas existentes no se mueven) ---------


def test_todo_lo_que_ya_cabia_sale_identico_a_format_f() -> None:
    muestras = [
        Decimal(n) / Decimal(10**k) for n in (0, 1, 5, 7, 123, 999999) for k in range(0, 29)
    ]
    muestras += [Decimal(f"{n}E-{k}") for n in (1, 3, 99) for k in range(0, 29)]
    muestras += [Decimal(n) for n in (0, 1, 10**20 - 1)]
    for valor in muestras:
        assert canonico.texto_decimal(valor) == format(valor, "f"), valor
        assert canonico.texto_decimal(-valor) == format(-valor, "f"), valor


# --- propiedad: barrido determinista (hypothesis no es dependencia del proyecto) ----------------


def test_todo_cociente_del_contexto_por_omision_sale_aceptado_y_es_la_cuantizacion() -> None:
    n_total = 0
    for d in range(1, 301):
        for n in range(0, 301, 7):
            for escala in (Decimal(1), Decimal("0.01"), Decimal("1E-9"), Decimal("123456.789")):
                for signo in (1, -1):
                    valor = signo * Decimal(n) / Decimal(d) * escala
                    texto = canonico.texto_decimal(valor)
                    assert texto is not None
                    assert canonico.PATRON_CIFRA.fullmatch(texto), (n, d, texto)
                    assert json_estricto.PATRON_CIFRA.fullmatch(texto), (n, d, texto)
                    assert Decimal(texto) == Decimal(_esperado(valor)), (n, d)
                    assert texto == _esperado(valor) or "." not in format(valor, "f")
                    n_total += 1
    assert n_total > 100_000


def test_la_diferencia_maxima_es_media_unidad_del_ultimo_decimal() -> None:
    peor = Decimal(0)
    for d in range(1, 400):
        valor = Decimal(1) / Decimal(d)
        peor = max(peor, abs(Decimal(canonico.texto_decimal(valor) or "0") - valor))
    assert peor <= D28 / 2 < Decimal("1E-28")


def test_ningun_monto_a_dos_decimales_cambia_en_el_barrido() -> None:
    """Redondeo contable (HALF_UP a 2 decimales) del valor y de su texto cuantizado: iguales.

    Solo podria diferir un valor a menos de 5E-29 de un empate de centesimas; un cociente n/d con
    d <= 400 esta a >= 1/(200*d) de cualquier empate, tan lejos como para que no ocurra aqui.
    """
    paso = Decimal("0.01")
    for d in range(1, 401):
        for n in range(1, 2000, 3):
            valor = Decimal(n) / Decimal(d)
            antes = valor.quantize(paso, rounding=ROUND_HALF_UP)
            despues = Decimal(canonico.texto_decimal(valor) or "0").quantize(
                paso, rounding=ROUND_HALF_UP
            )
            assert antes == despues, (n, d)
