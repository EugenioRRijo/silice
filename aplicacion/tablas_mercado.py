"""Las tablas del estudio de mercado (MP-5, Tarea 13; diseño de montar un presupuesto §5.1).

Viven en la base del caso (revisión `caso_0013_mp_mercado`) porque son **datos de la empresa**: los
precios que vio en el mercado se quedan en su carpeta de trabajo, en ese equipo. `MetaData` propia,
sin clave foránea a `core.models` (como `paquete/modelo.py`); los montos con `DecimalExacto` (texto,
nunca `float`). Las escribe y las lee solo `aplicacion/mercado.py`.

- `mp_observacion`: un precio visto (de un insumo que se compra o de una partida que se cobra), con
  su fuente, fecha, moneda, quién lo anotó y cuándo. `anulada_por` es nulo mientras vale.
- `mp_precio_objetivo`: el precio de venta objetivo de una partida, con las observaciones de las
  que sale (ids en JSON); vale el último por partida (se escribe solo por inserción).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Engine, Index, Integer, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.models.tipos import DecimalExacto

__all__ = [
    "METADATA_MERCADO",
    "ObservacionDeMercado",
    "PrecioObjetivo",
    "crear_esquema_mercado",
]

METADATA_MERCADO = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_MERCADO


class ObservacionDeMercado(Base):
    """Un precio visto en el mercado para un insumo (`compra`) o una partida (`cobro`)."""

    __tablename__ = "mp_observacion"
    __table_args__ = (Index("ix_mp_observacion_lado_codigo", "lado", "codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lado: Mapped[str] = mapped_column(String(10), nullable=False)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    fuente_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    fuente: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    moneda: Mapped[str] = mapped_column(String(10), nullable=False)
    precio: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    nota: Mapped[str] = mapped_column(String(500), nullable=False)
    responsable: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    anulada_por: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)


class PrecioObjetivo(Base):
    """El precio de venta objetivo de una partida; vale el último (mayor `id`) por partida."""

    __tablename__ = "mp_precio_objetivo"
    __table_args__ = (Index("ix_mp_precio_objetivo_codigo_partida", "codigo_partida"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_partida: Mapped[str] = mapped_column(String(40), nullable=False)
    precio: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    moneda: Mapped[str] = mapped_column(String(10), nullable=False)
    observaciones: Mapped[str] = mapped_column(String(400), nullable=False)
    responsable: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)


def crear_esquema_mercado(motor: Engine) -> None:
    """Crea las tablas si aún no existen (pruebas y bases en memoria; las de disco migran)."""
    METADATA_MERCADO.create_all(motor)
