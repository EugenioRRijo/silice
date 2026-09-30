"""Normalización del texto libre que comparan las reglas de verificación.

Único lugar del sistema donde se normaliza texto (principio DRY, NORMAS.md §2). Las descripciones
de un APU, de un cómputo y de una especificación las escriben personas distintas en momentos
distintos: `Tubería PVC de 4"`, `TUBERIA PVC 4 PULGADAS` y `tuberia pvc 4 pulg` son el mismo dato.
Antes de compararlos (reglas R4 y R6) se llevan todos a una misma forma: minúsculas, sin
diacríticos, con una sola grafía para la pulgada, punto como separador decimal y espacios simples.

`formatear_decimal` es lo contrario: presenta un `Decimal` para un informe. Vive aquí porque el
redondeo a dos decimales de NORMAS.md §2 es una decisión de presentación, y hay una sola copia.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal

__all__ = [
    "es_numero",
    "formatear_decimal",
    "normalizar_texto",
    "pares_numero_unidad",
    "tokens",
]

# Grafías de la pulgada que aparecen en los APU y en las memorias de cálculo.
_PULGADA = re.compile(r"(?<![a-z])(?:pulgadas|pulgada|pulg)\.?(?![a-z])|''|\"|″|′′")
_UNIDAD_PULGADA = "pulg"

_COMA_DECIMAL = re.compile(r"(?<=\d),(?=\d)")
_TOKEN = re.compile(r"[a-z0-9/.]+")
_NUMERO = re.compile(r"\d+(?:/\d+)?(?:\.\d+)?")


def normalizar_texto(texto: str) -> str:
    """Forma canónica de un texto para compararlo con otro.

    Minúsculas, sin diacríticos (NFKD), toda grafía de la pulgada como ` pulg`, la coma decimal
    como punto y los espacios colapsados.
    """
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_diacriticos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    minusculas = sin_diacriticos.lower()
    con_pulgadas = _PULGADA.sub(f" {_UNIDAD_PULGADA} ", minusculas)
    con_punto_decimal = _COMA_DECIMAL.sub(".", con_pulgadas)
    return " ".join(con_punto_decimal.split())


def tokens(texto: str) -> list[str]:
    """Palabras y cantidades del texto ya normalizado: `[a-z0-9/.]+`."""
    return _TOKEN.findall(normalizar_texto(texto))


def es_numero(token: str) -> bool:
    """True si el token es una cantidad: entero, fracción o decimal (`4`, `3/4`, `0.10`)."""
    return _NUMERO.fullmatch(token) is not None


def pares_numero_unidad(tokens_del_texto: list[str]) -> list[tuple[str, str]]:
    """Pares (cantidad, palabra que la sigue) del texto: `["4", "pulg"]` -> `[("4", "pulg")]`.

    Es la base de la detección de contradicciones de la regla R4: si la especificación dice
    `("3/4", "pulg")` y el texto de la partida dice `("4", "pulg")`, la misma magnitud lleva dos
    valores distintos. Una cantidad seguida de otra cantidad (`2 1/2 pulg`) no forma par: solo
    cuenta la última, que es la que la unidad califica.
    """
    pares: list[tuple[str, str]] = []
    for indice, token in enumerate(tokens_del_texto[:-1]):
        siguiente = tokens_del_texto[indice + 1]
        if es_numero(token) and not es_numero(siguiente):
            pares.append((token, siguiente))
    return pares


def formatear_decimal(valor: Decimal, decimales: int | None = None) -> str:
    """Texto de un `Decimal` para un informe, sin notación exponencial.

    Con `decimales` redondea a esa cantidad (dos, al presentar montos: NORMAS.md §2); sin ella
    conserva el valor exacto y solo recorta los ceros finales, para que la evidencia de un
    hallazgo no pierda dígitos.
    """
    if decimales is not None:
        cuantizado = valor.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)
        return f"{cuantizado:f}"
    texto = f"{valor:f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto or "0"
