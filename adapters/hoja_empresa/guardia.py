"""Guardia del archivo que sube el usuario, antes de abrirlo con openpyxl (spec 1.5, F-D10).

El libro viene de fuera: puede ser un `.xlsm` con macros renombrado, un ZIP malformado o una
bomba de descompresión. Esta guardia mira solo el contenedor ZIP (el directorio central), sin
descomprimir nada, y rechaza con un mensaje claro para el usuario. Los tamaños que usa son los
declarados en el directorio central: `zipfile` nunca entrega más bytes que `file_size` al leer una
entrada, así que el tamaño declarado es una cota superior fiable de lo que openpyxl descomprime.

Límites (F-D10): 25 MB el archivo, 5 000 entradas, 250 MB descomprimidos en total y razón de
compresión ≤ 200 por entrada y en total. Los libros reales de la empresa están muy lejos de esos
límites (el mayor pesa 0,3 MB, tiene 121 entradas y su peor razón es 13,6).
"""

from __future__ import annotations

import io
import zipfile

__all__ = [
    "ArchivoRechazado",
    "EXTENSION",
    "MAX_BYTES",
    "MAX_DESCOMPRIMIDO",
    "MAX_ENTRADAS",
    "MAX_RAZON",
    "verificar_archivo",
]

EXTENSION = ".xlsx"
MAX_BYTES = 25 * 1024 * 1024
MAX_ENTRADAS = 5000
MAX_DESCOMPRIMIDO = 250 * 1024 * 1024
MAX_RAZON = 200

_CON_MACROS = {
    ".xlsm": "es un libro con macros (.xlsm)",
    ".xlsb": "es un libro binario (.xlsb)",
    ".xls": "es un libro de Excel 97-2003 (.xls)",
    ".xltm": "es una plantilla con macros (.xltm)",
}


class ArchivoRechazado(ValueError):  # noqa: N818 (nombre fijado por el contrato 1.5)
    """El archivo no se procesa. El mensaje está escrito para mostrarlo al usuario tal cual."""


def _extension(nombre: str) -> str:
    base = nombre.replace("\\", "/").rsplit("/", 1)[-1].strip()
    punto = base.rfind(".")
    return base[punto:].lower() if punto > 0 else ""


def _mb(n: int) -> str:
    return f"{n / (1024 * 1024):.1f}".replace(".", ",")


def verificar_archivo(datos: bytes, nombre: str) -> None:
    """Lanza `ArchivoRechazado` si el archivo no es un `.xlsx` seguro de abrir; si lo es, no hace
    nada.

    El orden importa para el mensaje: primero lo que se ve sin abrir (extensión y tamaño), después
    el contenedor ZIP y por último su contenido (macros y la pieza `xl/workbook.xml`).
    """
    ext = _extension(nombre)
    if ext != EXTENSION:
        motivo = _CON_MACROS.get(
            ext, f"tiene la extensión {ext!r}" if ext else "no tiene extensión"
        )
        raise ArchivoRechazado(
            f"El archivo «{nombre}» {motivo}. Solo se aceptan libros de Excel .xlsx sin macros: "
            "ábralo en Excel y guárdelo como «Libro de Excel (.xlsx)»."
        )
    if len(datos) > MAX_BYTES:
        raise ArchivoRechazado(
            f"El archivo «{nombre}» pesa {_mb(len(datos))} MB y supera el máximo de "
            f"{MAX_BYTES // 2**20} MB."
        )
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as zf:
            entradas = zf.infolist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, OSError, EOFError) as exc:
        raise ArchivoRechazado(
            f"El archivo «{nombre}» no es un libro .xlsx válido (está dañado o no es de Excel)."
        ) from exc

    if len(entradas) > MAX_ENTRADAS:
        raise ArchivoRechazado(
            f"El archivo «{nombre}» tiene {len(entradas)} piezas internas; el máximo es "
            f"{MAX_ENTRADAS}. No parece un libro de presupuesto."
        )
    total = 0
    comprimido = 0
    for e in entradas:
        total += e.file_size
        comprimido += e.compress_size
        if e.file_size and (e.compress_size == 0 or e.file_size > MAX_RAZON * e.compress_size):
            raise ArchivoRechazado(
                f"El archivo «{nombre}» tiene una pieza interna ({e.filename}) con una compresión "
                f"anómala (más de {MAX_RAZON} a 1). Se rechaza por seguridad."
            )
    if total > MAX_DESCOMPRIMIDO:
        raise ArchivoRechazado(
            f"El archivo «{nombre}» ocupa {_mb(total)} MB descomprimido y supera el máximo de "
            f"{MAX_DESCOMPRIMIDO // 2**20} MB."
        )
    if total and (comprimido == 0 or total > MAX_RAZON * comprimido):
        raise ArchivoRechazado(
            f"El archivo «{nombre}» tiene una compresión anómala (más de {MAX_RAZON} a 1). "
            "Se rechaza por seguridad."
        )

    nombres = {e.filename.replace("\\", "/") for e in entradas}
    if any(n.rsplit("/", 1)[-1].lower() == "vbaproject.bin" for n in nombres):
        raise ArchivoRechazado(
            f"El archivo «{nombre}» contiene macros (vbaProject.bin) aunque su extensión sea "
            ".xlsx. Guárdelo de nuevo como «Libro de Excel (.xlsx)» sin macros."
        )
    if "xl/workbook.xml" not in nombres:
        raise ArchivoRechazado(
            f"El archivo «{nombre}» no tiene la estructura de un libro de Excel (falta "
            "xl/workbook.xml)."
        )
