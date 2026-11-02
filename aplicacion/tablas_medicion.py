"""Las notas de medición de los renglones de la Hoja (MP-3, Tarea 9; diseño §5.3 y §10).

Vive en la base del caso (revisión `caso_0012_mp_medicion`): la nota que la persona escribió al
agregar una partida a mano («6 m × 35 m de muro»), por obra, versión y clave del renglón. Es texto
libre que no entra en el cálculo (la medición reproducible es el cálculo, que va como regla del
renglón). `MetaData` propia, sin clave foránea a `core.models` (`proyecto_id` es el `id` de la obra,
sin restricción, como `paquete/modelo.py`).

La escriben y la leen `guardar_notas` y `notas_de_version`, que usan `aplicacion/hoja.py` al guardar
y al abrir una versión. Una base que todavía no tiene la tabla (creada con `crear_esquema`, sin
migrar) se lee como sin notas y la tabla se crea al guardar la primera nota, como el espacio
(`crear_esquema_espacio`). Las filas solo se insertan: cada versión guarda las suyas.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import (
    Connection,
    Engine,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
    inspect,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

__all__ = [
    "METADATA_MEDICION",
    "NotaDeMedicion",
    "crear_esquema_medicion",
    "guardar_notas",
    "notas_de_version",
]

METADATA_MEDICION = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_MEDICION


class NotaDeMedicion(Base):
    """La nota de medición de un renglón de una versión de una obra."""

    __tablename__ = "mp_nota_medicion"
    __table_args__ = (
        UniqueConstraint("proyecto_id", "version", "clave", name="uq_mp_nota_medicion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    clave: Mapped[str] = mapped_column(String(200), nullable=False)
    nota: Mapped[str] = mapped_column(String(500), nullable=False)


def crear_esquema_medicion(destino: Engine | Connection) -> None:
    """Crea `mp_nota_medicion` si aún no existe (pruebas, bases en memoria y el guardado de una
    base sin migrar; las de disco migran)."""
    METADATA_MEDICION.create_all(destino)


def _hay_tabla(sesion: Session) -> bool:
    return inspect(sesion.connection()).has_table(NotaDeMedicion.__tablename__)


def guardar_notas(
    sesion: Session, proyecto_id: int, version: str, notas: Mapping[str, str]
) -> None:
    """Inserta las notas de la versión `version` de la obra `proyecto_id` (clave → nota). Sin
    notas no toca la base; si la tabla falta, la crea en la misma transacción. No confirma."""
    if not notas:
        return
    if not _hay_tabla(sesion):
        crear_esquema_medicion(sesion.connection())
    sesion.add_all(
        NotaDeMedicion(proyecto_id=proyecto_id, version=version, clave=clave, nota=nota)
        for clave, nota in notas.items()
    )
    sesion.flush()


def notas_de_version(sesion: Session, proyecto_id: int, version: str) -> dict[str, str]:
    """Las notas de la versión `version` de la obra `proyecto_id` (clave → nota); sin la tabla,
    ninguna (no la crea ni escribe)."""
    if not _hay_tabla(sesion):
        return {}
    filas = sesion.execute(
        select(NotaDeMedicion.clave, NotaDeMedicion.nota)
        .where(NotaDeMedicion.proyecto_id == proyecto_id, NotaDeMedicion.version == version)
        .order_by(NotaDeMedicion.id)
    )
    return {clave: nota for clave, nota in filas}
