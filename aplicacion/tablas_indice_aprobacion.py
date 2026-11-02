"""El índice de aprobaciones de la instalación (MP-4, Tarea 18; choque 14 del plan de montar un
presupuesto).

Vive en `instalacion.db` (revisión `ins_0005_mp_indice_aprobacion`): una fila por envío a
aprobación de cada carpeta de trabajo, para que «Por aprobar» liste los de todas las carpetas y
quien envió vea el dictamen sin abrir cada una. **Es un reflejo, no la fuente de verdad**: la
carpeta (`mp_aprobacion_evento`, `aplicacion.tablas_aprobacion`) manda, y
`aplicacion.indice_aprobaciones.reflejar` reescribe aquí las filas de una carpeta desde su rastro.
`caso` es el nombre del archivo de la carpeta; (`caso`, `envio_id`) es único. `proyecto` es el
código de la obra (el de `GET /v1/proyectos`) y `obra`, su nombre; `nota` es la del envío;
`notas` y `armo`, los del dictamen (vacías y falso sin él). `MetaData` propia, sin clave
foránea; el total con `DecimalExacto`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, MetaData, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.models.tipos import DecimalExacto

__all__ = ["METADATA_INDICE_APROBACION", "FilaIndiceAprobacion"]

METADATA_INDICE_APROBACION = MetaData()


class Base(DeclarativeBase):
    metadata = METADATA_INDICE_APROBACION


class FilaIndiceAprobacion(Base):
    """Un envío a aprobación de una carpeta, con su desenlace."""

    __tablename__ = "mp_indice_aprobacion"
    __table_args__ = (UniqueConstraint("caso", "envio_id", name="uq_mp_indice_aprobacion_envio"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caso: Mapped[str] = mapped_column(String(255), nullable=False)
    envio_id: Mapped[int] = mapped_column(Integer, nullable=False)
    proyecto: Mapped[str] = mapped_column(String(120), nullable=False)
    obra: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    total: Mapped[Decimal] = mapped_column(DecimalExacto, nullable=False)
    moneda: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    enviado_por: Mapped[str] = mapped_column(String(200), nullable=False)
    enviado_el: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    dictamen_por: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dictamen_el: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nota: Mapped[str] = mapped_column(String(2000), nullable=False)
    notas: Mapped[str] = mapped_column(String(2000), nullable=False)
    armo: Mapped[bool] = mapped_column(Boolean, nullable=False)
