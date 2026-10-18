"""Tablas de la arenera: materiales, movimientos y bandeja de pesajes sospechosos.

Las cantidades son `Decimal` en Python y texto en la base (`String(40)`), igual que
`core.models.tipos.DecimalExacto`, que aqui NO se importa: `produccion/` solo conoce
`core.contracts`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Dialect,
    ForeignKey,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

LONGITUD_DECIMAL = 40


class Cantidad(TypeDecorator[Decimal]):
    """`Decimal` persistido como texto exacto; `TypeError` si llega otra cosa (nunca `float`)."""

    impl = String(LONGITUD_DECIMAL)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if not isinstance(value, Decimal):
            raise TypeError(f"se esperaba Decimal, no {type(value).__name__}: {value!r}")
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))


METADATA_PRODUCCION = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_PRODUCCION


class Material(Base):
    __tablename__ = "prod_material"
    __table_args__ = (
        CheckConstraint("unidad_venta IN ('m3', 't')", name="ck_prod_material_unidad"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    unidad_venta: Mapped[str] = mapped_column(String(2))
    densidad_t_m3: Mapped[Decimal | None] = mapped_column(Cantidad, nullable=True)
    existencia_minima: Mapped[Decimal] = mapped_column(Cantidad)
    activo: Mapped[bool] = mapped_column(default=True)


class Movimiento(Base):
    __tablename__ = "prod_movimiento"
    __table_args__ = (
        UniqueConstraint("ticket", name="uq_prod_movimiento_ticket"),
        CheckConstraint(
            "tipo IN ('entrada', 'despacho', 'ajuste')", name="ck_prod_movimiento_tipo"
        ),
        CheckConstraint("origen IN ('manual', 'bascula')", name="ck_prod_movimiento_origen"),
        CheckConstraint("length(cantidad) > 0", name="ck_prod_movimiento_cantidad"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("prod_material.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(String(10))
    cantidad: Mapped[Decimal] = mapped_column(Cantidad)
    ticket: Mapped[str | None] = mapped_column(String(60), nullable=True)
    placa: Mapped[str] = mapped_column(String(20), default="")
    cliente: Mapped[str] = mapped_column(String(120), default="")
    nota: Mapped[str] = mapped_column(String(300), default="")
    origen: Mapped[str] = mapped_column(String(10), default="manual")
    usuario: Mapped[str] = mapped_column(String(120))
    registrado: Mapped[datetime] = mapped_column(DateTime)


class PesajeSospechoso(Base):
    __tablename__ = "prod_pesaje_sospechoso"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('pendiente', 'resuelto', 'descartado')",
            name="ck_prod_pesaje_sospechoso_estado",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    huella_archivo: Mapped[str] = mapped_column(String(64), index=True)
    fila: Mapped[int] = mapped_column(Integer)
    ticket: Mapped[str] = mapped_column(String(60), default="")
    fecha_texto: Mapped[str] = mapped_column(String(60), default="")
    placa: Mapped[str] = mapped_column(String(20), default="")
    material_texto: Mapped[str] = mapped_column(String(120), default="")
    bruto_texto: Mapped[str] = mapped_column(String(60), default="")
    tara_texto: Mapped[str] = mapped_column(String(60), default="")
    neto_texto: Mapped[str] = mapped_column(String(60), default="")
    motivo: Mapped[str] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(10), default="pendiente")
    resuelto_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resuelto_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
