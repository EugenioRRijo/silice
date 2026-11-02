"""La ficha de la obra (MOD-3a): cliente y ubicación de cada obra de la carpeta de trabajo.

Vive en la base del caso (revisión `caso_0011_mod_ficha_obra`). `MetaData` propia, sin clave
foránea a `core.models` (`proyecto_id` es el `id` del proyecto, sin restricción); la escribe y la
lee solo `aplicacion/obras.py`.
"""

from __future__ import annotations

from sqlalchemy import Engine, Integer, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["METADATA_OBRA", "FichaDeObra", "crear_esquema_obra"]

METADATA_OBRA = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_OBRA


class FichaDeObra(Base):
    """El cliente y la ubicación de una obra; sin fila, ambos son el texto vacío."""

    __tablename__ = "ficha_obra"

    proyecto_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    cliente: Mapped[str] = mapped_column(String(200), nullable=False, server_default="")
    ubicacion: Mapped[str] = mapped_column(String(200), nullable=False, server_default="")


def crear_esquema_obra(motor: Engine) -> None:
    """Crea `ficha_obra` si aún no existe (pruebas y bases en memoria; las de disco migran)."""
    METADATA_OBRA.create_all(motor)
