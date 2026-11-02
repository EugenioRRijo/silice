"""Los precios del corte declarados por material (MP-7, Tarea 25; diseño de montar un presupuesto
§11, meta 4).

Vive en la base del caso (revisiones `caso_0017_mp_corte` y `caso_0018_mp_corte_tasa`): el precio
de una obra es dato de la empresa y se queda en su carpeta de trabajo. `MetaData` propia, sin
clave foránea a `core.models` (como `paquete/modelo.py`); el precio con `DecimalExacto` (texto,
nunca `float`).

- `mp_precio_corte`: el precio que la persona declaró para un material de una obra a una fecha
  (desde el estudio de mercado o al recibir una compra), en la moneda de la obra, con su fuente,
  quién y cuándo. **Solo inserción**: un precio nuevo es otra fila; al leer manda el último hasta
  el corte. `precio` y `moneda` son lo que el control usa. Si la persona lo declaró en otra moneda
  que la obra, se convirtió con la tasa del BCV de su fecha (Tarea D2) y la fila guarda además el
  rastro: `moneda_original`, `precio_original`, `tasa` (Bs por USD), `fecha_tasa` y `fuente_tasa`
  (nulos si no hubo conversión).

El material se nombra por su descripción y su unidad, las de la composición congelada de la línea
base (`linea_composicion_version`). Una base que todavía no tiene la tabla (creada con
`crear_esquema`, sin migrar) se lee como sin precios declarados y la tabla se crea al declarar el
primero, como las causas de retraso (`aplicacion/tablas_causas.py`). La escribe y la lee solo
`aplicacion/precios_declarados.py`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Connection, Date, DateTime, Engine, Index, Integer, MetaData, String, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core.models.tipos import DecimalExacto

__all__ = [
    "METADATA_CORTE",
    "PrecioDelCorte",
    "crear_esquema_corte",
    "hay_tabla_corte",
]

METADATA_CORTE = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_CORTE


class PrecioDelCorte(Base):
    """El precio declarado de un material de una obra desde `fecha`."""

    __tablename__ = "mp_precio_corte"
    __table_args__ = (
        Index("ix_mp_precio_corte_insumo", "proyecto_id", "descripcion_insumo", "unidad"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion_insumo: Mapped[str] = mapped_column(String(300), nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), nullable=False)
    precio: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    moneda: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    fuente: Mapped[str] = mapped_column(String(300), nullable=False)
    responsable: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    moneda_original: Mapped[str | None] = mapped_column(String(10), nullable=True)
    precio_original: Mapped[Decimal | None] = mapped_column(DecimalExacto, nullable=True)
    tasa: Mapped[Decimal | None] = mapped_column(DecimalExacto, nullable=True)
    fecha_tasa: Mapped[date | None] = mapped_column(Date, nullable=True)
    fuente_tasa: Mapped[str | None] = mapped_column(String(300), nullable=True)


def crear_esquema_corte(destino: Engine | Connection) -> None:
    """Crea `mp_precio_corte` si aún no existe (pruebas, bases en memoria y la declaración en una
    base sin migrar; las de disco migran)."""
    METADATA_CORTE.create_all(destino)


def hay_tabla_corte(sesion: Session) -> bool:
    """True si la base de la sesión ya tiene `mp_precio_corte`."""
    return inspect(sesion.connection()).has_table(PrecioDelCorte.__tablename__)
