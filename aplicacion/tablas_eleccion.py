"""La tabla de la elección y las preferencias de cada cuenta (MOD-0, diseño de módulos §12.1).

Vive en `instalacion.db` (revisión `ins_0004_mod_eleccion`): una fila por cuenta con la carpeta de
trabajo (`caso`, el nombre del archivo; `NULL` = la carpeta de la instalación), la obra (`proyecto`,
el código que da `GET /v1/proyectos`), el último módulo abierto y si el sidebar de módulos queda
fijado. `MetaData` propia, sin clave foránea a `core.models` ni a las cuentas: la fila de una cuenta
dada de baja no estorba a nadie.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, MetaData, String, false
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

METADATA_ELECCION = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_ELECCION


class EleccionDeCuenta(Base):
    __tablename__ = "mp_eleccion"

    usuario_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    caso: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proyecto: Mapped[str | None] = mapped_column(String(120), nullable=True)
    modulo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sidebar_fijado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
