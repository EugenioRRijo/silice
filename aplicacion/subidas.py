r"""Guardado seguro de los archivos que el usuario sube a Streamlit (A-1, INV-123, RNF-12).

`UploadedFile.name` lo manda el navegador tal cual. Unirlo a una carpeta (`Path(carpeta) /
archivo.name`) deja que `..\..\x`, `/etc/passwd` o `C:\...` saquen el archivo de la carpeta
temporal, y que un nombre reservado de Windows (`CON`, `NUL`, `COM1`...) falle al escribirse. Esta
es la unica funcion de guardado de las pantallas con subida (`actualizacion` y `elaborar`).

Imita las reglas de `api/archivos.py:guardar_subida` (que es para `fastapi.UploadFile` y no se
reutiliza tal cual: `ui` no importa `api`): se conserva solo el **ultimo componente** del nombre,
porque los lectores deducen el formato de su extension, y un nombre sin componente utilizable es
un `ValueError`. Reglas adicionales, propias de Windows: los componentes se separan por `/` y por
`\` en cualquier sistema (la subida viene de otro equipo); los caracteres que Windows prohibe
(`<>"|?*` y los de control) pasan a `_`; el primer `:` corta el nombre
(flujos alternos de datos de NTFS); los
espacios y puntos finales se quitan; un nombre
reservado se renombra con un `_` delante (se prefiere salvar el archivo a rechazarlo); y el nombre
se acota a `LONGITUD_MAXIMA` caracteres conservando la extension.

Sin Streamlit: una subida es cualquier objeto con `name` y `getvalue()`. Vive en la capa de
aplicacion (RM-1, T7 de la migracion final) porque la recepcion de un paquete
(`aplicacion.revision.recibir`) guarda el archivo con este nombre y la capa no puede importar
`ui/`; `ui/subidas.py` lo reexporta para las pantallas.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

__all__ = ["LONGITUD_MAXIMA", "Subida", "guardar_subida", "nombre_seguro"]

LONGITUD_MAXIMA = 100
_EXTENSION_MAXIMA = 16
_SEPARADORES = re.compile(r"[\\/]")
_PROHIBIDOS = re.compile(r'[<>:"|?*\x00-\x1f]')
_RESERVADOS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
    | {"CONIN$", "CONOUT$"}
    | {f"COM{c}" for c in "¹²³"}
    | {f"LPT{c}" for c in "¹²³"}
)
_SIN_NOMBRE = "El archivo subido no trae un nombre utilizable"


class Subida(Protocol):
    """Lo que se usa de un `UploadedFile` de Streamlit."""

    name: str

    def getvalue(self) -> bytes: ...


def nombre_seguro(nombre: str | None) -> str:
    """El nombre con el que se guarda una subida: un solo componente, valido en Windows.

    `ValueError` si no queda nada utilizable (vacio, `.`, `..`, solo separadores o puntos).
    """
    ultimo = _SEPARADORES.split(nombre or "")[-1]
    # El primer `:` corta: lo que sigue es un flujo alterno de datos de NTFS (`a.csv:x`,
    # `a.csv::$DATA`) y cambiaria lo que el lector entiende por extension.
    ultimo = ultimo.split(":", 1)[0]
    limpio = _PROHIBIDOS.sub("_", ultimo).strip().rstrip(" .")
    if not limpio:
        raise ValueError(_SIN_NOMBRE)
    if limpio.split(".")[0].rstrip().upper() in _RESERVADOS:
        limpio = f"_{limpio}"
    if len(limpio) > LONGITUD_MAXIMA:
        extension = Path(limpio).suffix[:_EXTENSION_MAXIMA]
        base = limpio[: len(limpio) - len(Path(limpio).suffix)]
        base = base[: LONGITUD_MAXIMA - len(extension)].rstrip(" .")
        limpio = (base or "archivo") + extension
    return limpio


def guardar_subida(directorio: str | Path, archivo: Subida) -> Path:
    """Escribe `archivo` en `directorio` con su nombre seguro y devuelve la ruta.

    `ValueError` si el cliente no manda un nombre utilizable; en ese caso no escribe nada.
    """
    destino = Path(directorio) / nombre_seguro(archivo.name)
    destino.write_bytes(archivo.getvalue())
    return destino
