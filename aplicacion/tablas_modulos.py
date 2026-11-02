"""Qué módulos activables tiene encendidos la instalación (plan vial, Tarea 19).

Vive en `instalacion.db` (revisión `ins_0010_modulo`): una fila por cambio, nunca se sobrescribe
ni se borra. Vale la última fila de cada `clave`; una clave sin filas está activa (por defecto
todo está encendido). `MetaData` propia, sin clave foránea. `usuario` es el login de quien cambió.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["METADATA_MODULOS", "FilaModulo"]

METADATA_MODULOS = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_MODULOS


class FilaModulo(Base):
    """Un cambio de estado de un módulo: quién, cuándo y a qué."""

    __tablename__ = "modulo_cambio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(40), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    usuario: Mapped[str] = mapped_column(String(200), nullable=False)
    registrado: Mapped[datetime] = mapped_column(DateTime, nullable=False)
