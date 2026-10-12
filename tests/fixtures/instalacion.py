"""Base de la instalación de prueba (S3-1): tablas de `seguridad`, en un archivo temporal.

La deriva entre estas tablas y la revisión `ins_0001_seguridad` la vigila
`tests/integration/test_migraciones.py` (RNF-20); aquí basta `create_all`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from seguridad import cuentas
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Base, Usuario

AHORA = datetime(2026, 11, 10, 9, 0, 0)
CONTRASENA = "una contrasena larga de prueba"


@contextmanager
def instalacion(carpeta: Path) -> Iterator[Session]:
    """Una sesión sobre una `instalacion.db` nueva en `carpeta`."""
    carpeta.mkdir(parents=True, exist_ok=True)
    motor = crear_motor(carpeta / "instalacion.db")
    Base.metadata.create_all(motor)
    sesion = abrir_sesion(motor)
    try:
        yield sesion
    finally:
        sesion.close()
        motor.dispose()


def administrador(sesion: Session, carpeta: Path, login: str = "admin") -> Usuario:
    """El primer administrador, por el camino real: código de instalación y reclamo."""
    codigo = cuentas.emitir_codigo(sesion, carpeta, AHORA)
    return cuentas.reclamar_instalacion(
        sesion, codigo, login, "Admin de Prueba", CONTRASENA, AHORA, carpeta,
        freno=cuentas.FrenoGlobal(),
    )


def persona(
    sesion: Session, actor: Usuario, login: str, roles: tuple[str, ...], nombre: str = ""
) -> Usuario:
    return cuentas.crear_usuario(
        sesion, actor, login, nombre or login.title(), roles, CONTRASENA, AHORA
    )
