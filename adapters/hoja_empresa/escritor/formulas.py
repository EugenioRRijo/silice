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
from openpyxl.utils.cell import column_index_from_string as col_num
from openpyxl.utils.cell import get_column_letter as letra

__all__ = [
    "MAX_COL",
    "MAX_FILA",
    "Ref",
    "analizar_ref",
    "cita",
    "col_num",
    "dir_celda",
    "dir_rango",
    "es_formula_peligrosa",
    "letra",
    "motivo_peligro",
    "reescribir",
    "tokens",
]

MAX_FILA = 1_048_576
MAX_COL = 16_384
_CELDA = re.compile(r"^\$?([A-Za-z]{1,3})\$?(\d+)$")
_COL = re.compile(r"^\$?([A-Za-z]{1,3})$")
_FILA = re.compile(r"^\$?(\d+)$")
_SIMPLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

#: Funciones que hacen que Excel salga del libro: red (WEBSERVICE, FILTERXML sobre lo traído,
#: HYPERLINK), código nativo o macros XLM (CALL, REGISTER, REGISTER.ID, EXEC), datos del equipo
#: (INFO) o servidores externos (RTD, DDE). Lista negra del escritor (revisión de seguridad 1.5).
_FUNCIONES_PELIGROSAS = (
    "WEBSERVICE",
    "HYPERLINK",
    "CALL",
    "REGISTER.ID",
    "REGISTER",
    "EXEC",
    "FILTERXML",
    "INFO",
    "RTD",
    "DDE",
)
_RX_FUNCION_PELIGROSA = re.compile(
    r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(f) for f in _FUNCIONES_PELIGROSAS) + r")\s*\(",
    re.IGNORECASE,
)


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


def _fuera_de_comillas(texto: str) -> tuple[str, str]:
    """(texto sin literales "…", texto sin literales ni nombres de hoja '…').

    Un texto entre comillas dobles es un literal (no se ejecuta); entre comillas simples va un
    nombre de hoja, que no admite `[` ni `]` pero sí `|`. Comillas sin cerrar: lo que queda se
    trata como si estuviera fuera (cuenta para la lista negra, que es lo prudente).
    """
    sin_literales: list[str] = []
    sin_citas: list[str] = []
    i, n = 0, len(texto)
    while i < n:
        ch = texto[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if texto[j] == '"':
                    if j + 1 < n and texto[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            if j >= n:  # sin cerrar
                sin_literales.append(texto[i:])
                sin_citas.append(texto[i:])
                break
            sin_literales.append('""')
            sin_citas.append('""')
            i = j + 1
            continue
        if ch == "'":
            j = i + 1
            while j < n:
                if texto[j] == "'":
                    if j + 1 < n and texto[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            if j >= n:
                sin_literales.append(texto[i:])
                sin_citas.append(texto[i:])
                break
            sin_literales.append(texto[i : j + 1])
            sin_citas.append("''")
            i = j + 1
            continue
        sin_literales.append(ch)
        sin_citas.append(ch)
        i += 1
    return "".join(sin_literales), "".join(sin_citas)


def motivo_peligro(texto: object) -> str | None:
    """Por qué una fórmula del libro ajeno no se puede escribir como fórmula, o None si se puede.

    Lista negra (revisión de seguridad 1.5): DDE (`|` fuera de comillas, o `|` delante del `!`
    de una referencia), las funciones de `_FUNCIONES_PELIGROSAS` y toda referencia a otro libro
    (`[` fuera de un literal de texto: un nombre de hoja no admite `[`).
    """
    if not isinstance(texto, str):
        return None
    sin_literales, sin_citas = _fuera_de_comillas(texto)
    if "|" in sin_citas or re.search(r"\|\s*(?:'(?:[^']|'')*')?\s*!", sin_literales):
        return "intercambio dinámico de datos (DDE): ejecutaría otro programa"
    m = _RX_FUNCION_PELIGROSA.search(sin_citas)
    if m is not None:
        return f"usa {m.group(1).upper()}, que sale del libro (red, programas o el equipo)"
    if "[" in sin_literales or "]" in sin_literales:
        return "lee otro libro (vínculo externo)"
    return None


def es_formula_peligrosa(texto: object) -> bool:
    """True si la fórmula (o regla, o nombre definido) no debe escribirse como fórmula."""
    return motivo_peligro(texto) is not None


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
