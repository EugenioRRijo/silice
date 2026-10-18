"""Sesion de base de datos por peticion. Lo unico de la API que sabe de configuracion.

El caso se abre por `operacion.base_datos.preparar_base` (RV-5, spec S5 §5.2): el de `APU_BASE` (que
en el producto fija el lanzador) o, sin ella, el caso por defecto de la carpeta de datos. Una base
que no se puede preparar (mas nueva, ilegible, bloqueada, no adoptable) responde 503 con el mensaje,
sin crear tablas.

Caso por sesion web (RM-2, sesion 2b): una peticion con la cookie de una ficha que eligio caso
(`api.caso_web`) trabaja en ese caso; con la clave de API (`X-Silice-Clave`), o sin eleccion, en el
del proceso. El motor de SQLAlchemy se guarda **uno por ruta de caso** (`obtener_motor`): la base se
prepara una sola vez por proceso y caso. Quien llega aqui ya paso la dependencia de acceso de su
ruta (`api.sesion_web.exigir_clave_o_sesion`), que valido la ficha.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from api import caso_web
from api.sesion_web import COOKIE
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import ErrorDeBase, preparar_base
from operacion.config import ruta_caso_por_defecto
from seguridad import claves_api, sesiones

VARIABLE_BASE = "APU_BASE"
_PREFIJO_ARCHIVO = "sqlite:///"
#: El `usuario` de lo que crean las rutas antiguas, que S3 no protege con clave (S5 decide).
USUARIO_SIN_CLAVE = "api (sin clave)"
_motores: dict[str, Engine] = {}
_cerrojo = threading.Lock()


def url_por_defecto() -> str:
    return url_de_ruta(ruta_caso_por_defecto())


def url_de_ruta(ruta: Path) -> str:
    return f"{_PREFIJO_ARCHIVO}{Path(ruta).as_posix()}"


def ruta_de_url(url: str) -> Path | None:
    """El archivo de una URL `sqlite:///...`; `None` si no es un archivo SQLite."""
    if not url.startswith(_PREFIJO_ARCHIVO):
        return None
    ruta = url[len(_PREFIJO_ARCHIVO) :]
    return Path(ruta) if ruta and ruta != ":memory:" else None


def url_del_proceso() -> str:
    """El caso del proceso: `APU_BASE` o el por defecto de la carpeta de datos."""
    return os.environ.get(VARIABLE_BASE, "").strip() or url_por_defecto()


def url_de_la_peticion(request: Request) -> str:
    """El caso de esta peticion: el elegido por su ficha (RM-2) o, con la clave de API o sin
    eleccion, el del proceso. No abre la base."""
    if claves_api.CABECERA in request.headers:
        return url_del_proceso()
    ficha = request.cookies.get(COOKIE)
    if ficha:
        ruta = caso_web.elegido(sesiones.huella_de(ficha))
        if ruta is not None:
            return url_de_ruta(ruta)
    return url_del_proceso()


def obtener_motor(url: str) -> Engine:
    """El motor del caso `url`, uno por proceso: la primera vez prepara la base (503 si no se
    puede, sin guardar el motor)."""
    with _cerrojo:
        motor = _motores.get(url)
        if motor is None:
            ruta = ruta_de_url(url)
            if ruta is not None:
                try:
                    preparar_base(ruta)
                except ErrorDeBase as error:
                    raise HTTPException(status_code=503, detail=str(error)) from error
            motor = _motores[url] = crear_motor(url)
        return motor


def cerrar_motores() -> None:
    """Cierra y olvida todos los motores (las pruebas; en Windows un motor abierto retiene el
    archivo del caso)."""
    with _cerrojo:
        for motor in _motores.values():
            motor.dispose()
        _motores.clear()


def sesion_api(request: Request) -> Iterator[Session]:
    with abrir_sesion(obtener_motor(url_de_la_peticion(request))) as sesion:
        yield sesion


#: Alias de tipo para inyectar la sesion en las rutas sin disparar B008 (ruff): un `Depends(...)`
#: como valor por defecto es una llamada en la firma; dentro de `Annotated` no lo es.
SesionDep = Annotated[Session, Depends(sesion_api)]
