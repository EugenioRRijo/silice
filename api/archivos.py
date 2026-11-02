"""Guardado del archivo que sube el cliente en un directorio temporal.

Lo comparten `POST /listas-precios`, `POST /presupuestos/importar` y `POST /computos/{dominio}`:
el nombre lo manda el cliente y los lectores deducen el formato de su extension, asi que se
conserva, pero solo su ultimo componente. Un nombre con `..` o una ruta absoluta no puede sacar
el archivo del directorio temporal.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import UploadFile

MENSAJE_SIN_NOMBRE = "el archivo subido no trae un nombre utilizable"
LONGITUD_NOMBRE = 100
_PROHIBIDOS = re.compile(r'[<>:"|?*\x00-\x1f]')
_RESERVADOS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)


def nombre_seguro(nombre: str | None) -> str:
    """El ultimo componente del nombre, valido en Windows (`CON.csv` -> `_CON.csv`; lo que sigue a
    un `:` se descarta). `ValueError` si no queda nada."""
    ultimo = re.split(r"[\\/]", nombre or "")[-1].split(":", 1)[0]
    limpio = _PROHIBIDOS.sub("_", ultimo).strip().rstrip(" .")
    if not limpio:
        raise ValueError(MENSAJE_SIN_NOMBRE)
    if limpio.split(".")[0].rstrip().upper() in _RESERVADOS:
        limpio = f"_{limpio}"
    if len(limpio) > LONGITUD_NOMBRE:
        extension = Path(limpio).suffix[:16]
        base = limpio[: len(limpio) - len(Path(limpio).suffix)]
        limpio = (base[: LONGITUD_NOMBRE - len(extension)].rstrip(" .") or "archivo") + extension
    return limpio


def guardar_subida(directorio: str | Path, archivo: UploadFile) -> Path:
    """Escribe `archivo` en `directorio` con el ultimo componente de su nombre y devuelve la ruta.

    `ValueError` (422) si el cliente no manda nombre utilizable: sin el, no hay extension con la
    que elegir el lector.
    """
    ruta = Path(directorio) / nombre_seguro(archivo.filename)
    ruta.write_bytes(archivo.file.read())
    return ruta
