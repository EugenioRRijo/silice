"""Guardia del archivo que sube el usuario, antes de abrirlo con openpyxl (spec 1.5, F-D10).

El libro viene de fuera: puede ser un `.xlsm` con macros renombrado, un ZIP malformado, una
bomba de descompresión o un XML válido que pide a openpyxl un trabajo desmedido. La guardia
rechaza con un mensaje claro para el usuario, en dos pasos:

1. **El contenedor** (directorio central, sin descomprimir): extensión, tamaño, número de piezas,
   tamaños declarados y razón de compresión. Los tamaños son los declarados en el directorio
   central: `zipfile` nunca entrega más bytes que `file_size` al leer una entrada, así que el
   tamaño declarado es una cota superior fiable de lo que openpyxl descomprime.
2. **El contenido** (revisión de seguridad de la 1.5): un barrido por bloques de cada pieza, sin
   cargarla entera ni analizar el XML, que suma el área de las celdas combinadas
   (`<mergeCell ref="A1:B2"/>`) y mide el área que declara cada hoja (`<dimension ref="…"/>`).
   Por qué: openpyxl en modo normal crea un objeto por cada celda de una combinación (una sola
   combinación de 2 millones de celdas lo deja minutos colgado), y en modo de solo lectura
   recorre el área que declara `<dimension>` aunque las celdas no existan. Se barren TODAS las
   piezas y no solo `xl/worksheets/`, porque openpyxl llega a cada hoja por las relaciones del
   libro y la pieza puede llamarse de cualquier forma.

Límites (F-D10 y revisión de seguridad 1.5): 25 MiB el archivo, 5 000 entradas, 60 MiB
descomprimidos en total y 30 MiB por pieza, razón de compresión ≤ 200 por entrada y en total,
200 000 celdas combinadas por libro y 2 000 000 de celdas declaradas por hoja. Los libros reales
de la empresa están muy lejos de esos límites (medido el 2026-10-13 sobre los cinco libros: el
mayor pesa 0,3 MB, tiene 121 entradas y 1,4 MB descomprimidos, su pieza mayor ocupa 0,14 MB, su
peor razón es 13,6, combina 4 850 celdas y su hoja más grande declara 2 548).

El barrido no reconoce un XML codificado en UTF-16 (ningún libro de Excel lo usa): en ese caso no
encuentra etiquetas y no rechaza; los demás límites siguen valiendo.

Unidades: los tamaños se miden en potencias de 2 (1 MiB = 2**20 bytes) y los mensajes dicen "MiB".
"""

from __future__ import annotations

import io
import re
import zipfile
import zlib

__all__ = [
    "ArchivoRechazado",
    "EXTENSION",
    "MAX_AREA_HOJA",
    "MAX_BYTES",
    "MAX_COMBINADAS",
    "MAX_DESCOMPRIMIDO",
    "MAX_ENTRADAS",
    "MAX_PIEZA",
    "MAX_RAZON",
    "verificar_archivo",
]

EXTENSION = ".xlsx"
MAX_BYTES = 25 * 1024 * 1024
MAX_ENTRADAS = 5000
#: SUPUESTO_DECLARADO (revisión de seguridad 1.5): 60 MiB descomprimidos en total y 30 MiB por
#: pieza. Bajan de los 250 MB de F-D10 porque openpyxl en modo normal ocupa en memoria varias
#: veces el tamaño del XML; el libro real mayor descomprime 1,4 MB, así que el margen sigue siendo
#: de 40.
MAX_DESCOMPRIMIDO = 60 * 1024 * 1024
MAX_PIEZA = 30 * 1024 * 1024
MAX_RAZON = 200
#: SUPUESTO_DECLARADO (revisión de seguridad 1.5): celdas combinadas sumadas en todo el libro. El
#: libro real que más combina suma 4 850; 200 000 deja un margen de 40 veces.
MAX_COMBINADAS = 200_000
#: SUPUESTO_DECLARADO (revisión de seguridad 1.5): área que una hoja declara en `<dimension>`. La
#: hoja real más grande declara 2 548 celdas; 2 000 000 (20 000 filas × 100 columnas) es más de lo
#: que usa un presupuesto y mantiene acotado el recorrido de openpyxl en solo lectura.
MAX_AREA_HOJA = 2_000_000

#: Bloque de lectura del barrido y solape entre bloques. El solape es mayor que la etiqueta más
#: larga que el patrón admite (prefijo, hasta 256 bytes de atributos y 64 de referencia), así que
#: toda etiqueta que empieza antes del corte se ve entera en el bloque y ninguna se cuenta dos
#: veces (solo se cuentan las que empiezan antes del corte).
_BLOQUE = 1024 * 1024
_SOLAPE = 1024
_RE_ETIQUETA = re.compile(
    rb'<(?:[A-Za-z_][\w.-]{0,31}:)?(mergeCell|dimension)\s[^>]{0,256}?\bref="([^"]{1,64})"'
)
_RE_REF = re.compile(r"^\$?([A-Za-z]{1,3})\$?(\d{1,7})(?::\$?([A-Za-z]{1,3})\$?(\d{1,7}))?$")

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


def _mib(n: int) -> str:
    return f"{n / (1024 * 1024):.1f}".replace(".", ",")


def _miles(n: int) -> str:
    """Entero con punto de miles, como se escribe en Venezuela (2.000.000)."""
    return f"{n:,}".replace(",", ".")


def _columna(letras: str) -> int:
    n = 0
    for ch in letras.upper():
        n = n * 26 + ord(ch) - 64
    return n


def _area(ref: str) -> int | None:
    """Celdas que cubre una referencia `A1` o `A1:B2` (en cualquier orden de esquinas); None si
    no es una referencia de celdas (openpyxl la rechazará al abrir, no hace falta adivinar)."""
    m = _RE_REF.match(ref)
    if m is None:
        return None
    c1, f1 = _columna(m[1]), int(m[2])
    c2, f2 = (_columna(m[3]), int(m[4])) if m[3] else (c1, f1)
    return (abs(f2 - f1) + 1) * (abs(c2 - c1) + 1)


def _barrer(zf: zipfile.ZipFile, entradas: list[zipfile.ZipInfo], nombre: str) -> None:
    """Barre cada pieza por bloques buscando `<mergeCell ref>` y `<dimension ref>`.

    Corta en cuanto se pasa un límite: con un libro hostil no hace falta leer el resto. Solo
    busca con la expresión regular en los bloques que contienen alguna de las dos palabras (la
    búsqueda de una subcadena es mucho más rápida), así que la tabla de celdas se salta casi
    gratis.
    """
    combinadas = 0
    for e in entradas:
        if e.is_dir() or not e.file_size:
            continue
        pendiente = b""
        with zf.open(e) as pieza:
            while True:
                bloque = pieza.read(_BLOQUE)
                datos = pendiente + bloque
                corte = max(0, len(datos) - _SOLAPE) if bloque else len(datos)
                if b"mergeCell" in datos or b"dimension" in datos:
                    for m in _RE_ETIQUETA.finditer(datos, 0, len(datos)):
                        if m.start() >= corte:
                            break
                        area = _area(m[2].decode("ascii", "replace"))
                        if area is None:
                            continue
                        if m[1] == b"mergeCell":
                            combinadas += area
                            if combinadas > MAX_COMBINADAS:
                                raise ArchivoRechazado(
                                    f"El archivo «{nombre}» combina más de "
                                    f"{_miles(MAX_COMBINADAS)} celdas (celdas combinadas); un "
                                    "libro así bloquea la lectura. Se rechaza por seguridad: "
                                    "deshaga las combinaciones innecesarias y guárdelo de nuevo."
                                )
                        elif area > MAX_AREA_HOJA:
                            raise ArchivoRechazado(
                                f"El archivo «{nombre}» tiene una hoja que declara "
                                f"{_miles(area)} celdas (rango {m[2].decode('ascii', 'replace')}); "
                                f"el máximo es {_miles(MAX_AREA_HOJA)} por hoja. Se rechaza por "
                                "seguridad: borre las filas y columnas vacías del final y "
                                "guárdelo de nuevo."
                            )
                if not bloque:
                    break
                pendiente = datos[corte:]


def verificar_archivo(datos: bytes, nombre: str) -> None:
    """Lanza `ArchivoRechazado` si el archivo no es un `.xlsx` seguro de abrir; si lo es, no hace
    nada.

    El orden importa para el mensaje: primero lo que se ve sin abrir (extensión y tamaño), después
    el contenedor ZIP, su contenido (macros y la pieza `xl/workbook.xml`) y por último el barrido
    de celdas combinadas y dimensiones, que es lo único que descomprime.
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
            f"El archivo «{nombre}» pesa {_mib(len(datos))} MiB y supera el máximo de "
            f"{MAX_BYTES // 2**20} MiB."
        )
    try:
        zf = zipfile.ZipFile(io.BytesIO(datos))
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, OSError, EOFError) as exc:
        raise ArchivoRechazado(
            f"El archivo «{nombre}» no es un libro .xlsx válido (está dañado o no es de Excel)."
        ) from exc
    with zf:
        entradas = zf.infolist()
        _verificar_contenedor(entradas, nombre)
        try:
            _barrer(zf, entradas, nombre)
        except ArchivoRechazado:
            raise
        except (
            zipfile.BadZipFile,
            zlib.error,
            NotImplementedError,  # método de compresión que zipfile no conoce
            RuntimeError,  # pieza cifrada
            ValueError,
            OSError,
            EOFError,
        ) as exc:
            raise ArchivoRechazado(
                f"El archivo «{nombre}» no es un libro .xlsx válido (está dañado o no es de Excel)."
            ) from exc


def _verificar_contenedor(entradas: list[zipfile.ZipInfo], nombre: str) -> None:
    """Lo que se decide con el directorio central, sin descomprimir nada."""
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
        if e.file_size > MAX_PIEZA:
            raise ArchivoRechazado(
                f"El archivo «{nombre}» tiene una pieza interna ({e.filename}) que ocupa "
                f"{_mib(e.file_size)} MiB descomprimida y supera el máximo de "
                f"{MAX_PIEZA // 2**20} MiB por pieza."
            )
    if total > MAX_DESCOMPRIMIDO:
        raise ArchivoRechazado(
            f"El archivo «{nombre}» ocupa {_mib(total)} MiB descomprimido y supera el máximo de "
            f"{MAX_DESCOMPRIMIDO // 2**20} MiB."
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
