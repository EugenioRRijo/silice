"""Las tablas de la procura con fechas (MP-7, Tarea 23; diseño de montar un presupuesto §11,
meta 3).

Viven en la base del caso (revisión `caso_0016_mp_procura`): las compras de una obra son datos de la
empresa y se quedan en su carpeta de trabajo. `MetaData` propia, sin clave foránea a `core.models`
(como `paquete/modelo.py`); cantidades y precios con `DecimalExacto` (texto, nunca `float`). Las
escribe y las lee solo `aplicacion/procura.py`.

- `mp_plazo_entrega`: el plazo de entrega (días hábiles) de un material en una obra; una fila por
  (obra, descripción, unidad), que se reemplaza al cambiarlo. Sin fila rige el plazo por omisión.
- `mp_compra`: un pedido o una recepción de un material de una obra, con su fecha y, si se
  declararon, la cantidad y el precio (en la moneda de la carpeta); quién y cuándo. Solo inserción.

El material se nombra por su descripción y su unidad, las de la composición congelada de la versión
(`linea_composicion_version`), que es donde la explosión los agrupa.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Engine, Index, Integer, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.models.tipos import DecimalExacto

__all__ = [
    "METADATA_PROCURA",
    "CompraDeInsumo",
    "PlazoDeEntrega",
    "crear_esquema_procura",
]

METADATA_PROCURA = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_PROCURA


class PlazoDeEntrega(Base):
    """Los días hábiles que tarda en llegar un material de una obra desde que se pide."""

    __tablename__ = "mp_plazo_entrega"

    proyecto_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    descripcion_insumo: Mapped[str] = mapped_column(String(300), primary_key=True)
    unidad: Mapped[str] = mapped_column(String(20), primary_key=True)
    dias: Mapped[int] = mapped_column(Integer, nullable=False)


class CompraDeInsumo(Base):
    """Un pedido (`pedida`) o una recepción (`recibida`) de un material de una obra."""

    __tablename__ = "mp_compra"
    __table_args__ = (Index("ix_mp_compra_insumo", "proyecto_id", "descripcion_insumo", "unidad"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion_insumo: Mapped[str] = mapped_column(String(300), nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), nullable=False)
    evento: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    cantidad: Mapped[Decimal | None] = mapped_column(DecimalExacto, nullable=True, default=None)
    precio: Mapped[Decimal | None] = mapped_column(DecimalExacto, nullable=True, default=None)
    moneda: Mapped[str | None] = mapped_column(String(10), nullable=True, default=None)
    responsable: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)


def crear_esquema_procura(motor: Engine) -> None:
    """Crea las tablas si aún no existen (pruebas y bases en memoria; las de disco migran)."""
    METADATA_PROCURA.create_all(motor)
