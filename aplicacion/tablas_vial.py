"""Los tramos viales de cada versión (plan vial, Tarea 8).

Vive en la base del caso (revisión `caso_0019_vial_tramos`): los tramos de una obra son dato de la
empresa y se quedan en su carpeta de trabajo. `MetaData` propia, sin clave foránea a `core.models`
(como `aplicacion/tablas_corte.py`); las cifras con `DecimalExacto` (texto, nunca `float`).

- `vial_tramos_guardado`: un guardado de los tramos de una versión (`version_id` es el `id` del
  presupuesto), con quién, cuándo y de dónde salió (`fuente`: «Importado de via.csv» o lo que
  escribió quien guardó). **Solo inserción**: guardar otra vez es otra fila; al leer manda el
  último. Nada se sobrescribe y el rastro de lo anterior queda.
- `vial_tramo`: los tramos de ese guardado, en orden. Las capas y la demarcación van como texto
  JSON con las cifras en texto (una lista corta por tramo que nunca se consulta por dentro).

Una base que todavía no tiene las tablas (creada con `crear_esquema`, sin migrar) se lee como sin
tramos y las tablas se crean al guardar los primeros. La escribe y la lee solo `aplicacion/vial.py`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Connection,
    DateTime,
    Engine,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    inspect,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core.models.tipos import DecimalExacto

__all__ = [
    "METADATA_VIAL",
    "GuardadoDeTramos",
    "TramoGuardado",
    "crear_esquema_vial",
    "hay_tablas_viales",
]

METADATA_VIAL = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_VIAL


class GuardadoDeTramos(Base):
    """Un guardado de los tramos de una versión."""

    __tablename__ = "vial_tramos_guardado"
    __table_args__ = (Index("ix_vial_tramos_guardado_version", "version_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False)
    usuario: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fuente: Mapped[str] = mapped_column(String(300), nullable=False)


class TramoGuardado(Base):
    """Un tramo de un guardado."""

    __tablename__ = "vial_tramo"
    __table_args__ = (Index("ix_vial_tramo_guardado", "guardado_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guardado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    tramo_id: Mapped[str] = mapped_column(String(80), nullable=False)
    progresiva_ini_km: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    progresiva_fin_km: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    ancho_m: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    distancia_planta_km: Mapped[Decimal | None] = mapped_column(DecimalExacto, nullable=True)
    capas: Mapped[str] = mapped_column(Text, nullable=False)
    demarcacion: Mapped[str] = mapped_column(Text, nullable=False)


def crear_esquema_vial(destino: Engine | Connection) -> None:
    """Crea las dos tablas si aún no existen (pruebas, bases en memoria y el primer guardado en una
    base sin migrar; las de disco migran)."""
    METADATA_VIAL.create_all(destino)


def hay_tablas_viales(sesion: Session) -> bool:
    """True si la base de la sesión ya tiene las dos tablas."""
    inspector = inspect(sesion.connection())
    return all(inspector.has_table(t.__tablename__) for t in (GuardadoDeTramos, TramoGuardado))
