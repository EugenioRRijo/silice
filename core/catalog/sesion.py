"""Motor, esquema y sesión. Lo único que sabe de configuración de base de datos."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from core.models import Base

URL_POR_DEFECTO = "sqlite:///data/apu.db"
_PREFIJO_ARCHIVO_SQLITE = "sqlite:///"
_MEMORIA = ":memory:"

#: SL-E12: espera de SQLite ante una base ocupada, en milisegundos. SUPUESTO_DECLARADO (S3 §4.4).
ESPERA_OCUPADA_MS = 5000
#: Opción de ejecución que pide `BEGIN IMMEDIATE`: la lleva `abrir_sesion_de_escritura`.
OPCION_INMEDIATA = "silice_inmediata"


def crear_motor(url: str = URL_POR_DEFECTO) -> Engine:
    """Devuelve el motor de la URL indicada, creando el directorio del archivo si hace falta.

    Activa `PRAGMA foreign_keys` en SQLite: sin él, el motor ignora las claves foráneas y el
    esquema dejaría de ser el que documenta docs/modelo_datos.md. Desde SL-E12 (varios usuarios a
    la vez, S3 §6.3) activa además el diario WAL y `busy_timeout`, y toma el control del `BEGIN`
    (receta de SQLAlchemy para pysqlite): las transacciones que crean versión empiezan con
    `BEGIN IMMEDIATE` para tomar el bloqueo de escritura ANTES de leer el último eslabón.
    """
    _preparar_directorio(url)
    motor = create_engine(url)
    if motor.dialect.name == "sqlite":
        event.listen(motor, "connect", _activar_claves_foraneas)
        event.listen(motor, "connect", _preparar_conexion)
        event.listen(motor, "begin", _comenzar)
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


def abrir_sesion_de_escritura(motor: Engine) -> Session:
    """Una sesión cuya transacción empieza con `BEGIN IMMEDIATE` (SL-E12): la de todo camino que
    crea una versión. Quien guarda toma el bloqueo de escritura antes de leer el último eslabón y
    el otro espera hasta `ESPERA_OCUPADA_MS`; en WAL los lectores no se bloquean."""
    return Session(motor.execution_options(**{OPCION_INMEDIATA: True}))


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


def _preparar_conexion(conexion, _registro) -> None:
    # `isolation_level = None`: pysqlite deja de emitir el BEGIN implícito y lo emite `_comenzar`.
    conexion.isolation_level = None
    cursor = conexion.cursor()
    cursor.execute(f"PRAGMA busy_timeout={ESPERA_OCUPADA_MS}")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def _comenzar(conexion) -> None:
    inmediata = conexion.get_execution_options().get(OPCION_INMEDIATA, False)
    conexion.exec_driver_sql("BEGIN IMMEDIATE" if inmediata else "BEGIN")
