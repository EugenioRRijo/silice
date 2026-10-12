"""SL-E7: el registro encadenado con huellas (spec S3 §6.2 y §7.4). Tabla aditiva.

Módulo propio, reexportado desde `core.models` (archivos calientes, maestro §3.2). Una fila por
versión: encadena su contenido, sus `RegistroCambio`, sus anexos y el eslabón anterior **del
mismo proyecto**. El índice único (`proyecto_id`, `anterior`) es la salvaguarda de la
concurrencia (S3 §6.3): dos versiones no pueden colgar del mismo eslabón.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base

#: Tipos de sellado: `retroactivo` es el de las versiones que ya existían al abrir el caso con S3.
TIPOS_DE_ESLABON = ("normal", "retroactivo")


class EslabonVersion(Base):
    """SL-E7: el eslabón de una versión. Solo-agregar: ninguna función de `core` lo actualiza."""

    __tablename__ = "eslabon_version"
    __table_args__ = (
        Index("uq_eslabon_proyecto_anterior", "proyecto_id", "anterior", unique=True),
    )

    presupuesto_id: Mapped[int] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="CASCADE"), primary_key=True
    )
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    anterior: Mapped[str] = mapped_column(String(64))  # huella_eslabon previa; génesis: 64 ceros
    huella_contenido: Mapped[str] = mapped_column(String(64))
    huella_cambios: Mapped[str] = mapped_column(String(64))
    huella_anexos: Mapped[str] = mapped_column(String(64))
    huella_eslabon: Mapped[str] = mapped_column(String(64))
    usuario: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    tipo: Mapped[str] = mapped_column(String(12))
    version_formato: Mapped[int] = mapped_column(Integer)
