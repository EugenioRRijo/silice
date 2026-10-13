"""Utilidades de fórmulas: referencias, nombres de hoja y reescritura por tokens.

La reescritura usa el tokenizador de openpyxl (no expresiones regulares sobre el texto completo),
para no tocar un texto entre comillas que se parezca a una referencia. Cada operando de tipo rango
pasa por una función que devuelve su texto nuevo, el mismo, o `None` si la fórmula ya no se puede
conservar (vínculo externo, `#REF!`, hoja que no sale en la devolución): en ese caso la fórmula
entera se sustituye por su valor (spec 1.5, F-D5).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from openpyxl.formula.tokenizer import Token, Tokenizer

__all__ = [
    "MAX_COL",
    "MAX_FILA",
    "Ref",
    "analizar_ref",
    "cita",
    "col_num",
    "dir_celda",
    "dir_rango",
    "letra",
    "reescribir",
    "tokens",
]

MAX_FILA = 1_048_576
MAX_COL = 16_384
_CELDA = re.compile(r"^\$?([A-Za-z]{1,3})\$?(\d+)$")
_COL = re.compile(r"^\$?([A-Za-z]{1,3})$")
_FILA = re.compile(r"^\$?(\d+)$")
_SIMPLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def col_num(letras: str) -> int:
    n = 0
    for ch in letras.upper():
        n = n * 26 + (ord(ch) - 64)
    return n


def letra(col: int) -> str:
    s = ""
    while col:
        col, r = divmod(col - 1, 26)
        s = chr(65 + r) + s
    return s


def cita(hoja: str) -> str:
    """Nombre de hoja listo para una fórmula: `INSUMOS` o `'APU-01'`."""
    if _SIMPLE.match(hoja) and not _CELDA.match(hoja):
        return hoja
    return "'" + hoja.replace("'", "''") + "'"


def dir_celda(fila: int, col: int, absoluta: bool = True) -> str:
    if absoluta:
        return f"${letra(col)}${fila}"
    return f"{letra(col)}{fila}"


def dir_rango(f1: int, c1: int, f2: int, c2: int, absoluta: bool = True) -> str:
    a = dir_celda(f1, c1, absoluta)
    if (f1, c1) == (f2, c2):
        return a
    return f"{a}:{dir_celda(f2, c2, absoluta)}"


@dataclass(frozen=True, slots=True)
class Ref:
    """Una referencia de celda o rango. `hoja` None = la hoja de la fórmula.

    `externa`: apunta a otro libro (`[1]HOJA!…`). `rota`: contiene `#REF!`.
    """

    hoja: str | None
    f1: int
    c1: int
    f2: int
    c2: int
    externa: bool = False
    rota: bool = False

    @property
    def es_celda(self) -> bool:
        return self.f1 == self.f2 and self.c1 == self.c2


def _separar_hoja(texto: str) -> tuple[str | None, str, bool]:
    """'\\'APU-01\\'!$B:$B' → ('APU-01', '$B:$B', externa)."""
    if "!" not in texto:
        return None, texto, False
    if texto.startswith("'"):
        i = 1
        partes = []
        while i < len(texto):
            ch = texto[i]
            if ch == "'":
                if i + 1 < len(texto) and texto[i + 1] == "'":
                    partes.append("'")
                    i += 2
                    continue
                break
            partes.append(ch)
            i += 1
        hoja = "".join(partes)
        resto = texto[i + 1 :]
        resto = resto[1:] if resto.startswith("!") else resto
    else:
        hoja, _, resto = texto.partition("!")
    externa = hoja.startswith("[") or "]" in hoja
    if hoja.startswith("[") and "]" in hoja:
        hoja = hoja.split("]", 1)[1]
    return hoja, resto, externa


def analizar_ref(texto: str) -> Ref | str | None:
    """Texto de un operando rango → `Ref`, o el nombre definido (str), o None si no se entiende."""
    hoja, resto, externa = _separar_hoja(texto.strip())
    if "#REF!" in resto.upper():
        return Ref(hoja, 0, 0, 0, 0, externa=externa, rota=True)
    if ":" in resto:
        a, _, b = resto.partition(":")
        ma, mb = _CELDA.match(a), _CELDA.match(b)
        if ma and mb:
            c1, f1 = col_num(ma.group(1)), int(ma.group(2))
            c2, f2 = col_num(mb.group(1)), int(mb.group(2))
            return Ref(hoja, min(f1, f2), min(c1, c2), max(f1, f2), max(c1, c2), externa)
        ca, cb = _COL.match(a), _COL.match(b)
        if ca and cb:
            c1, c2 = col_num(ca.group(1)), col_num(cb.group(1))
            return Ref(hoja, 1, min(c1, c2), MAX_FILA, max(c1, c2), externa)
        fa, fb = _FILA.match(a), _FILA.match(b)
        if fa and fb:
            f1, f2 = int(fa.group(1)), int(fb.group(1))
            return Ref(hoja, min(f1, f2), 1, max(f1, f2), MAX_COL, externa)
        return None
    m = _CELDA.match(resto)
    if m:
        c, f = col_num(m.group(1)), int(m.group(2))
        if c <= MAX_COL and f <= MAX_FILA:
            return Ref(hoja, f, c, f, c, externa)
    if re.match(r"^[A-Za-z_\\][A-Za-z0-9_.\\]*$", resto):
        if externa:
            return Ref(hoja, 0, 0, 0, 0, externa=True)
        return f"{hoja}!{resto}" if hoja else resto
    return None


def tokens(formula: str) -> list[Token]:
    return list(Tokenizer(formula if formula.startswith("=") else "=" + formula).items)


def reescribir(formula: str, rango: Callable[[str], str | None]) -> str | None:
    """Pasa cada operando rango por `rango`; None si alguno no se puede conservar.

    Un operando de error `#REF!` también devuelve None.
    """
    salida: list[str] = []
    for t in tokens(formula):
        if t.type == Token.OPERAND and t.subtype == Token.RANGE:
            nuevo = rango(t.value)
            if nuevo is None:
                return None
            salida.append(nuevo)
        elif t.type == Token.OPERAND and t.subtype == Token.ERROR and t.value.upper() == "#REF!":
            return None
        else:
            salida.append(t.value)
    return "=" + "".join(salida)
