"""Sesion de base de datos por peticion. Lo unico de la API que sabe de configuracion.

El caso se abre por `operacion.base_datos.preparar_base` (RV-5, spec S5 §5.2): el de `APU_BASE` (que
en el producto fija el lanzador) o, sin ella, el caso por defecto de la carpeta de datos. Una base
que no se puede preparar (mas nueva, ilegible, bloqueada, no adoptable) responde 503 con el mensaje,
sin crear tablas.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from operacion.config import ruta_caso_por_defecto

VARIABLE_BASE = "APU_BASE"
_PREFIJO_ARCHIVO = "sqlite:///"
#: El `usuario` de lo que crean las rutas antiguas, que S3 no protege con clave (S5 decide).
USUARIO_SIN_CLAVE = "api (sin clave)"
_motor = None


def url_por_defecto() -> str:
    return f"{_PREFIJO_ARCHIVO}{ruta_caso_por_defecto().as_posix()}"


def ruta_de_url(url: str) -> Path | None:
    """El archivo de una URL `sqlite:///...`; `None` si no es un archivo SQLite."""
    if not url.startswith(_PREFIJO_ARCHIVO):
        return None
    ruta = url[len(_PREFIJO_ARCHIVO) :]
    return Path(ruta) if ruta and ruta != ":memory:" else None


def _obtener_motor():
    global _motor
    if _motor is None:
        url = os.environ.get(VARIABLE_BASE, "").strip() or url_por_defecto()
        ruta = ruta_de_url(url)
        if ruta is not None:
            try:
                preparar_base(ruta)
            except ErrorDeBase as error:
                raise HTTPException(status_code=503, detail=str(error)) from error
        _motor = crear_motor(url)
    return _motor


def sesion_api() -> Iterator[Session]:
    with abrir_sesion(_obtener_motor()) as sesion:
        yield sesion


#: Alias de tipo para inyectar la sesion en las rutas sin disparar B008 (ruff): un `Depends(...)`
#: como valor por defecto es una llamada en la firma; dentro de `Annotated` no lo es.
SesionDep = Annotated[Session, Depends(sesion_api)]
