# core/models/control.py
"""Tablas aditivas de Sílice S2 (spec S2 §6.1). Módulo propio, reexportado por `core.models`, para
no tocar `entidades.py` (M §3.2); cada fase de núcleo agrega aquí las suyas con su revisión de
Alembic en `migraciones/caso/versions/`. Ninguna altera una tabla existente (ruling SF3-E0).

`valuacion`, `linea_valuacion` y `anulacion_valuacion` son solo-agregar: ninguna función de `core`
emite `UPDATE` ni `DELETE` sobre ellas (S2-R10); la única tabla que se actualiza es
`parametros_control`, y cada cambio deja su `RegistroCambio` (objeto `parametro`).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base
from core.models.tipos import DecimalExacto

PERSPECTIVAS = ("costo", "precio")


class LineaBaseControl(Base):
    """SL-E4: la línea base de control (S2 §6.1). La vigente al corte es la de mayor `desde`
    menor o igual al corte; declarar otra es agregar una fila. Queda invalidada si la moneda de su
    versión ya no es la del proyecto: se calcula, no se escribe (RV-11)."""

    __tablename__ = "linea_base_control"
    __table_args__ = (Index("ix_linea_base_control_proyecto", "proyecto_id", "desde"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    desde: Mapped[date] = mapped_column(Date)
    perspectiva: Mapped[str] = mapped_column(String(10))
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)

    calendario: Mapped[CalendarioObra] = relationship(
        back_populates="linea_base", uselist=False, cascade="all, delete-orphan"
    )


class CalendarioObra(Base):
    """SL-E4: fecha de inicio, días hábiles por período y feriados de una línea base."""

    __tablename__ = "calendario_obra"

    linea_base_id: Mapped[int] = mapped_column(
        ForeignKey("linea_base_control.id", ondelete="CASCADE"), primary_key=True
    )
    fecha_inicio: Mapped[date] = mapped_column(Date)
    dias_por_periodo: Mapped[int] = mapped_column(Integer)
    feriados: Mapped[str] = mapped_column(Text, default="[]")

    linea_base: Mapped[LineaBaseControl] = relationship(back_populates="calendario")


class ParametrosControl(Base):
    """SL-E4: umbrales de las alertas y supuestos de las opciones de un proyecto (S2 §4.5, §4.6).
    Sin fila rigen los valores por defecto de `core.budget.valor_ganado`. Todos son
    SUPUESTO_DECLARADO salvo `penalizacion_diaria`, que es un dato del contrato."""

    __tablename__ = "parametros_control"

    proyecto_id: Mapped[int] = mapped_column(
        ForeignKey("proyecto.id", ondelete="CASCADE"), primary_key=True
    )
    spi_error: Mapped[Decimal] = mapped_column(DecimalExacto)
    cpi_error: Mapped[Decimal] = mapped_column(DecimalExacto)
    retraso_error: Mapped[Decimal] = mapped_column(DecimalExacto)
    precio_info: Mapped[Decimal] = mapped_column(DecimalExacto)
    equilibrio_puntos: Mapped[Decimal] = mapped_column(DecimalExacto)
    eta_cuadrilla: Mapped[Decimal] = mapped_column(DecimalExacto)
    cuadrillas_max: Mapped[int] = mapped_column(Integer)
    eta_horas_extra: Mapped[Decimal] = mapped_column(DecimalExacto)
    horas_extra_dia: Mapped[Decimal] = mapped_column(DecimalExacto)
    recargo_horas_extra: Mapped[Decimal] = mapped_column(DecimalExacto)
    fcas_en_horas_extra: Mapped[bool] = mapped_column(Boolean)
    penalizacion_diaria: Mapped[Decimal] = mapped_column(DecimalExacto)
    fuente_penalizacion: Mapped[str] = mapped_column(String(300), default="")


class Valuacion(Base):
    """SL-E4: una valuación por cantidades ejecutadas. Cuenta desde su registro (`fecha_hora`)
    hasta que se anula (RV-18, S2-R14). El número y otros campos pueden faltar: R14 los marca."""

    __tablename__ = "valuacion"
    __table_args__ = (Index("ix_valuacion_proyecto", "proyecto_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    numero: Mapped[str] = mapped_column(String(40), default="")
    desde: Mapped[date] = mapped_column(Date)
    hasta: Mapped[date] = mapped_column(Date)
    fecha: Mapped[date | None] = mapped_column(Date, default=None)
    inspector: Mapped[str] = mapped_column(String(120), default="")
    origen: Mapped[str] = mapped_column(String(300))
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)

    lineas: Mapped[list[LineaValuacion]] = relationship(
        back_populates="valuacion", order_by="LineaValuacion.id", cascade="all, delete-orphan"
    )
    anulacion: Mapped[AnulacionValuacion | None] = relationship(
        back_populates="valuacion", uselist=False
    )


class LineaValuacion(Base):
    """SL-E4: la cantidad ejecutada de una partida en una valuación (del período, no acumulada)."""

    __tablename__ = "linea_valuacion"
    __table_args__ = (Index("ix_linea_valuacion_valuacion", "valuacion_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    valuacion_id: Mapped[int] = mapped_column(ForeignKey("valuacion.id", ondelete="CASCADE"))
    codigo_partida: Mapped[str] = mapped_column(String(40))
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto)
    fecha_medicion: Mapped[date | None] = mapped_column(Date, default=None)
    observacion: Mapped[str] = mapped_column(Text, default="")

    valuacion: Mapped[Valuacion] = relationship(back_populates="lineas")


class AnulacionValuacion(Base):
    """SL-E4: la anulación de una valuación. La anulada se conserva y deja de contar."""

    __tablename__ = "anulacion_valuacion"

    valuacion_id: Mapped[int] = mapped_column(
        ForeignKey("valuacion.id", ondelete="CASCADE"), primary_key=True
    )
    motivo: Mapped[str] = mapped_column(Text)
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)

    valuacion: Mapped[Valuacion] = relationship(back_populates="anulacion")


class CostoReal(Base):
    """SL-E4: un costo real declarado. Se convierte con `tasa_aplicable(fecha)` de S1 al calcular;
    no se guarda el convertido."""

    __tablename__ = "costo_real"
    __table_args__ = (Index("ix_costo_real_proyecto", "proyecto_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    valuacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("valuacion.id", ondelete="SET NULL"), default=None
    )
    codigo_partida: Mapped[str | None] = mapped_column(String(40), default=None)
    monto: Mapped[Decimal] = mapped_column(DecimalExacto)
    moneda: Mapped[str] = mapped_column(String(10))
    fecha: Mapped[date] = mapped_column(Date)
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))


class CitaValuacion(Base):
    """SL-E4, puente a S1 (RV-11, S1 §8.6): las valuaciones que un período de un estudio de
    reajuste usó para su ejecutado. Es la revisión de `ejecutado_periodo` que S1 deja a S2, como
    tabla aparte (ruling RP7-4): una valuación entra entera en un solo período."""

    __tablename__ = "cita_valuacion"
    __table_args__ = (UniqueConstraint("periodo_id", "valuacion_id", name="uq_cita_valuacion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo_reajuste.id", ondelete="CASCADE"))
    valuacion_id: Mapped[int] = mapped_column(ForeignKey("valuacion.id", ondelete="CASCADE"))
