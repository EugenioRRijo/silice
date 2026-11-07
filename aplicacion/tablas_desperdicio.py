"""La traza del desperdicio de los materiales de un APU (F5 vial, tarea 3).

Vive en la base del caso (revisión `caso_0022_apu_desperdicio`). El desperdicio va **dentro de la
cantidad** de la `LineaMaterial` (diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-
design.md` §4, opción B; decisión provisional 1 del 2026-11-06): el núcleo no cambia. Aquí queda lo
que el núcleo no guarda, la cantidad neta y el porcentaje, para mostrar «0,52 (0,50 + 4 %)» y
precargar Componer con lo que se tecleó. `MetaData` propia, sin clave foránea a `core.models` (como
`aplicacion/tablas_vial.py`); las cifras con `DecimalExacto` (texto, nunca `float`).

- `apu_desperdicio_guardado`: un guardado de la composición de una partida (por su código), con su
  hora. **Solo inserción**: guardar otra vez es otra fila y al leer manda el último; un guardado sin
  desperdicio deja su fila sin líneas, y así la traza anterior deja de valer.
- `apu_desperdicio`: las líneas con desperdicio de ese guardado, en orden.

Una base que todavía no tiene las tablas se lee como sin trazas y las tablas se crean al guardar la
primera. La escribe y la lee solo `aplicacion/desperdicio.py`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Connection, DateTime, Engine, Index, Integer, MetaData, String, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core.models.tipos import DecimalExacto

__all__ = [
    "METADATA_DESPERDICIO",
    "GuardadoDeDesperdicio",
    "LineaConDesperdicio",
    "crear_esquema_desperdicio",
    "hay_tablas_de_desperdicio",
]

METADATA_DESPERDICIO = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_DESPERDICIO


class GuardadoDeDesperdicio(Base):
    """Un guardado de la composición de una partida, con o sin líneas con desperdicio."""

    __tablename__ = "apu_desperdicio_guardado"
    __table_args__ = (Index("ix_apu_desperdicio_guardado_partida", "partida_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_codigo: Mapped[str] = mapped_column(String(64), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class LineaConDesperdicio(Base):
    """Un material con desperdicio de un guardado."""

    __tablename__ = "apu_desperdicio"
    __table_args__ = (Index("ix_apu_desperdicio_guardado", "guardado_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guardado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(300), nullable=False)
    unidad: Mapped[str] = mapped_column(String(40), nullable=False)
    cantidad_neta: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    desperdicio_pct: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)


def crear_esquema_desperdicio(destino: Engine | Connection) -> None:
    """Crea las dos tablas si aún no existen (pruebas y el primer guardado en una base sin migrar;
    las de disco migran)."""
    METADATA_DESPERDICIO.create_all(destino)


def hay_tablas_de_desperdicio(sesion: Session) -> bool:
    """True si la base de la sesión ya tiene las dos tablas."""
    inspector = inspect(sesion.connection())
    return all(
        inspector.has_table(t.__tablename__) for t in (GuardadoDeDesperdicio, LineaConDesperdicio)
    )
