"""El mapa de series que «Riesgo de la obra» recuerda por versión (mejora de la DS-81).

Vive en la base del caso (revisión `caso_0023_riesgo_mapa`): qué serie mueve cada insumo es una
elección sobre la obra y se queda en su carpeta de trabajo. `MetaData` propia, sin clave foránea a
`core.models` (como `aplicacion/tablas_vial.py`).

- `riesgo_mapa_guardado`: un guardado del mapa de una versión (`version_id` es el `id` del
  presupuesto), con quién y cuándo. **Solo inserción**: guardar otro mapa es otra fila; al leer
  manda el último. Un guardado sin filas es un mapa vacío (la persona no eligió ninguna serie).
- `riesgo_mapa_serie`: las parejas insumo y serie de ese guardado (`insumo` es la descripción del
  insumo en el APU o el código del componente de la receta, como en `MapaSeries`).

Una base que todavía no tiene las tablas se lee como sin mapa y las tablas se crean al guardar el
primero. La escribe y la lee solo `aplicacion/riesgo/mapa_guardado.py`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Connection, DateTime, Engine, Index, Integer, MetaData, String, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

__all__ = [
    "LARGO_INSUMO",
    "LARGO_SERIE",
    "LARGO_USUARIO",
    "METADATA_RIESGO",
    "GuardadoDeMapa",
    "SerieDeInsumo",
    "crear_esquema_riesgo",
    "hay_tablas_de_riesgo",
]

METADATA_RIESGO = MetaData()
LARGO_USUARIO = 200
LARGO_INSUMO = 500
LARGO_SERIE = 40


class Base(DeclarativeBase):
    metadata = METADATA_RIESGO


class GuardadoDeMapa(Base):
    """Un guardado del mapa de series de una versión."""

    __tablename__ = "riesgo_mapa_guardado"
    __table_args__ = (Index("ix_riesgo_mapa_guardado_version", "version_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False)
    usuario: Mapped[str] = mapped_column(String(LARGO_USUARIO), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SerieDeInsumo(Base):
    """La serie que mueve un insumo en un guardado."""

    __tablename__ = "riesgo_mapa_serie"
    __table_args__ = (Index("ix_riesgo_mapa_serie_guardado", "guardado_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guardado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    insumo: Mapped[str] = mapped_column(String(LARGO_INSUMO), nullable=False)
    serie: Mapped[str] = mapped_column(String(LARGO_SERIE), nullable=False)


def crear_esquema_riesgo(destino: Engine | Connection) -> None:
    """Crea las dos tablas si aún no existen (pruebas y el primer guardado en una base sin migrar;
    las de disco migran)."""
    METADATA_RIESGO.create_all(destino)


def hay_tablas_de_riesgo(sesion: Session) -> bool:
    """True si la base de la sesión ya tiene las dos tablas."""
    inspector = inspect(sesion.connection())
    return all(inspector.has_table(t.__tablename__) for t in (GuardadoDeMapa, SerieDeInsumo))
