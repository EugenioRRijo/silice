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


def crear_motor(ruta: Path | str) -> Engine:
    motor = create_engine(f"sqlite:///{Path(ruta).as_posix()}")

    @event.listens_for(motor, "connect")
    def _preparar(conexion, _registro) -> None:
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={ESPERA_OCUPADA_MS}")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return motor


def abrir_sesion(motor: Engine) -> Session:
    return Session(motor, expire_on_commit=False)
