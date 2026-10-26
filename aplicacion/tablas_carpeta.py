"""La moneda de la carpeta de trabajo (MP-1, Tarea 1; D-MP1: una moneda por carpeta).

Vive en la base del caso (revisión `caso_0010_mp_carpeta`): una sola fila (`id = 1`) con la moneda
declarada, quién la declaró y cuándo. `MetaData` propia, sin clave foránea a `core.models` (como
`paquete/modelo.py`); la escribe y la lee solo `aplicacion/listas_para_armar.py`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Engine, Integer, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["METADATA_CARPETA", "CarpetaDeTrabajo", "crear_esquema_carpeta"]

METADATA_CARPETA = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_CARPETA


class CarpetaDeTrabajo(Base):
    """La moneda en que trabaja la carpeta: sus listas para armar, precios y APU están en ella."""

    __tablename__ = "mp_carpeta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    moneda: Mapped[str] = mapped_column(String(10), nullable=False)
    declarada_por: Mapped[str] = mapped_column(String(200), nullable=False)
    declarada_el: Mapped[datetime] = mapped_column(DateTime, nullable=False)


def crear_esquema_carpeta(motor: Engine) -> None:
    """Crea `mp_carpeta` si aún no existe (pruebas y bases en memoria; las de disco migran)."""
    METADATA_CARPETA.create_all(motor)
