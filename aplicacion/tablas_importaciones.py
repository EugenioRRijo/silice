"""El registro de importaciones de la obra (rediseño del front, F4, Tarea 10).

Vive en la base del caso (revisión `caso_0020_hoja_importaciones`): qué archivo se importó a una
obra (nombre, fecha y hora, quién y qué produjo) es dato de la empresa y se queda en su carpeta de
trabajo. **Del archivo no se guarda copia**: solo su nombre, nunca una ruta. `MetaData` propia, sin
clave foránea a `core.models` (como `aplicacion/tablas_vial.py`).

- `hoja_importaciones`: una fila por importación que llegó a una versión guardada (`version_id` es
  el `id` del presupuesto que la guardó). **Solo inserción**: nada se sobrescribe ni se borra. Lo
  importado que sigue en un borrador sin guardar no está aquí: vive con su borrador, en memoria.

Una base que todavía no tiene la tabla (creada con `crear_esquema`, sin migrar) se lee como sin
registro y la tabla se crea al guardar la primera versión con importaciones. La escribe y la lee
solo `aplicacion/importaciones.py`.
"""

from __future__ import annotations

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
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

__all__ = [
    "METADATA_IMPORTACIONES",
    "ImportacionGuardada",
    "crear_esquema_importaciones",
    "hay_tabla_de_importaciones",
]

METADATA_IMPORTACIONES = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_IMPORTACIONES


class ImportacionGuardada(Base):
    """Una importación (plano o cómputo) que llegó a una versión guardada."""

    __tablename__ = "hoja_importaciones"
    __table_args__ = (Index("ix_hoja_importaciones_version", "version_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usuario: Mapped[str] = mapped_column(String(200), nullable=False)
    resumen: Mapped[str] = mapped_column(String(300), nullable=False)


def crear_esquema_importaciones(destino: Engine | Connection) -> None:
    """Crea la tabla si aún no existe (pruebas, bases en memoria y el primer guardado en una base
    sin migrar; las de disco migran)."""
    METADATA_IMPORTACIONES.create_all(destino)


def hay_tabla_de_importaciones(sesion: Session) -> bool:
    """True si la base de la sesión ya tiene la tabla."""
    return inspect(sesion.connection()).has_table(ImportacionGuardada.__tablename__)
