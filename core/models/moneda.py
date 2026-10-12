"""Tablas aditivas de Sílice S1 (spec S1 §5.2). Módulo propio para no tocar `entidades.py` (M §3.2);
cada fase de núcleo agrega aquí las suyas con su revisión en `migraciones/caso/`. Ninguna altera
una tabla existente (ruling SF3-E0)."""

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
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base
from core.models.tipos import DecimalExacto


class SerieIndice(Base):
    """SL-E1: una serie (tasa compra/venta, INPC, insumos de la construcción)."""

    __tablename__ = "serie_indice"
    __table_args__ = (UniqueConstraint("codigo", name="uq_serie_indice_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str] = mapped_column(String(200))
    organismo: Mapped[str] = mapped_column(String(120))
    unidad: Mapped[str] = mapped_column(String(40))
    periodicidad: Mapped[str] = mapped_column(String(12))
    base: Mapped[str] = mapped_column(String(200), default="")


class ImportacionIndice(Base):
    """SL-E1: un archivo importado para una serie, con su huella SHA-256 y su fuente."""

    __tablename__ = "importacion_indice"
    __table_args__ = (Index("ix_importacion_indice_serie_huella", "serie_id", "huella"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey("serie_indice.id"))
    archivo: Mapped[str] = mapped_column(String(255))
    huella: Mapped[str] = mapped_column(String(64))
    fuente: Mapped[str] = mapped_column(String(500))
    fecha_descarga: Mapped[date] = mapped_column(Date)
    fecha_importacion: Mapped[datetime] = mapped_column(DateTime)
    responsable: Mapped[str] = mapped_column(String(120))
    filas_leidas: Mapped[int] = mapped_column(Integer)
    filas_rechazadas: Mapped[int] = mapped_column(Integer)
    informe: Mapped[str] = mapped_column(Text, default="")


class ValorIndice(Base):
    """SL-E1: valor de una serie en una fecha (fecha valor o primer día del período)."""

    __tablename__ = "valor_indice"
    __table_args__ = (
        UniqueConstraint("serie_id", "fecha", "importacion_id", name="uq_valor_indice"),
        Index("ix_valor_indice_serie_fecha", "serie_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey("serie_indice.id"))
    importacion_id: Mapped[int] = mapped_column(
        ForeignKey("importacion_indice.id", ondelete="CASCADE")
    )
    fecha: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(DecimalExacto)
    provisional: Mapped[bool] = mapped_column(Boolean, default=False)


class MonedaProyecto(Base):
    """SL-E1: historial de la moneda de un proyecto; la vigente es la última."""

    __tablename__ = "moneda_proyecto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    moneda: Mapped[str] = mapped_column(String(10))
    desde: Mapped[datetime] = mapped_column(DateTime)
    version_id: Mapped[int | None] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="SET NULL"), default=None
    )
    responsable: Mapped[str] = mapped_column(String(120))
    fuente: Mapped[str] = mapped_column(String(300))


class PrecioOrigen(Base):
    """SL-E1: origen de un precio (S1 §5.1). Sin fila, manda la lista (precedencia única)."""

    __tablename__ = "precio_origen"

    precio_id: Mapped[int] = mapped_column(
        ForeignKey("precio_insumo.id", ondelete="CASCADE"), primary_key=True
    )
    moneda_original: Mapped[str] = mapped_column(String(10))
    precio_original: Mapped[Decimal] = mapped_column(DecimalExacto)
    fecha_precio: Mapped[date] = mapped_column(Date)
    tasa: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    fecha_tasa: Mapped[date | None] = mapped_column(Date, default=None)
    fuente_tasa: Mapped[str] = mapped_column(String(300), default="")
    fuente: Mapped[str] = mapped_column(String(300), default="")


class ListaEmpresa(Base):
    """SL-E2: la lista de una empresa (S1 §6.1). La empresa es texto (RV-6): una instantánea sin
    clave foránea a `instalacion.db`; S3 la rellena desde la empresa propia."""

    __tablename__ = "lista_empresa"

    lista_id: Mapped[int] = mapped_column(
        ForeignKey("lista_precios.id", ondelete="CASCADE"), primary_key=True
    )
    empresa_nombre: Mapped[str] = mapped_column(String(200))
    empresa_rif: Mapped[str] = mapped_column(String(20))
    lista_base_id: Mapped[int] = mapped_column(ForeignKey("lista_precios.id"))
    lista_referencia_id: Mapped[int | None] = mapped_column(
        ForeignKey("lista_precios.id"), default=None
    )
    plazo_vigencia_dias: Mapped[int] = mapped_column(Integer)
    rango_inferior: Mapped[Decimal] = mapped_column(DecimalExacto)
    rango_superior: Mapped[Decimal] = mapped_column(DecimalExacto)


class ClausulaReajuste(Base):
    """SL-E3: la cláusula de reajuste de un contrato (S1 §8.1), tal como se declaró al guardar un
    estudio. Inmutable: rehacerla es guardar otro estudio con otra cláusula."""

    __tablename__ = "clausula_reajuste"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    duracion_meses: Mapped[int] = mapped_column(Integer)
    fecha_referencia_primer_anio: Mapped[date] = mapped_column(Date)
    periodicidad: Mapped[str] = mapped_column(String(20))
    mecanismo: Mapped[str] = mapped_column(String(20))
    mecanismo_pagadero: Mapped[str | None] = mapped_column(String(20), default=None)
    fuente_pagadero: Mapped[str] = mapped_column(String(300), default="")
    estructura: Mapped[str] = mapped_column(String(20))
    fecha_base_indices: Mapped[date] = mapped_column(Date)
    r: Mapped[Decimal] = mapped_column(DecimalExacto)
    fuente_r: Mapped[str] = mapped_column(String(300))
    r_en_comprobacion: Mapped[bool] = mapped_column(Boolean, default=False)
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))


class ComponenteClausula(Base):
    """SL-E3: un componente de la cláusula con su serie y, con estructura declarada, su peso."""

    __tablename__ = "componente_clausula"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clausula_id: Mapped[int] = mapped_column(ForeignKey("clausula_reajuste.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(Integer)
    componente: Mapped[str] = mapped_column(String(20))
    serie_id: Mapped[int] = mapped_column(ForeignKey("serie_indice.id"))
    peso: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)


class EstudioReajuste(Base):
    """SL-E3: un estudio guardado (S1 §8.5). Solo-agregar: un parcial al corte se reemplaza una
    sola vez por otro estudio que lo cita en `reemplaza_a` (S1-R21)."""

    __tablename__ = "estudio_reajuste"
    __table_args__ = (UniqueConstraint("reemplaza_a", name="uq_estudio_reemplaza_a"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    clausula_id: Mapped[int] = mapped_column(ForeignKey("clausula_reajuste.id", ondelete="CASCADE"))
    fecha_calculo: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20))
    fecha_corte: Mapped[date | None] = mapped_column(Date, default=None)
    reemplaza_a: Mapped[int | None] = mapped_column(ForeignKey("estudio_reajuste.id"), default=None)
    moneda: Mapped[str] = mapped_column(String(10))
    lado: Mapped[str] = mapped_column(String(10))
    monto_original: Mapped[Decimal] = mapped_column(DecimalExacto)
    total_escalatoria: Mapped[Decimal] = mapped_column(DecimalExacto)
    total_comprobacion: Mapped[Decimal] = mapped_column(DecimalExacto)
    total_reconocido: Mapped[Decimal] = mapped_column(DecimalExacto)
    avisos: Mapped[str] = mapped_column(Text, default="[]")
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class PeriodoReajuste(Base):
    """SL-E3: un período del estudio con sus resultados, la versión revalorada que usó, la tasa de
    su cierre y la importación de cada índice (`importaciones`: JSON `{"serie@AAAA-MM-DD": id}`)."""

    __tablename__ = "periodo_reajuste"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estudio_id: Mapped[int] = mapped_column(ForeignKey("estudio_reajuste.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(Integer)
    desde: Mapped[date] = mapped_column(Date)
    hasta: Mapped[date] = mapped_column(Date)
    km: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    escalatoria: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    comprobacion: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    reconocido: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    mecanismo_reconocido: Mapped[str] = mapped_column(String(20))
    version_comprobacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="SET NULL"), default=None
    )
    tasa: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    fecha_tasa: Mapped[date | None] = mapped_column(Date, default=None)
    importaciones: Mapped[str] = mapped_column(Text, default="{}")
    marcas: Mapped[str] = mapped_column(Text, default="[]")
    excepcion: Mapped[str] = mapped_column(String(300), default="")


class EjecutadoPeriodo(Base):
    """SL-E3: lo ejecutado de una partida en un período, con su fuente (acta o valuación; S1 §8.6:
    escrito a mano en la 0.6.0; S2 agrega la cita a la valuación con su propia revisión)."""

    __tablename__ = "ejecutado_periodo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodo_reajuste.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(Integer)
    codigo_partida: Mapped[str] = mapped_column(String(40))
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto)
    fuente: Mapped[str] = mapped_column(String(300))
