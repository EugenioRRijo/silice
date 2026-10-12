"""Lector JSON estricto para todo lo que viene de fuera (spec S3 §7.3 y §8.4; RV-16).

Rechaza lo que `json.loads` acepta por omisión y que dos lectores podrían interpretar distinto o
usar para agotar la memoria: `NaN`, `Infinity` y `-Infinity`; claves duplicadas; anidamiento de
más de 64 niveles (o `RecursionError`); y toda cifra fuera del patrón `PATRON_CIFRA`, que se
comprueba ANTES de construir un `Decimal` (un `1E+999999999` no llega a `Decimal`).

El patrón admite hasta 20 dígitos enteros y 28 decimales: el motor no redondea (prec 28,
NORMAS §2), así que un precio unitario guardado puede traer 28 decimales. El ejemplo del spec
(15 y 12) se amplió por eso (RP8-13). Nunca hay exponente ni signo `+`.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from decimal import Decimal
from typing import Any

MAX_NIVELES = 64
PATRON_CIFRA = re.compile(r"^-?[0-9]{1,20}(\.[0-9]{1,28})?$")  # [0-9]: \d acepta otros alfabetos


class JsonRechazado(ValueError):  # noqa: N818
    """Un JSON que no cumple el lector estricto; el mensaje dice por qué, sin traza."""


def a_decimal(texto: object) -> Decimal:
    """`Decimal` de un texto que cumple `PATRON_CIFRA`; `JsonRechazado` si no."""
    if not isinstance(texto, str) or not PATRON_CIFRA.fullmatch(texto):
        raise JsonRechazado(f"cifra fuera del patron estricto: {str(texto)[:40]!r}")
    return Decimal(texto)


def _pares(pares: list[tuple[str, Any]]) -> dict[str, Any]:
    repetidas = [clave for clave, n in Counter(c for c, _ in pares).items() if n > 1]
    if repetidas:
        raise JsonRechazado(f"clave JSON duplicada: {repetidas[0]!r}")
    return dict(pares)


def _constante(nombre: str) -> Any:
    raise JsonRechazado(f"constante no admitida: {nombre}")


def _entero(texto: str) -> int:
    if not PATRON_CIFRA.fullmatch(texto):
        raise JsonRechazado(f"cifra fuera del patron estricto: {texto[:40]!r}")
    return int(texto)


def _decimal(texto: str) -> Decimal:
    return a_decimal(texto)


def _profundidad(valor: Any) -> int:
    """Niveles de anidamiento, sin recursión (un JSON hostil no debe agotar la pila)."""
    maxima, pila = 0, [(valor, 1)]
    while pila:
        actual, nivel = pila.pop()
        if isinstance(actual, dict):
            hijos = list(actual.values())
        elif isinstance(actual, list):
            hijos = actual
        else:
            continue
        maxima = max(maxima, nivel)
        pila.extend((hijo, nivel + 1) for hijo in hijos)
    return maxima


def leer_json(datos: bytes | str, *, max_niveles: int = MAX_NIVELES) -> Any:
    """El valor JSON de `datos` (UTF-8 estricto) o `JsonRechazado`.

    Los números enteros salen como `int` y los que traen punto como `Decimal`; los montos de los
    documentos de Sílice viajan como texto y se convierten con `a_decimal`.
    """
    try:
        texto = datos if isinstance(datos, str) else datos.decode("utf-8")
        valor = json.loads(
            texto,
            object_pairs_hook=_pares,
            parse_constant=_constante,
            parse_int=_entero,
            parse_float=_decimal,
        )
    except JsonRechazado:
        raise
    except RecursionError:
        raise JsonRechazado("JSON demasiado anidado") from None
    except (UnicodeDecodeError, ValueError) as error:
        raise JsonRechazado(f"no es un JSON valido: {str(error)[:80]}") from None
    if _profundidad(valor) > max_niveles:
        raise JsonRechazado(f"JSON anidado a mas de {max_niveles} niveles")
    return valor
