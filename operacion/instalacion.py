"""La base de la instalación, abierta una vez por proceso (spec S3 §4.2; DA-S3-2).

Cuentas, sesiones, claves y registro de accesos viven en `instalacion.db`, no en el caso. La
interfaz (`ui.sesion`) y la API (`api.dependencias`) la abren con esta única función: crea y migra
la base con `preparar_base(ruta, Destino.INSTALACION)` y entrega un motor por ruta (un pool de
conexiones: estado del proceso, no de un usuario; excepción declarada de S3 §4.4). Ninguna crea
carpetas por su cuenta fuera de lo que hace `preparar_base`.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from operacion.base_datos import Destino, preparar_base
from operacion.config import ruta_instalacion
from seguridad.base import abrir_sesion, crear_motor

__all__ = ["cerrar_motores", "motor_de_instalacion", "sesion_de_instalacion"]

_MOTORES: dict[Path, Engine] = {}
_CANDADO = threading.Lock()


def motor_de_instalacion(entorno: Mapping[str, str] | None = None) -> Engine:
    ruta = ruta_instalacion(entorno)
    with _CANDADO:
        motor = _MOTORES.get(ruta)
        if motor is None:
            preparar_base(ruta, Destino.INSTALACION)
            motor = _MOTORES[ruta] = crear_motor(ruta)
        return motor


@contextmanager
def sesion_de_instalacion(entorno: Mapping[str, str] | None = None) -> Iterator[Session]:
    sesion = abrir_sesion(motor_de_instalacion(entorno))
    try:
        yield sesion
    finally:
        sesion.close()


def cerrar_motores() -> None:
    """Solo para las pruebas y para el cierre ordenado: cierra los pools abiertos."""
    with _CANDADO:
        for motor in _MOTORES.values():
            motor.dispose()
        _MOTORES.clear()
