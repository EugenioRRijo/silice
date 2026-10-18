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
from operacion.instalacion import motor_de_instalacion, sesion_de_instalacion

VARIABLE_BASE = "APU_BASE"
_PREFIJO_ARCHIVO = "sqlite:///"
#: El `usuario` de lo que crean las rutas antiguas, que S3 no protege con clave (S5 decide).
USUARIO_SIN_CLAVE = "api (sin clave)"
#: El `usuario` de lo que escriben las rutas con clave (RT-S4-4): `exigir_clave_api` no entrega la
#: identidad de la clave a la ruta, así que la bitácora dice solo que fue por la API.
USUARIO_API = "api (clave de API)"
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


def sesion_instalacion_api() -> Iterator[Session]:
    """Sesión de `instalacion.db` por petición (arenera, RT-S4-1). Cada petición es una transacción:
    al terminar bien hace `commit`; si la ruta lanza cualquier excepción (un 4xx incluido), hace
    `rollback` y la vuelve a lanzar. Los servicios de `produccion/` solo hacen `flush`.

    Se abre la transacción con un `BEGIN` explícito: `pysqlite` no emite `BEGIN` antes de un
    `SAVEPOINT` (solo antes de un `INSERT`/`UPDATE`/`DELETE`) y, sin él, el `RELEASE` del primer
    `begin_nested()` de un servicio confirmaría todo y el `rollback` posterior no deshace nada."""
    try:
        motor_de_instalacion()  # la prepara y migra una vez por proceso; una base mala es un 503
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    with sesion_de_instalacion() as sesion:
        sesion.connection().exec_driver_sql("BEGIN")
        try:
            yield sesion
            sesion.commit()
        except BaseException:
            sesion.rollback()
            raise


#: `scope="function"`: la salida del generador (el `commit`) corre al volver la ruta, ANTES de
#: enviar la respuesta; con el alcance por omisión correría después y un cliente podría leer antes
#: del commit.
SesionInstalacionDep = Annotated[Session, Depends(sesion_instalacion_api, scope="function")]
