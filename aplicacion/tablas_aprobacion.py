"""El rastro de aprobaciones de la carpeta de trabajo (MP-4, Tarea 17; diseño §5.4 y §10).

Vive en la base del caso (revisión `caso_0014_mp_aprobacion`): una fila por envío, retiro o
dictamen, **solo inserción**. Cada fila guarda el sello del eslabón de su versión
(`EslabonVersion.huella_eslabon`) y su propia huella encadenada a la anterior de la misma obra: una
cadena paralela a la del núcleo, fuera de `core/`. Dos salvaguardas en la base: `cierre_de` es único
(un envío se cierra una sola vez, por retiro o por dictamen) y (`proyecto_id`, `anterior`) también
(dos eventos no cuelgan del mismo eslabón). `MetaData` propia, sin clave foránea a `core.models`
(como `paquete/modelo.py`); la escribe y la lee solo `aplicacion/aprobaciones.py`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Engine, Integer, MetaData, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["METADATA_APROBACION", "FilaEventoAprobacion", "crear_esquema_aprobacion"]

METADATA_APROBACION = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_APROBACION


class FilaEventoAprobacion(Base):
    """Un envío, un retiro o un dictamen sobre una versión de una obra."""

    __tablename__ = "mp_aprobacion_evento"
    __table_args__ = (
        UniqueConstraint("cierre_de", name="uq_mp_aprobacion_cierre"),
        UniqueConstraint("proyecto_id", "anterior", name="uq_mp_aprobacion_anterior"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)  # envio | retiro | dictamen
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    huella_version: Mapped[str] = mapped_column(String(64), nullable=False)
    resultado: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notas: Mapped[str] = mapped_column(String(2000), nullable=False)
    usuario: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    armo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cierre_de: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anterior: Mapped[str] = mapped_column(String(64), nullable=False)
    huella: Mapped[str] = mapped_column(String(64), nullable=False)


def crear_esquema_aprobacion(motor: Engine) -> None:
    """Crea `mp_aprobacion_evento` si aún no existe (pruebas y bases en memoria; las de disco
    migran)."""
    METADATA_APROBACION.create_all(motor)
