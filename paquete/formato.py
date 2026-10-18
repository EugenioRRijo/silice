"""Formato `.silice` v1 y su lectura con límites (spec S3 §8.1 y §8.4; maestro §4.5, RV-8).

Un ZIP con nombres fijos y ningún otro. Se lee **en memoria, sin extraer al disco y sin confiar en
los tamaños de las cabeceras**: cada entrada se lee con tope (`read(limite + 1)`) contando los
bytes reales. Los límites son `SUPUESTO_DECLARADO` hasta medir paquetes reales, y cada uno tiene su
frontera exacta (pasa / se rechaza):

| Límite | Pasa | Se rechaza |
|---|---|---|
| tamaño del archivo | 20 MiB (20 971 520 B) | 20 971 521 B |
| descomprimido por entrada | 50 MiB (52 428 800 B) | 52 428 801 B |
| descomprimido en total | 100 MiB (104 857 600 B) | 104 857 601 B |
| relación de compresión por entrada | 100:1 | 101:1 |
| renglones más líneas de composición | 200 000 | 200 001 |
| anidamiento de cualquier JSON | 64 niveles | 65 |

Además se rechaza: nombre fuera de la lista, nombre repetido, ruta absoluta, con `..` o con barra
invertida, entrada cifrada y método de compresión que no sea almacenado o *deflate*.
"""

from __future__ import annotations

import io
import zipfile
import zlib
from collections import Counter
from collections.abc import Mapping

from core.budget.cadena import huella_de_anexos
from seguridad.json_estricto import JsonRechazado, leer_json

__all__ = [
    "ANEXOS_ADMITIDOS",
    "FORMATO_PAQUETE",
    "LIMITE_ARCHIVO",
    "LIMITE_ENTRADA",
    "LIMITE_FILAS",
    "LIMITE_TOTAL",
    "NOMBRES_FIJOS",
    "OBLIGATORIOS",
    "RELACION_MAXIMA",
    "VERSION_FORMATO",
    "JsonRechazado",
    "PaqueteRechazado",
    "abrir_zip",
    "huella_de_anexos",
    "leer_json",
    "relacion_aceptable",
]

FORMATO_PAQUETE = "silice-paquete"
VERSION_FORMATO = 1
EXTENSION = ".silice"

NOMBRE_MANIFIESTO = "manifiesto.json"
NOMBRE_FIRMA = "firma.ed25519"
NOMBRES_FIJOS = (
    NOMBRE_MANIFIESTO,
    NOMBRE_FIRMA,
    "presupuesto.json",
    "informe.json",
    "cadena.json",
)
ANEXOS_ADMITIDOS = (
    "anexos/espacio.json",
    "anexos/reajuste.json",
    "anexos/control.json",
    "anexos/ia.json",
)
OBLIGATORIOS = (NOMBRE_MANIFIESTO, "presupuesto.json", "informe.json", "cadena.json")
ADMITIDOS = frozenset(NOMBRES_FIJOS) | frozenset(ANEXOS_ADMITIDOS)

MIB = 1024 * 1024
LIMITE_ARCHIVO = 20 * MIB  # 20 971 520
LIMITE_ENTRADA = 50 * MIB  # 52 428 800
LIMITE_TOTAL = 100 * MIB  # 104 857 600
RELACION_MAXIMA = 100
LIMITE_FILAS = 200_000
METODOS_ADMITIDOS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)


class PaqueteRechazado(ValueError):  # noqa: N818
    """El archivo no se puede abrir como paquete; el mensaje dice por qué y qué hacer."""


def relacion_aceptable(descomprimido: int, comprimido: int) -> bool:
    """`descomprimido <= 100 x comprimido`, en enteros (100:1 pasa, 101:1 se rechaza)."""
    return descomprimido <= RELACION_MAXIMA * comprimido


def _nombre_inseguro(nombre: str) -> bool:
    return (
        nombre.startswith(("/", "\\"))
        or "\\" in nombre
        or ":" in nombre
        or any(parte in {"..", "."} for parte in nombre.split("/"))
        or nombre.endswith("/")
    )


def abrir_zip(datos: bytes) -> dict[str, bytes]:
    """Los archivos del paquete por nombre, o `PaqueteRechazado`. No toca el disco."""
    if len(datos) > LIMITE_ARCHIVO:
        raise PaqueteRechazado(
            f"El archivo pesa {len(datos)} bytes y el máximo es {LIMITE_ARCHIVO} (20 MiB). "
            "Pida al emisor un paquete más pequeño."
        )
    try:
        zip_ = zipfile.ZipFile(io.BytesIO(datos))
    # `NotImplementedError`: un byte dañado en la versión del ZIP («zip file version 23.5»).
    except (zipfile.BadZipFile, OSError, ValueError, NotImplementedError):
        raise PaqueteRechazado(
            "El archivo no es un paquete de Silice válido (el ZIP está dañado). Pida uno nuevo."
        ) from None
    with zip_:
        informacion = zip_.infolist()
        repetidos = [n for n, c in Counter(i.filename for i in informacion).items() if c > 1]
        if repetidos:
            raise PaqueteRechazado(f"El paquete repite el archivo {repetidos[0]!r}: es inseguro.")
        for i in informacion:
            if _nombre_inseguro(i.filename):
                raise PaqueteRechazado(f"El paquete trae una ruta insegura: {i.filename!r}.")
            if i.filename not in ADMITIDOS:
                raise PaqueteRechazado(f"El paquete trae un archivo no admitido: {i.filename!r}.")
            if i.flag_bits & 0x1:
                raise PaqueteRechazado(f"El archivo {i.filename!r} del paquete está cifrado.")
            if i.compress_type not in METODOS_ADMITIDOS:
                raise PaqueteRechazado(
                    f"El archivo {i.filename!r} usa un método de compresión no admitido."
                )
        contenido: dict[str, bytes] = {}
        total = 0
        for i in informacion:
            try:
                with zip_.open(i) as flujo:
                    octetos = flujo.read(LIMITE_ENTRADA + 1)
            except (
                zipfile.BadZipFile,
                EOFError,
                OSError,
                RuntimeError,
                NotImplementedError,
                ValueError,  # un desplazamiento dañado da «negative seek value» al abrir la entrada
                zlib.error,  # un flujo DEFLATE dañado no es BadZipFile: tampoco debe escapar
            ):
                raise PaqueteRechazado(
                    f"El archivo {i.filename!r} del paquete está dañado. Pida uno nuevo."
                ) from None
            if len(octetos) > LIMITE_ENTRADA:
                raise PaqueteRechazado(
                    f"El archivo {i.filename!r} descomprimido excede {LIMITE_ENTRADA} bytes."
                )
            total += len(octetos)
            if total > LIMITE_TOTAL:
                raise PaqueteRechazado(
                    f"El paquete descomprimido excede {LIMITE_TOTAL} bytes en total (bomba de "
                    "compresión)."
                )
            if not relacion_aceptable(len(octetos), i.compress_size):
                raise PaqueteRechazado(
                    f"El archivo {i.filename!r} se comprime más de {RELACION_MAXIMA}:1: es "
                    "sospechoso."
                )
            contenido[i.filename] = octetos
    return contenido


def comprobar_salida(archivos: Mapping[str, bytes], tamano_zip: int) -> None:
    """Lo que `exportar` exige antes de ofrecer el paquete: que el revisor no lo rechace (22f)."""
    if tamano_zip > LIMITE_ARCHIVO:
        raise PaqueteRechazado(
            f"El paquete pesaría {tamano_zip} bytes y el máximo es {LIMITE_ARCHIVO}: no se "
            "genera un paquete que el revisor rechazaría."
        )
    for nombre, octetos in archivos.items():
        if len(octetos) > LIMITE_ENTRADA:
            raise PaqueteRechazado(f"{nombre} excede {LIMITE_ENTRADA} bytes: no se genera.")
    if sum(len(o) for o in archivos.values()) > LIMITE_TOTAL:
        raise PaqueteRechazado("El paquete excede el total descomprimido permitido.")
