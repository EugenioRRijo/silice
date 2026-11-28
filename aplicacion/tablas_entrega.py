"""La fecha de entrega al cliente de cada obra (Lote G5; especificación
`docs/especificaciones/2026-11-26-notificaciones-por-evento.md` §4 y decisión de Eugenio del
2026-11-26).

Vive en la base del caso (revisión `caso_0025_entrega_de_obra`): `core/` no cambia y la fecha de
entrega de una obra se guarda en su carpeta de trabajo. `MetaData` propia, sin clave foránea a
`core.models` (como `aplicacion/tablas_procura.py` y `aplicacion/tablas_obra.py`).

- `entrega_de_obra`: una fila por obra (`proyecto_codigo`, el código de la obra como texto) con su
  `fecha_entrega` opcional (`date`, nula si se quitó), cuándo se actualizó (`actualizada`) y quién
  lo hizo (`actualizada_por`). La escribe y la lee solo `aplicacion/entrega_de_obra.py`.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Connection, Date, DateTime, Engine, MetaData, String, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

__all__ = [
    "LARGO_CODIGO",
    "LARGO_RESPONSABLE",
    "METADATA_ENTREGA",
    "EntregaDeObra",
    "crear_esquema_entrega",
    "hay_tabla_entrega",
]

METADATA_ENTREGA = MetaData()
LARGO_CODIGO = 40
LARGO_RESPONSABLE = 200


class Base(DeclarativeBase):
    metadata = METADATA_ENTREGA


class EntregaDeObra(Base):
    """La fecha de entrega al cliente fijada para una obra de la carpeta."""

    __tablename__ = "entrega_de_obra"

    proyecto_codigo: Mapped[str] = mapped_column(String(LARGO_CODIGO), primary_key=True)
    fecha_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    actualizada: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actualizada_por: Mapped[str] = mapped_column(String(LARGO_RESPONSABLE), nullable=False)


def crear_esquema_entrega(destino: Engine | Connection) -> None:
    """Crea `entrega_de_obra` si aún no existe (pruebas y el primer guardado en una base sin
    migrar; las de disco migran)."""
    METADATA_ENTREGA.create_all(destino)


def hay_tabla_entrega(sesion: Session) -> bool:
    """True si la base de la sesión ya tiene `entrega_de_obra`."""
    return inspect(sesion.connection()).has_table(EntregaDeObra.__tablename__)
