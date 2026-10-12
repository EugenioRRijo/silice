"""Tablas aditivas de Sílice S1 (spec S1 §5.2). Módulo propio para no tocar `entidades.py` (M §3.2);
cada fase de núcleo agrega aquí las suyas con su revisión en `migraciones/caso/`. Ninguna altera
una tabla existente (ruling SF3-E0)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base
from core.models.tipos import DecimalExacto


class SerieIndice(Base):
    """SL-E1: una serie (tasa compra/venta, INPC, insumos de la construcción)."""

    __tablename__ = "serie_indice"
    __table_args__ = (UniqueConstraint("codigo", name="uq_serie_indice_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str] = mapped_column(String(200))
    organismo: Mapped[str] = mapped_column(String(120))
    unidad: Mapped[str] = mapped_column(String(40))
    periodicidad: Mapped[str] = mapped_column(String(12))
    base: Mapped[str] = mapped_column(String(200), default="")


class ImportacionIndice(Base):
    """SL-E1: un archivo importado para una serie, con su huella SHA-256 y su fuente."""

    __tablename__ = "importacion_indice"
    __table_args__ = (Index("ix_importacion_indice_serie_huella", "serie_id", "huella"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey("serie_indice.id"))
    archivo: Mapped[str] = mapped_column(String(255))
    huella: Mapped[str] = mapped_column(String(64))
    fuente: Mapped[str] = mapped_column(String(500))
    fecha_descarga: Mapped[date] = mapped_column(Date)
    fecha_importacion: Mapped[datetime] = mapped_column(DateTime)
    responsable: Mapped[str] = mapped_column(String(120))
    filas_leidas: Mapped[int] = mapped_column(Integer)
    filas_rechazadas: Mapped[int] = mapped_column(Integer)
    informe: Mapped[str] = mapped_column(Text, default="")


class ValorIndice(Base):
    """SL-E1: valor de una serie en una fecha (fecha valor o primer día del período)."""

    __tablename__ = "valor_indice"
    __table_args__ = (
        UniqueConstraint("serie_id", "fecha", "importacion_id", name="uq_valor_indice"),
        Index("ix_valor_indice_serie_fecha", "serie_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey("serie_indice.id"))
    importacion_id: Mapped[int] = mapped_column(
        ForeignKey("importacion_indice.id", ondelete="CASCADE")
    )
    fecha: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(DecimalExacto)
    provisional: Mapped[bool] = mapped_column(Boolean, default=False)


class MonedaProyecto(Base):
    """SL-E1: historial de la moneda de un proyecto; la vigente es la última."""

    __tablename__ = "moneda_proyecto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    moneda: Mapped[str] = mapped_column(String(10))
    desde: Mapped[datetime] = mapped_column(DateTime)
    version_id: Mapped[int | None] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="SET NULL"), default=None
    )
    responsable: Mapped[str] = mapped_column(String(120))
    fuente: Mapped[str] = mapped_column(String(300))


class PrecioOrigen(Base):
    """SL-E1: origen de un precio (S1 §5.1). Sin fila, manda la lista (precedencia única)."""

    __tablename__ = "precio_origen"

    precio_id: Mapped[int] = mapped_column(
        ForeignKey("precio_insumo.id", ondelete="CASCADE"), primary_key=True
    )
    moneda_original: Mapped[str] = mapped_column(String(10))
    precio_original: Mapped[Decimal] = mapped_column(DecimalExacto)
    fecha_precio: Mapped[date] = mapped_column(Date)
    tasa: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    fecha_tasa: Mapped[date | None] = mapped_column(Date, default=None)
    fuente_tasa: Mapped[str] = mapped_column(String(300), default="")
    fuente: Mapped[str] = mapped_column(String(300), default="")
