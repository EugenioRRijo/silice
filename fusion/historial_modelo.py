"""La tabla del historial de auditorias de «Libro de la empresa» (UC-25; RF-142, RF-143).

Vive en `instalacion.db` (revision `ins_0003_auditoria_libro`): el historial es de la instalacion
entera, no de un caso. Guarda el resumen y los hallazgos compactos de cada auditoria; **nunca** el
libro ni el PDF (RNF-28): por eso no hay columna binaria, solo la huella SHA-256 del archivo. Los
totales son texto decimal exacto (`String(40)`), nunca `float`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Dialect,
    Integer,
    MetaData,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

LONGITUD_DECIMAL = 40


class Total(TypeDecorator[Decimal]):
    """`Decimal` persistido como texto exacto; `TypeError` si llega otra cosa (nunca `float`)."""

    impl = String(LONGITUD_DECIMAL)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if not isinstance(value, Decimal):
            raise TypeError(f"se esperaba Decimal, no {type(value).__name__}: {value!r}")
        return format(value, "f")

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))


METADATA_HISTORIAL = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_HISTORIAL


class AuditoriaLibro(Base):
    __tablename__ = "auditoria_libro"
    __table_args__ = (CheckConstraint("tipo IN ('libro', 'pdf')", name="ck_auditoria_libro_tipo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, index=True)
    usuario: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(5))
    nombre_archivo: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    fecha_libro: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_libro: Mapped[Decimal | None] = mapped_column(Total, nullable=True)
    total_silice: Mapped[Decimal | None] = mapped_column(Total, nullable=True)
    errores: Mapped[int] = mapped_column(Integer)
    advertencias: Mapped[int] = mapped_column(Integer)
    informativos: Mapped[int] = mapped_column(Integer)
    atipicos: Mapped[int] = mapped_column(Integer)
    recortado: Mapped[bool] = mapped_column(Boolean)
    hallazgos: Mapped[str] = mapped_column(Text)  # JSON: regla, hoja, celda, severidad, mensaje
