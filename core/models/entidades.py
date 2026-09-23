"""Las quince entidades de docs/modelo_datos.md, en SQLAlchemy 2.0.

Siete nombres coinciden a propósito con tipos de `core.contracts` (`ComposicionAPU`,
`ItemComputo`, `Rendimiento`, `Presupuesto`, `PartidaPresupuestada`, `PuntoCurva`, `Hallazgo`):
son la misma idea en dos capas. Para que nunca se confundan, se usa **siempre cualificado**
(`from core import models` → `models.Presupuesto`), y la conversión entre modelo y contrato vive en
exactamente dos módulos: `core/catalog/mapeo.py` (catálogo) y `core/budget/persistencia.py`
(presupuesto), como fija el ADR 12 de docs/arquitectura.md.

Las enumeraciones se persisten como texto (el valor del `StrEnum`) o entero (el del `IntEnum`), no
como `sqlalchemy.Enum`: añadir un dominio nuevo no debe exigir una migración de esquema.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.contracts.apu import TipoRendimiento
from core.models.base import Base
from core.models.tipos import DecimalExacto


class TipoInsumo(StrEnum):
    """Naturaleza de un insumo. Determina en qué tupla del APU entra su línea."""

    MATERIAL = "material"
    EQUIPO = "equipo"
    MANO_OBRA = "mano_obra"


#: Prefijo del código generado para cada tipo de insumo (docs/modelo_datos.md §2.1).
PREFIJO_CODIGO_INSUMO = {
    TipoInsumo.MATERIAL: "MAT",
    TipoInsumo.EQUIPO: "EQU",
    TipoInsumo.MANO_OBRA: "MO",
}


# ---------------------------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------------------------


class Partida(Base):
    """Cabecera de un APU: qué se ejecuta, en qué unidad y en qué dominio."""

    __tablename__ = "partida"
    __table_args__ = (Index("ix_partida_descripcion", "descripcion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    codigo_covenin: Mapped[str | None] = mapped_column(String(40), default=None)
    descripcion: Mapped[str] = mapped_column(String(300))
    unidad: Mapped[str] = mapped_column(String(20))
    dominio: Mapped[str] = mapped_column(String(20))

    composicion: Mapped[list[ComposicionAPU]] = relationship(
        back_populates="partida",
        order_by="ComposicionAPU.orden",
        cascade="all, delete-orphan",
    )
    rendimientos: Mapped[list[Rendimiento]] = relationship(
        back_populates="partida",
        order_by="Rendimiento.fecha",
        cascade="all, delete-orphan",
    )


class Insumo(Base):
    """Material, equipo o mano de obra. No lleva precio: el precio depende de la lista."""

    __tablename__ = "insumo"
    __table_args__ = (Index("ix_insumo_tipo_descripcion", "tipo", "descripcion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    tipo: Mapped[str] = mapped_column(String(10))
    descripcion: Mapped[str] = mapped_column(String(300))
    unidad: Mapped[str | None] = mapped_column(String(20), default=None)

    lineas: Mapped[list[ComposicionAPU]] = relationship(back_populates="insumo")
    precios: Mapped[list[PrecioInsumo]] = relationship(back_populates="insumo")


class ComposicionAPU(Base):
    """Una línea del desglose: qué insumo, cuánto y con qué depreciación (si es equipo).

    `depreciacion` y `modalidad` son ambas anulables porque cada una la lleva un solo tipo de
    insumo: `depreciacion` los equipos, `modalidad` la mano de obra. `NULL` en `modalidad` se lee
    como `jornal`, el valor por defecto del contrato.
    """

    __tablename__ = "composicion_apu"
    __table_args__ = (Index("ix_composicion_partida_orden", "partida_id", "orden"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partida.id"))
    insumo_id: Mapped[int] = mapped_column(ForeignKey("insumo.id"))
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto)
    depreciacion: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    modalidad: Mapped[str | None] = mapped_column(String(10), default=None)
    orden: Mapped[int] = mapped_column(Integer)

    partida: Mapped[Partida] = relationship(back_populates="composicion")
    insumo: Mapped[Insumo] = relationship(back_populates="lineas")


class Ejecucion(Base):
    """Obra ejecutada de la que se miden rendimientos reales (UC‑06)."""

    __tablename__ = "ejecucion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referencia: Mapped[str] = mapped_column(String(60), unique=True)
    proyecto_id: Mapped[int | None] = mapped_column(ForeignKey("proyecto.id"), default=None)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date, default=None)
    descripcion: Mapped[str] = mapped_column(String(300), default="")

    proyecto: Mapped[Proyecto | None] = relationship(back_populates="ejecuciones")
    rendimientos: Mapped[list[Rendimiento]] = relationship(back_populates="ejecucion")


class Rendimiento(Base):
    """Unidades de partida por día. Un rendimiento medido exige la ejecución que lo produjo."""

    __tablename__ = "rendimiento"
    __table_args__ = (
        CheckConstraint(
            f"tipo <> '{TipoRendimiento.MEDIDO.value}' OR ejecucion_id IS NOT NULL",
            name="ck_rendimiento_medido_exige_ejecucion",
        ),
        Index("ix_rendimiento_partida_tipo_fecha", "partida_id", "tipo", "fecha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partida.id"))
    valor: Mapped[Decimal] = mapped_column(DecimalExacto)
    tipo: Mapped[str] = mapped_column(String(10))
    fecha: Mapped[date] = mapped_column(Date)
    condiciones: Mapped[str] = mapped_column(String(300), default="")
    ejecucion_id: Mapped[int | None] = mapped_column(ForeignKey("ejecucion.id"), default=None)

    partida: Mapped[Partida] = relationship(back_populates="rendimientos")
    ejecucion: Mapped[Ejecucion | None] = relationship(back_populates="rendimientos")


# ---------------------------------------------------------------------------------------------
# Precios y su historial
# ---------------------------------------------------------------------------------------------


class ListaPrecios(Base):
    """Precios vigentes desde una fecha. Inmutable una vez que un presupuesto la referencia."""

    __tablename__ = "lista_precios"
    __table_args__ = (Index("ix_lista_precios_fecha_vigencia", "fecha_vigencia"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    moneda: Mapped[str] = mapped_column(String(10))
    fecha_vigencia: Mapped[date] = mapped_column(Date)
    origen: Mapped[str] = mapped_column(String(200), default="")

    precios: Mapped[list[PrecioInsumo]] = relationship(
        back_populates="lista", cascade="all, delete-orphan"
    )
    cambios: Mapped[list[CambioPrecio]] = relationship(
        back_populates="lista_nueva", foreign_keys="CambioPrecio.lista_nueva_id"
    )


class PrecioInsumo(Base):
    """Precio de un insumo en una lista. Para la mano de obra, el jornal diario."""

    __tablename__ = "precio_insumo"
    __table_args__ = (
        UniqueConstraint("lista_id", "insumo_id", name="uq_precio_insumo_lista_insumo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lista_id: Mapped[int] = mapped_column(ForeignKey("lista_precios.id"))
    insumo_id: Mapped[int] = mapped_column(ForeignKey("insumo.id"))
    precio: Mapped[Decimal] = mapped_column(DecimalExacto)

    lista: Mapped[ListaPrecios] = relationship(back_populates="precios")
    insumo: Mapped[Insumo] = relationship(back_populates="precios")


class CambioPrecio(Base):
    """Historial: qué insumo cambió al pasar de una lista a otra y cuánto (UC‑02)."""

    __tablename__ = "cambio_precio"
    __table_args__ = (Index("ix_cambio_precio_lista_nueva", "lista_nueva_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lista_anterior_id: Mapped[int] = mapped_column(ForeignKey("lista_precios.id"))
    lista_nueva_id: Mapped[int] = mapped_column(ForeignKey("lista_precios.id"))
    insumo_id: Mapped[int] = mapped_column(ForeignKey("insumo.id"))
    precio_anterior: Mapped[Decimal] = mapped_column(DecimalExacto)
    precio_nuevo: Mapped[Decimal] = mapped_column(DecimalExacto)
    variacion: Mapped[Decimal] = mapped_column(DecimalExacto)
    fecha: Mapped[date] = mapped_column(Date)

    lista_anterior: Mapped[ListaPrecios] = relationship(foreign_keys=[lista_anterior_id])
    lista_nueva: Mapped[ListaPrecios] = relationship(
        back_populates="cambios", foreign_keys=[lista_nueva_id]
    )
    insumo: Mapped[Insumo] = relationship()
    incidencias: Mapped[list[IncidenciaCambio]] = relationship(
        back_populates="cambio", cascade="all, delete-orphan"
    )


class IncidenciaCambio(Base):
    """Efecto de un cambio de precio sobre el precio unitario de una partida (UC‑02)."""

    __tablename__ = "incidencia_cambio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cambio_id: Mapped[int] = mapped_column(ForeignKey("cambio_precio.id"))
    partida_id: Mapped[int] = mapped_column(ForeignKey("partida.id"))
    precio_unitario_anterior: Mapped[Decimal] = mapped_column(DecimalExacto)
    precio_unitario_nuevo: Mapped[Decimal] = mapped_column(DecimalExacto)
    variacion: Mapped[Decimal] = mapped_column(DecimalExacto)

    cambio: Mapped[CambioPrecio] = relationship(back_populates="incidencias")
    partida: Mapped[Partida] = relationship()


# ---------------------------------------------------------------------------------------------
# Proyecto, presupuesto y auditoría
# ---------------------------------------------------------------------------------------------


class Proyecto(Base):
    """Obra que agrupa presupuestos y ejecuciones."""

    __tablename__ = "proyecto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True)
    descripcion: Mapped[str] = mapped_column(String(500), default="")
    dominio: Mapped[str] = mapped_column(String(20), default="")

    presupuestos: Mapped[list[Presupuesto]] = relationship(
        back_populates="proyecto", cascade="all, delete-orphan"
    )
    ejecuciones: Mapped[list[Ejecucion]] = relationship(back_populates="proyecto")


class Presupuesto(Base):
    """Versión valorada de un proyecto: referencia su lista y congela sus parámetros de costo."""

    __tablename__ = "presupuesto"
    __table_args__ = (
        UniqueConstraint("proyecto_id", "codigo", name="uq_presupuesto_proyecto_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40))
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id"))
    fecha: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(10))
    lista_precios_id: Mapped[int] = mapped_column(ForeignKey("lista_precios.id"))
    fcas: Mapped[Decimal] = mapped_column(DecimalExacto)
    bono_alimentacion: Mapped[Decimal] = mapped_column(DecimalExacto)
    administracion: Mapped[Decimal] = mapped_column(DecimalExacto)
    utilidad: Mapped[Decimal] = mapped_column(DecimalExacto)

    proyecto: Mapped[Proyecto] = relationship(back_populates="presupuestos")
    lista_precios: Mapped[ListaPrecios] = relationship()
    partidas: Mapped[list[PartidaPresupuestada]] = relationship(
        back_populates="presupuesto",
        order_by="PartidaPresupuestada.orden",
        cascade="all, delete-orphan",
    )
    curva: Mapped[list[PuntoCurva]] = relationship(
        back_populates="presupuesto",
        order_by="PuntoCurva.orden",
        cascade="all, delete-orphan",
    )
    hallazgos: Mapped[list[Hallazgo]] = relationship(
        back_populates="presupuesto", cascade="all, delete-orphan"
    )
    items_computo: Mapped[list[ItemComputo]] = relationship(back_populates="presupuesto")


class ItemComputo(Base):
    """Cantidad de obra con su procedencia. Conserva la unidad original y la normalizada."""

    __tablename__ = "item_computo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_partida: Mapped[str] = mapped_column(String(40))
    descripcion: Mapped[str] = mapped_column(String(300))
    unidad_original: Mapped[str] = mapped_column(String(20))
    unidad: Mapped[str] = mapped_column(String(20))
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto)
    origen_id: Mapped[str] = mapped_column(String(120))
    origen_tipo: Mapped[str] = mapped_column(String(20))
    dominio: Mapped[str] = mapped_column(String(20))
    presupuesto_id: Mapped[int | None] = mapped_column(ForeignKey("presupuesto.id"), default=None)
    regla: Mapped[str | None] = mapped_column(String(300), default=None)
    parametros: Mapped[str] = mapped_column(Text, default="{}")
    especificaciones: Mapped[str] = mapped_column(Text, default="{}")

    presupuesto: Mapped[Presupuesto | None] = relationship(back_populates="items_computo")


class PartidaPresupuestada(Base):
    """Renglón del presupuesto con la instantánea completa de su `ResultadoAPU`."""

    __tablename__ = "partida_presupuestada"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id"))
    partida_id: Mapped[int] = mapped_column(ForeignKey("partida.id"))
    item_computo_id: Mapped[int] = mapped_column(ForeignKey("item_computo.id"))
    orden: Mapped[int] = mapped_column(Integer)
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto)
    materiales: Mapped[Decimal] = mapped_column(DecimalExacto)
    equipos: Mapped[Decimal] = mapped_column(DecimalExacto)
    mano_obra: Mapped[Decimal] = mapped_column(DecimalExacto)
    costo_directo: Mapped[Decimal] = mapped_column(DecimalExacto)
    con_administracion: Mapped[Decimal] = mapped_column(DecimalExacto)
    precio_unitario: Mapped[Decimal] = mapped_column(DecimalExacto)
    total: Mapped[Decimal] = mapped_column(DecimalExacto)

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="partidas")
    partida: Mapped[Partida] = relationship()
    item_computo: Mapped[ItemComputo] = relationship()


class PuntoCurva(Base):
    """Período del plan de trabajo. El acumulado se guarda tal cual: la regla R2 lo audita."""

    __tablename__ = "punto_curva"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id"))
    orden: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[str] = mapped_column(String(120))
    monto: Mapped[Decimal] = mapped_column(DecimalExacto)
    acumulado: Mapped[Decimal] = mapped_column(DecimalExacto)

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="curva")


class Hallazgo(Base):
    """Resultado persistido de una regla de verificación sobre un presupuesto (CLAUDE.md §7)."""

    __tablename__ = "hallazgo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id"))
    regla: Mapped[str] = mapped_column(String(10))
    severidad: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[str] = mapped_column(String(500))
    impacto: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    origen_ids: Mapped[str] = mapped_column(Text, default="[]")
    valor_observado: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    valor_esperado: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="hallazgos")
