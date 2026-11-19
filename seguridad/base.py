"""Motor de la base de la instalación: SQLite en WAL, con espera y claves foráneas.

`seguridad` no puede importar `core` (arquitectura), así que repite aquí lo mínimo de
`core.catalog.sesion.crear_motor`. La base se crea y se migra con
`operacion.base_datos.preparar_base(ruta, Destino.INSTALACION)` antes de abrirla.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

ESPERA_OCUPADA_MS = 5000  # SUPUESTO_DECLARADO: igual que SL-E12
#: Opción de ejecución que pide `BEGIN IMMEDIATE`: la lleva `abrir_sesion_de_escritura`.
OPCION_INMEDIATA = "silice_inmediata"


def crear_motor(ruta: Path | str) -> Engine:
    motor = create_engine(f"sqlite:///{Path(ruta).as_posix()}")

    @event.listens_for(motor, "connect")
    def _preparar(conexion, _registro) -> None:
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={ESPERA_OCUPADA_MS}")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    @event.listens_for(motor, "begin")
    def _comenzar(conexion) -> None:
        # Solo la sesión de escritura emite el BEGIN: las demás siguen con el lazy de pysqlite (un
        # SELECT no abre transacción). Con `BEGIN IMMEDIATE` ya emitido, pysqlite no abre otro.
        if conexion.get_execution_options().get(OPCION_INMEDIATA, False):
            conexion.exec_driver_sql("BEGIN IMMEDIATE")

    return motor


def abrir_sesion(motor: Engine) -> Session:
    return Session(motor, expire_on_commit=False)


def abrir_sesion_de_escritura(motor: Engine) -> Session:
    """Una sesión cuya transacción empieza con `BEGIN IMMEDIATE`: toma el bloqueo de escritura
    ANTES de leer lo que va a comprobar (un conteo, un contador) y la otra escritura espera hasta
    `ESPERA_OCUPADA_MS` y ve lo que ésta confirme. Los lectores (`abrir_sesion`) no esperan (WAL).
    """
    return Session(motor.execution_options(**{OPCION_INMEDIATA: True}), expire_on_commit=False)
