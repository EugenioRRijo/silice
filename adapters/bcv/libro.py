"""Abre un libro del BCV (.xls con xlrd, .xlsx con openpyxl; ambos importados en la función) y lo
entrega como cuadrícula neutra. Un número que llega como float se lleva a Decimal con repr y se
declara en `Libro.avisos` (S1 §7.2)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from adapters.bcv.informe import FormatoNoReconocido

Celda = str | Decimal | date | None
LIMITE_BYTES = 20 * 1024 * 1024
FIRMA_OLE2 = bytes.fromhex("D0CF11E0A1B11AE1")
FIRMA_ZIP = b"PK\x03\x04"


@dataclass(frozen=True, slots=True)
class Hoja:
    nombre: str
    filas: tuple[tuple[Celda, ...], ...]


@dataclass(frozen=True, slots=True)
class Libro:
    archivo: str
    huella: str
    hojas: tuple[Hoja, ...]
    avisos: tuple[str, ...] = ()


def abrir_libro(ruta: Path) -> Libro:
    tamano = ruta.stat().st_size
    if tamano > LIMITE_BYTES:
        raise FormatoNoReconocido(f"{ruta.name}: pesa {tamano / 2**20:.1f} MB; el limite es 20 MB")
    contenido = ruta.read_bytes()
    sufijo = ruta.suffix.lower()
    if sufijo == ".xls":
        if not contenido.startswith(FIRMA_OLE2):
            extra = " (es un .xlsx renombrado)" if contenido.startswith(FIRMA_ZIP) else ""
            raise FormatoNoReconocido(
                f"{ruta.name}: la extension .xls no coincide con el contenido{extra}"
            )
        hojas, floats = _xls(contenido, ruta.name)
    elif sufijo == ".xlsx":
        if not contenido.startswith(FIRMA_ZIP):
            raise FormatoNoReconocido(
                f"{ruta.name}: la extension .xlsx no coincide con el contenido"
            )
        hojas, floats = _xlsx(ruta)
    else:
        raise FormatoNoReconocido(f"{ruta.name}: se leen .xls y .xlsx")
    avisos = (
        (f"{floats} celdas numericas leidas como float y llevadas a Decimal con repr",)
        if floats
        else ()
    )
    return Libro(ruta.name, hashlib.sha256(contenido).hexdigest(), hojas, avisos)


def _xls(contenido: bytes, nombre: str) -> tuple[tuple[Hoja, ...], int]:
    import xlrd  # extra `bcv` (RV‑24), importación diferida

    try:
        libro = xlrd.open_workbook(file_contents=contenido)
    except Exception as error:  # xlrd lanza varias clases ante un archivo dañado
        raise FormatoNoReconocido(f"{nombre}: no se pudo abrir ({error})") from None
    floats, hojas = 0, []
    for hoja in libro.sheets():
        filas = []
        for r in range(hoja.nrows):
            fila: list[Celda] = []
            for c in range(hoja.ncols):
                celda = hoja.cell(r, c)
                if celda.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    fila.append(None)
                elif celda.ctype == xlrd.XL_CELL_TEXT:
                    fila.append(celda.value.strip() or None)
                elif celda.ctype == xlrd.XL_CELL_NUMBER:
                    floats += 1
                    fila.append(Decimal(repr(celda.value)))
                elif celda.ctype == xlrd.XL_CELL_DATE:
                    fila.append(xlrd.xldate_as_datetime(celda.value, libro.datemode).date())
                else:
                    fila.append(str(celda.value))
            filas.append(tuple(fila))
        hojas.append(Hoja(hoja.name, tuple(filas)))
    return tuple(hojas), floats


def _xlsx(ruta: Path) -> tuple[tuple[Hoja, ...], int]:
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    floats, hojas = 0, []
    try:
        for hoja in libro.worksheets:
            filas = []
            for valores in hoja.iter_rows(values_only=True):
                fila: list[Celda] = []
                for v in valores:
                    if isinstance(v, float):
                        floats += 1
                        fila.append(Decimal(repr(v)))
                    elif isinstance(v, int) and not isinstance(v, bool):
                        fila.append(Decimal(v))
                    elif isinstance(v, datetime):
                        fila.append(v.date())
                    elif isinstance(v, str):
                        fila.append(v.strip() or None)
                    else:
                        fila.append(None if v is None else str(v))
                filas.append(tuple(fila))
            hojas.append(Hoja(hoja.title, tuple(filas)))
    finally:
        libro.close()
    return tuple(hojas), floats
