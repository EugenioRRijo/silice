"""Abrir una base de Sílice (RF-96; spec S5 §6). Capa de Alembic: destinos, revisiones y migrar.

Dos destinos (DA-S5-7): la base de cada caso y la de la instalación, cada una con su entorno en
`migraciones/<destino>/` y su `alembic_version`. Sin `alembic.ini`: la configuración se arma aquí
y la conexión se entrega en `config.attributes["connection"]`.
"""

from __future__ import annotations

import functools
from enum import StrEnum
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Engine, create_engine

import migraciones
from migraciones.comun import BaseNoAdoptable, ErrorDeBase

CARPETA_MIGRACIONES = Path(migraciones.__file__).resolve().parent

__all__ = ["BaseNoAdoptable", "ErrorDeBase"]


class Destino(StrEnum):
    CASO = "caso"
    INSTALACION = "instalacion"


class MigracionFallida(ErrorDeBase):  # noqa: N818
    """Una revisión falló o dejó la base inconsistente; la base original no se modificó."""


def _configuracion(destino: Destino) -> Config:
    configuracion = Config()
    ubicacion = str(CARPETA_MIGRACIONES / destino.value).replace("%", "%%")
    configuracion.set_main_option("script_location", ubicacion)
    configuracion.set_main_option("path_separator", "os")
    configuracion.set_main_option("version_path_separator", "os")
    return configuracion


@functools.cache
def _guion(destino: Destino) -> ScriptDirectory:
    return ScriptDirectory.from_config(_configuracion(destino))


def revision_head(destino: Destino) -> str | None:
    """La última revisión del destino; `None` mientras no tenga ninguna (la instalación hoy)."""
    return _guion(destino).get_current_head()


def revisiones_conocidas(destino: Destino) -> frozenset[str]:
    return frozenset(script.revision for script in _guion(destino).walk_revisions())


def revisiones_en_orden(destino: Destino) -> list[str]:
    """De la base a `head`."""
    return list(reversed([script.revision for script in _guion(destino).walk_revisions()]))


def motor_de_migracion(ruta: Path) -> Engine:
    """Motor SIN `PRAGMA foreign_keys`: el modo batch de Alembic recrea tablas y, con las claves
    activas, borrar la tabla vieja dispararía las foráneas. Se comprueban al terminar."""
    return create_engine(URL.create("sqlite", database=str(ruta)))


def aplicar_revisiones(ruta: Path, destino: Destino, objetivo: str = "head") -> None:
    """`upgrade` hasta `objetivo` y, después, `foreign_key_check` e `integrity_check`."""
    motor = motor_de_migracion(ruta)
    try:
        with motor.begin() as conexion:
            configuracion = _configuracion(destino)
            configuracion.attributes["connection"] = conexion
            command.upgrade(configuracion, objetivo)
        with motor.connect() as conexion:
            rotas = conexion.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            integridad = [str(f[0]) for f in conexion.exec_driver_sql("PRAGMA integrity_check")]
    finally:
        motor.dispose()
    if rotas:
        raise MigracionFallida(
            f"Tras migrar {ruta.name} quedaron {len(rotas)} filas con claves foráneas rotas."
        )
    if integridad != ["ok"]:
        raise MigracionFallida(
            f"Tras migrar {ruta.name}, integrity_check: {'; '.join(integridad[:5])}."
        )


def deshacer_revisiones(ruta: Path, destino: Destino, objetivo: str = "base") -> None:
    """`downgrade` (DA-S5-6): existe y se prueba en la CI; nunca se ofrece al usuario."""
    motor = motor_de_migracion(ruta)
    try:
        with motor.begin() as conexion:
            configuracion = _configuracion(destino)
            configuracion.attributes["connection"] = conexion
            command.downgrade(configuracion, objetivo)
    finally:
        motor.dispose()
