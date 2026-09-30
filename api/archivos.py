"""Guardado del archivo que sube el cliente en un directorio temporal.

Lo comparten `POST /listas-precios`, `POST /presupuestos/importar` y `POST /computos/{dominio}`:
el nombre lo manda el cliente y los lectores deducen el formato de su extension, asi que se
conserva, pero solo su ultimo componente. Un nombre con `..` o una ruta absoluta no puede sacar
el archivo del directorio temporal.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile


def guardar_subida(directorio: str | Path, archivo: UploadFile) -> Path:
    """Escribe `archivo` en `directorio` con el ultimo componente de su nombre y devuelve la ruta.

    `ValueError` (422) si el cliente no manda nombre utilizable: sin el, no hay extension con la
    que elegir el lector.
    """
    nombre = Path(archivo.filename or "").name
    if nombre in ("", ".", ".."):
        raise ValueError("el archivo subido no trae un nombre utilizable")
    ruta = Path(directorio) / nombre
    ruta.write_bytes(archivo.file.read())
    return ruta
