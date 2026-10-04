"""Normalización del texto libre que comparan las reglas de verificación.

Único lugar del sistema donde se normaliza texto (principio DRY, NORMAS.md §2). Las descripciones
de un APU, de un cómputo y de una especificación las escriben personas distintas en momentos
distintos: `Tubería PVC de 4"`, `TUBERIA PVC 4 PULGADAS` y `tuberia pvc 4 pulg` son el mismo dato.
Antes de compararlos (reglas R4 y R6) se llevan todos a una misma forma: minúsculas, sin
diacríticos, con una sola grafía para la pulgada, punto como separador decimal y espacios simples.

Para comparar especificaciones (R4, SF‑E5) el texto normalizado se lleva un paso más allá: a una
secuencia de `Componente`, palabras y cantidades, donde cada cantidad vale su `Decimal` (`3/4`,
`0.75` y `0,75` valen lo mismo; `1 1/2` es una sola cantidad de 1,5). Dos textos se comparan por
componentes, no por subcadena: «4 pulg» no está dentro de «3/4 pulg», ni «auditor» dentro de
«auditoria».

`formatear_decimal` es lo contrario: presenta un `Decimal` para un informe. Vive aquí porque el
redondeo a dos decimales de NORMAS.md §2 es una decisión de presentación, y hay una sola copia.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

__all__ = [
    "Componente",
    "Magnitud",
    "componentes",
    "es_numero",
    "formatear_decimal",
    "magnitudes",
    "magnitudes_de",
    "normalizar_texto",
    "pares_numero_unidad",
    "tokens",
    "valor_numerico",
]

# Grafías de la pulgada que aparecen en los APU y en las memorias de cálculo.
_PULGADA = re.compile(r"(?<![a-z])(?:pulgadas|pulgada|pulg)\.?(?![a-z])|''|\"|″|′′")
_UNIDAD_PULGADA = "pulg"

_COMA_DECIMAL = re.compile(r"(?<=\d),(?=\d)")
_TOKEN = re.compile(r"[a-z0-9/.]+")
_NUMERO = re.compile(r"\d+(?:/\d+)?(?:\.\d+)?")
_ENTERO = re.compile(r"\d+")
_FRACCION_SIMPLE = re.compile(r"(\d+)/(\d+)")


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

    Forma textual, sin valor: una cantidad seguida de otra cantidad (`2 1/2 pulg`) no forma par y
    solo cuenta la última. La regla R4 ya no la usa (SF‑E5): compara `magnitudes`, que une el
    número mixto y compara por `Decimal`.
    """
    pares: list[tuple[str, str]] = []
    for indice, token in enumerate(tokens_del_texto[:-1]):
        siguiente = tokens_del_texto[indice + 1]
        if es_numero(token) and not es_numero(siguiente):
            pares.append((token, siguiente))
    return pares


def valor_numerico(token: str) -> Decimal | None:
    """El `Decimal` de una cantidad (`4`, `0.10`, `3/4`), o `None` si el token no es una cantidad.

    Una fracción se divide en `Decimal` (nunca `float`): la división es correctamente redondeada,
    así que dos grafías del mismo racional (`1/2` y `2/4`) dan el mismo valor. Un denominador cero
    no es una cantidad.
    """
    if not es_numero(token):
        return None
    if "/" not in token:
        return Decimal(token)
    numerador, denominador = (Decimal(parte) for parte in token.split("/"))
    if denominador == 0:
        return None
    return numerador / denominador


@dataclass(frozen=True, slots=True)
class Componente:
    """Una palabra o una cantidad del texto normalizado.

    `texto` es la grafía normalizada (la que cita un hallazgo); `valor`, el `Decimal` de una
    cantidad, o `None` si es una palabra. Dos componentes son el mismo dato si tienen la misma
    `clave`: las cantidades se comparan por valor y las palabras por texto.
    """

    texto: str
    valor: Decimal | None = None

    @property
    def clave(self) -> tuple[str, Decimal | str]:
        if self.valor is not None:
            return ("cantidad", self.valor)
        return ("palabra", self.texto)


@dataclass(frozen=True, slots=True)
class Magnitud:
    """Una cantidad y la palabra que la califica: `1 1/2 pulg` -> (`"1 1/2"`, 1.5, `"pulg"`)."""

    texto: str
    valor: Decimal
    unidad: str


def _limpiar(token: str) -> str:
    """Quita la puntuación que pega la escritura a un token: el punto final de una frase
    (`concreto.`) y las barras sueltas. `.5` es `0.5`."""
    limpio = token.strip("/").rstrip(".")
    if limpio.startswith("."):
        limpio = f"0{limpio}" if limpio[1:2].isdigit() else limpio.lstrip(".")
    return limpio


def _fraccion_propia(token: str) -> Decimal | None:
    """El valor de `a/b` con 0 < a < b (la parte fraccionaria de un número mixto), o `None`."""
    coincidencia = _FRACCION_SIMPLE.fullmatch(token)
    if coincidencia is None:
        return None
    numerador, denominador = (int(grupo) for grupo in coincidencia.groups())
    if not 0 < numerador < denominador:
        return None
    return Decimal(numerador) / Decimal(denominador)


def componentes(texto: str) -> list[Componente]:
    """El texto como secuencia de palabras y cantidades comparables.

    Un entero seguido de una fracción propia es un número mixto y forma una sola cantidad
    (`1 1/2` vale 1,5): es la grafía de los diámetros en pulgadas.
    """
    crudos = [limpio for limpio in (_limpiar(token) for token in tokens(texto)) if limpio]
    resultado: list[Componente] = []
    indice = 0
    while indice < len(crudos):
        actual = crudos[indice]
        valor = valor_numerico(actual)
        if valor is not None and _ENTERO.fullmatch(actual) and indice + 1 < len(crudos):
            fraccion = _fraccion_propia(crudos[indice + 1])
            if fraccion is not None:
                resultado.append(Componente(f"{actual} {crudos[indice + 1]}", valor + fraccion))
                indice += 2
                continue
        resultado.append(Componente(actual, valor))
        indice += 1
    return resultado


def magnitudes_de(secuencia: Sequence[Componente]) -> list[Magnitud]:
    """Cada cantidad de `secuencia` seguida de una palabra, con esa palabra como unidad.

    Es la base de la detección de contradicciones de la regla R4: si la especificación dice
    3/4 pulg y el texto de la partida dice 4 pulg, la misma magnitud lleva dos valores distintos.
    """
    return [
        Magnitud(actual.texto, actual.valor, siguiente.texto)
        for actual, siguiente in zip(secuencia, secuencia[1:], strict=False)
        if actual.valor is not None and siguiente.valor is None
    ]


def magnitudes(texto: str) -> list[Magnitud]:
    """`magnitudes_de(componentes(texto))`."""
    return magnitudes_de(componentes(texto))


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
