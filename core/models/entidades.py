"""Las entidades de docs/modelo_datos.md, en SQLAlchemy 2.0: las diecisiete del sistema y las
tablas aditivas del sprint final (SF3: instantánea, registro de cambios y origen de precios).

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

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
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


class JustificacionRendimiento(Base):
    """UC‑06, flujo 4a: la justificación con la que el proyectista acepta la advertencia de RF‑27.

    Una por rendimiento, ligada al que se registró con la advertencia. Guarda también el texto de
    la advertencia aceptada, para leerla sin reconstruir la dispersión de ese momento. Tabla
    aditiva: `crear_esquema` la agrega a una base existente sin tocar las demás, y la relación se
    declara solo de este lado, así que `Rendimiento` y sus consultas no cambian (expediente C6.1).
    """

    __tablename__ = "justificacion_rendimiento"

    rendimiento_id: Mapped[int] = mapped_column(
        ForeignKey("rendimiento.id", ondelete="CASCADE"), primary_key=True
    )
    texto: Mapped[str] = mapped_column(Text)
    advertencia: Mapped[str] = mapped_column(Text)
    fecha: Mapped[date] = mapped_column(Date)

    rendimiento: Mapped[Rendimiento] = relationship()


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


class DescarteVersion(Base):
    """UC‑02, flujo 7a: la versión revalorada que el usuario descartó.

    Es una marca, no un borrado: la versión sigue guardada y cargándose como documento, y el
    historial de cambios que la produjo (`CambioPrecio`, `IncidenciaCambio`) se conserva porque
    alimenta el histórico del módulo predictivo (`docs/ERS.md:170`). Tabla aditiva: `crear_esquema`
    la agrega a una base existente sin tocar las demás (expediente C3.2).
    """

    __tablename__ = "descarte_version"

    presupuesto_id: Mapped[int] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="CASCADE"), primary_key=True
    )
    fecha: Mapped[date] = mapped_column(Date)

    presupuesto: Mapped[Presupuesto] = relationship()


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
    """Resultado persistido de una regla de verificación sobre un presupuesto (NORMAS.md §7)."""

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


# ---------------------------------------------------------------------------------------------
# Sprint final (SF3): instantánea por versión, registro de cambios y origen de precios.
# Todas son tablas aditivas: `crear_esquema` las agrega a una base anterior sin `ALTER TABLE`
# (ruling SF3‑E0, docs/bitacora/2026-10-sf-expedientes.md).
# ---------------------------------------------------------------------------------------------


class ComposicionVersion(Base):
    """SF‑E6: la composición de APU y el rendimiento con que se valoró una partida en una versión.

    Una por (versión, código de partida). `rendimiento` es la instantánea del rendimiento vigente de
    la partida en esa versión.
    """

    __tablename__ = "composicion_version"
    __table_args__ = (
        UniqueConstraint("presupuesto_id", "codigo_partida", name="uq_composicion_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    codigo_partida: Mapped[str] = mapped_column(String(40))
    descripcion: Mapped[str] = mapped_column(String(300))
    unidad: Mapped[str] = mapped_column(String(20))
    rendimiento: Mapped[Decimal] = mapped_column(DecimalExacto)

    lineas: Mapped[list[LineaComposicionVersion]] = relationship(
        back_populates="composicion",
        order_by="LineaComposicionVersion.orden",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class LineaComposicionVersion(Base):
    """SF‑E6: una línea de la composición congelada, con el precio con que se valoró.

    `insumo_id` es de qué insumo del catálogo salió (anulable): sirve para revalorar la línea con
    otra lista de precios (UC‑02, cotizaciones). `tipo` es un valor de `TipoInsumo`.
    """

    __tablename__ = "linea_composicion_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    composicion_id: Mapped[int] = mapped_column(
        ForeignKey("composicion_version.id", ondelete="CASCADE")
    )
    orden: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(10))
    insumo_id: Mapped[int | None] = mapped_column(ForeignKey("insumo.id"), default=None)
    descripcion: Mapped[str] = mapped_column(String(300))
    unidad: Mapped[str | None] = mapped_column(String(20), default=None)
    cantidad: Mapped[Decimal] = mapped_column(DecimalExacto)
    precio: Mapped[Decimal] = mapped_column(DecimalExacto)
    depreciacion: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    modalidad: Mapped[str | None] = mapped_column(String(10), default=None)

    composicion: Mapped[ComposicionVersion] = relationship(back_populates="lineas")
    insumo: Mapped[Insumo | None] = relationship()


class PlanVersion(Base):
    """SF‑E6: el reparto del plan de trabajo de una versión (período, partida, fracción).

    La curva guardada (`PuntoCurva`) no conserva el reparto por partida: sin esta tabla ni una
    cotización ni una restauración podrían conservar el plan (RF‑54, RF‑56). `codigo_partida` es
    anulable para un período declarado sin partidas.
    """

    __tablename__ = "plan_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuesto.id", ondelete="CASCADE"))
    periodo: Mapped[int] = mapped_column(Integer)
    etiqueta: Mapped[str] = mapped_column(String(120))
    orden: Mapped[int] = mapped_column(Integer)
    codigo_partida: Mapped[str | None] = mapped_column(String(40), default=None)
    fraccion: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)


#: Motivos con que una versión nueva declara su `VersionOrigen`.
MOTIVOS_VERSION = ("edicion", "restauracion", "cotizacion", "revaloracion", "conversion")


class VersionOrigen(Base):
    """SF‑E2: de qué versión salió otra (cierra la limitación C3.2 de `DescarteVersion`).

    Una fila por versión que no se elaboró de cero: edición, restauración, cotización o
    revaloración (`MOTIVOS_VERSION`).
    """

    __tablename__ = "version_origen"

    presupuesto_id: Mapped[int] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="CASCADE"), primary_key=True
    )
    origen_id: Mapped[int | None] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="SET NULL"), default=None
    )
    motivo: Mapped[str] = mapped_column(String(20))


class RegistroCambio(Base):
    """SF‑E2: una celda cambiada al guardar una versión (spec §9.3). Los valores son texto.

    `version_origen_id` es la versión de la que salió el cambio y `version_resultante_id` la que lo
    contiene (la misma, para un registro que no crea versión). La **fuente del cambio** (por qué y
    con qué respaldo) y el **responsable** son obligatorios; el origen de la medida es de la fila
    de la hoja y no entra aquí.
    """

    __tablename__ = "registro_cambio"
    __table_args__ = (Index("ix_registro_cambio_resultante", "version_resultante_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    version_origen_id: Mapped[int | None] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="SET NULL"), default=None
    )
    version_resultante_id: Mapped[int] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="CASCADE")
    )
    objeto: Mapped[str] = mapped_column(String(20))
    clave: Mapped[str] = mapped_column(String(200))
    campo: Mapped[str] = mapped_column(String(60))
    valor_anterior: Mapped[str] = mapped_column(Text, default="")
    valor_nuevo: Mapped[str] = mapped_column(Text, default="")
    fuente: Mapped[str] = mapped_column(String(300))
    responsable: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


#: Alcances de una lista de precios.
ALCANCE_GLOBAL = "global"
ALCANCE_PROYECTO = "proyecto"
ALCANCE_EMPRESA = "empresa"  # SL-E2: la lista de una empresa (S1 §6.1)
ALCANCE_REFERENCIA = "referencia"  # SL-E2: MaPreX en Bs, solo para contrastar con R11 (S1 §6.2)
#: Alcances que `Catalogo.lista_vigente` nunca resuelve: una versión los referencia explícitamente.
ALCANCES_FUERA_DE_VIGENTE = (ALCANCE_PROYECTO, ALCANCE_EMPRESA, ALCANCE_REFERENCIA)


class ListaPreciosOrigen(Base):
    """SF‑E7: de dónde sale una lista (tasa de cambio con su fecha) y su alcance.

    Una lista sin fila aquí es **global** (todas las de las bases anteriores). Una lista de alcance
    `proyecto` nace de una cotización: copia de `lista_base_id` con insumos cambiados, que una
    versión referencia explícitamente (DA‑SF‑9), y `lista_vigente` no la resuelve.
    """

    __tablename__ = "lista_precios_origen"

    lista_id: Mapped[int] = mapped_column(
        ForeignKey("lista_precios.id", ondelete="CASCADE"), primary_key=True
    )
    tasa: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    fecha_tasa: Mapped[date | None] = mapped_column(Date, default=None)
    alcance: Mapped[str] = mapped_column(String(10), default=ALCANCE_GLOBAL)
    proyecto_id: Mapped[int | None] = mapped_column(
        ForeignKey("proyecto.id", ondelete="CASCADE"), default=None
    )
    lista_base_id: Mapped[int | None] = mapped_column(ForeignKey("lista_precios.id"), default=None)


class ReferenciaPrecio(Base):
    """SF‑E7: la referencia de un precio en su lista (p. ej. el Ref de MaPreX)."""

    __tablename__ = "referencia_precio"

    precio_id: Mapped[int] = mapped_column(
        ForeignKey("precio_insumo.id", ondelete="CASCADE"), primary_key=True
    )
    referencia: Mapped[str] = mapped_column(String(60))


class Cotizacion(Base):
    """SF‑E7: una cotización activa en una lista de proyecto (proveedor, número y fecha)."""

    __tablename__ = "cotizacion"
    __table_args__ = (UniqueConstraint("lista_id", "insumo_id", name="uq_cotizacion_lista_insumo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lista_id: Mapped[int] = mapped_column(ForeignKey("lista_precios.id", ondelete="CASCADE"))
    insumo_id: Mapped[int] = mapped_column(ForeignKey("insumo.id"))
    precio: Mapped[Decimal] = mapped_column(DecimalExacto)
    precio_base: Mapped[Decimal | None] = mapped_column(DecimalExacto, default=None)
    proveedor: Mapped[str] = mapped_column(String(120))
    numero: Mapped[str] = mapped_column(String(60))
    fecha: Mapped[date] = mapped_column(Date)

    insumo: Mapped[Insumo] = relationship()
