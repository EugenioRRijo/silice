"""Las causas de retraso por partida de cada valuación (MP-7, Tarea 22; diseño §11, meta 2).

Vive en la base del caso (revisión `caso_0015_mp_causas`): una fila por línea de valuación a la que
se le declaró una causa (`aplicacion.causas.CAUSAS`), con la valuación, la partida, la causa y el
momento del registro. **Solo inserción**: corregir una causa es registrar otra valuación (o anular
la que la trae; la de una valuación anulada deja de contar al leerla). `MetaData` propia, sin
clave foránea a `core.models` (`valuacion_id` es el `id` de `valuacion`, sin restricción, como
`paquete/modelo.py`).

Una base que todavía no tiene la tabla (creada con `crear_esquema`, sin migrar) se lee como sin
causas y la tabla se crea al guardar la primera, como las notas de medición
(`aplicacion/tablas_medicion.py`). La escriben y la leen solo `aplicacion/causas.py` y
`aplicacion/control.py`.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from datetime import datetime

from sqlalchemy import (
    Connection,
    DateTime,
    Engine,
    Index,
    Integer,
    MetaData,
    String,
    inspect,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

__all__ = [
    "METADATA_CAUSAS",
    "CausaDeRetraso",
    "causas_de_valuaciones",
    "crear_esquema_causas",
    "guardar_causas",
]

METADATA_CAUSAS = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_CAUSAS


class CausaDeRetraso(Base):
    """La causa declarada para una partida en una línea de una valuación."""

    __tablename__ = "mp_causa_retraso"
    __table_args__ = (Index("ix_mp_causa_retraso_valuacion", "valuacion_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    valuacion_id: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo_partida: Mapped[str] = mapped_column(String(40), nullable=False)
    causa: Mapped[str] = mapped_column(String(40), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)


def crear_esquema_causas(destino: Engine | Connection) -> None:
    """Crea `mp_causa_retraso` si aún no existe (pruebas, bases en memoria y el guardado de una
    base sin migrar; las de disco migran)."""
    METADATA_CAUSAS.create_all(destino)


def _hay_tabla(sesion: Session) -> bool:
    return inspect(sesion.connection()).has_table(CausaDeRetraso.__tablename__)


def guardar_causas(
    sesion: Session,
    valuacion_id: int,
    causas: Sequence[tuple[str, str]],
    fecha_hora: datetime,
) -> None:
    """Inserta las causas `(partida, causa)` de la valuación `valuacion_id`, en su orden. Sin
    causas no toca la base; si la tabla falta, la crea en la misma transacción. No confirma."""
    if not causas:
        return
    if not _hay_tabla(sesion):
        crear_esquema_causas(sesion.connection())
    sesion.add_all(
        CausaDeRetraso(
            valuacion_id=valuacion_id,
            codigo_partida=partida,
            causa=causa,
            fecha_hora=fecha_hora,
        )
        for partida, causa in causas
    )
    sesion.flush()


def causas_de_valuaciones(
    sesion: Session, valuaciones: Collection[int]
) -> list[tuple[int, str, str]]:
    """`(valuación, partida, causa)` de las valuaciones dadas, en el orden en que se registraron
    (por `id`); sin la tabla, ninguna (no la crea ni escribe)."""
    if not valuaciones or not _hay_tabla(sesion):
        return []
    filas = sesion.execute(
        select(CausaDeRetraso.valuacion_id, CausaDeRetraso.codigo_partida, CausaDeRetraso.causa)
        .where(CausaDeRetraso.valuacion_id.in_(list(valuaciones)))
        .order_by(CausaDeRetraso.id)
    )
    return [(valuacion, partida, causa) for valuacion, partida, causa in filas]
