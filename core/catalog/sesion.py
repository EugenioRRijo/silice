"""Motor, esquema y sesión. Lo único que sabe de configuración de base de datos."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from core.models import Base

URL_POR_DEFECTO = "sqlite:///data/apu.db"
_PREFIJO_ARCHIVO_SQLITE = "sqlite:///"
_MEMORIA = ":memory:"


def crear_motor(url: str = URL_POR_DEFECTO) -> Engine:
    """Devuelve el motor de la URL indicada, creando el directorio del archivo si hace falta.

    Activa `PRAGMA foreign_keys` en SQLite: sin él, el motor ignora las claves foráneas y el
    esquema dejaría de ser el que documenta docs/modelo_datos.md.
    """
    _preparar_directorio(url)
    motor = create_engine(url)
    if motor.dialect.name == "sqlite":
        event.listen(motor, "connect", _activar_claves_foraneas)
    return motor


def crear_esquema(motor: Engine) -> None:
    """Crea las diecisiete tablas y sus índices si aún no existen.

    `create_all` solo crea lo que falta (`checkfirst`): una base anterior gana las tablas
    aditivas (`descarte_version`, C3; `justificacion_rendimiento`, C6) sin `ALTER TABLE` y sin
    tocar las demás ni sus filas.
    """
    Base.metadata.create_all(motor)


def abrir_sesion(motor: Engine) -> Session:
    """Abre una sesión. Se usa como gestor de contexto: `with abrir_sesion(motor) as sesion:`."""
    return Session(motor)


def _preparar_directorio(url: str) -> None:
    if not url.startswith(_PREFIJO_ARCHIVO_SQLITE):
        return
    ruta = url[len(_PREFIJO_ARCHIVO_SQLITE) :]
    if not ruta or ruta == _MEMORIA:
        return
    Path(ruta).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _activar_claves_foraneas(conexion, _registro) -> None:
    cursor = conexion.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
