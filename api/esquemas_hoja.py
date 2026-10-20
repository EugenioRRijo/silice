"""Esquemas de `/v1/hoja` (T10, 3b-1; diseño §4.2 y §4.3).

Los montos viajan como `Monto {texto, exacto}`: `texto` a dos decimales (como la página clásica) y
`exacto` sin redondear; ningún `float` en el JSON. Los conteos son enteros. Las rebanadas 3b-2 y
3b-3 añaden aquí las vistas de cada pestaña; la 3c-1, el cuerpo y la respuesta de la edición del
espacio (E1).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from aplicacion.hoja import FilaVersion
from aplicacion.hoja_vista import (
    BaseAbierta,
    Monto,
    ResumenHoja,
    VistaApu,
    VistaEquilibrio,
    VistaEspacio,
    VistaParametros,
    VistaPlan,
    VistaPrecios,
    VistaPresupuesto,
    VistaTrazabilidad,
)

#: Cada texto de celda o de código llega acotado (diseño §4.1): ≤ 500 caracteres.
Texto500 = Annotated[str, Field(max_length=500)]


class MontoHojaRespuesta(BaseModel):
    texto: str
    exacto: str


class HallazgosHojaRespuesta(BaseModel):
    severidad: str
    total: int


class BaseAbiertaRespuesta(BaseModel):
    proyecto: str
    version: str | None
    vigente: str | None
    lista: str | None
    espacio_de: str | None
    solo_lectura: bool
    moneda: str


class ResumenHojaRespuesta(BaseModel):
    rev: int
    moneda: str
    total: MontoHojaRespuesta
    cambios: int
    pendientes_catalogo: int
    hallazgos: list[HallazgosHojaRespuesta]
    hay_plan: bool
    version_mas_nueva: str | None
    guardado_como: str | None


class VersionHojaRespuesta(BaseModel):
    codigo: str
    fecha: str
    motivo: str
    origen: str
    vigente: bool
    descartada: bool
    cambios: int


def version_a_respuesta(fila: FilaVersion) -> VersionHojaRespuesta:
    return VersionHojaRespuesta(
        codigo=fila.codigo,
        fecha=fila.fecha.isoformat(),
        motivo=fila.motivo,
        origen=fila.origen,
        vigente=fila.vigente,
        descartada=fila.descartada,
        cambios=fila.cambios,
    )


class VersionesHojaRespuesta(BaseModel):
    proyecto: str
    moneda: str
    por_omision: str | None
    versiones: list[VersionHojaRespuesta]


class BorradorNuevo(BaseModel):
    """`version: null` abre un borrador en blanco para un proyecto que aún no tiene versiones."""

    proyecto: Annotated[str, Field(min_length=1, max_length=500)]
    version: Texto500 | None = None


class InstantaneaHojaRespuesta(BaseModel):
    creadas: int
    mensaje: str | None


class BorradorHojaRespuesta(BaseModel):
    id: str
    base: BaseAbiertaRespuesta
    resumen: ResumenHojaRespuesta


class BorradorAbierto(BorradorHojaRespuesta):
    instantanea: InstantaneaHojaRespuesta


def monto_a_respuesta(monto: Monto) -> MontoHojaRespuesta:
    return MontoHojaRespuesta(texto=monto.texto, exacto=monto.exacto)


def base_a_respuesta(base: BaseAbierta) -> BaseAbiertaRespuesta:
    return BaseAbiertaRespuesta(
        proyecto=base.proyecto,
        version=base.version,
        vigente=base.vigente,
        lista=base.lista,
        espacio_de=base.espacio_de,
        solo_lectura=base.solo_lectura,
        moneda=base.moneda,
    )


def resumen_a_respuesta(resumen: ResumenHoja) -> ResumenHojaRespuesta:
    return ResumenHojaRespuesta(
        rev=resumen.rev,
        moneda=resumen.moneda,
        total=monto_a_respuesta(resumen.total),
        cambios=resumen.cambios,
        pendientes_catalogo=resumen.pendientes_catalogo,
        hallazgos=[
            HallazgosHojaRespuesta(severidad=h.severidad, total=h.total) for h in resumen.hallazgos
        ],
        hay_plan=resumen.hay_plan,
        version_mas_nueva=resumen.version_mas_nueva,
        guardado_como=resumen.guardado_como,
    )


# --- las vistas de las pestanas (3b-2) -------------------------------------------------------


class EstadoFilaRespuesta(BaseModel):
    severidad: str | None
    texto: str


class OpcionListaRespuesta(BaseModel):
    valor: str
    rotulo: str


class ColumnaTablaRespuesta(BaseModel):
    clave: str
    rotulo: str
    lista: list[OpcionListaRespuesta] | None


class TablaEspacioRespuesta(BaseModel):
    clave: str
    rotulo: str
    columnas: list[ColumnaTablaRespuesta]
    con_estado: bool


class CantidadDerivadaRespuesta(BaseModel):
    partida: str
    descripcion: str
    unidad: str
    cantidad: MontoHojaRespuesta
    origen: str


class VistaEspacioRespuesta(BaseModel):
    ayuda: str
    tablas: list[TablaEspacioRespuesta]
    filas: dict[str, list[dict[str, str]]]
    estado: dict[str, EstadoFilaRespuesta]
    derivadas: list[CantidadDerivadaRespuesta]
    total: MontoHojaRespuesta
    moneda: str
    pendientes: int
    vacio_mensaje: str | None


def vista_espacio_a_respuesta(vista: VistaEspacio) -> VistaEspacioRespuesta:
    return VistaEspacioRespuesta.model_validate(vista, from_attributes=True)


class FilaPresupuestoRespuesta(BaseModel):
    clave: str
    partida: str
    descripcion: str
    unidad: str
    cantidad: str
    cantidad_calculada: str
    escrita: bool
    pu: MontoHojaRespuesta | None
    total: MontoHojaRespuesta | None
    estado: EstadoFilaRespuesta


class VistaPresupuestoRespuesta(BaseModel):
    filas: list[FilaPresupuestoRespuesta]
    total: MontoHojaRespuesta
    moneda: str
    vacio_mensaje: str | None


def vista_presupuesto_a_respuesta(vista: VistaPresupuesto) -> VistaPresupuestoRespuesta:
    return VistaPresupuestoRespuesta.model_validate(vista, from_attributes=True)


class PartidaListaRespuesta(BaseModel):
    codigo: str
    descripcion: str


class ColumnaApuRespuesta(BaseModel):
    clave: str
    rotulo: str


class GrupoApuRespuesta(BaseModel):
    clave: str
    rotulo: str
    columnas: list[ColumnaApuRespuesta]
    filas: list[dict[str, str]]
    subtotal: MontoHojaRespuesta


class FilaCierreRespuesta(BaseModel):
    concepto: str
    monto: MontoHojaRespuesta
    nota: str


class MetricasApuRespuesta(BaseModel):
    materiales: MontoHojaRespuesta
    equipos: MontoHojaRespuesta
    mano_obra: MontoHojaRespuesta
    precio_unitario: MontoHojaRespuesta


class DetalleApuRespuesta(BaseModel):
    codigo: str
    descripcion: str
    unidad: str
    rendimiento: str
    grupos: list[GrupoApuRespuesta]
    cierre: list[FilaCierreRespuesta]
    metricas: MetricasApuRespuesta
    estados: list[str]
    solo_lectura_insumos: bool


class VistaApuRespuesta(BaseModel):
    partidas: list[PartidaListaRespuesta]
    sin_coincidencias: bool
    seleccionada: str | None
    detalle: DetalleApuRespuesta | None
    vacio_mensaje: str | None


def vista_apu_a_respuesta(vista: VistaApu) -> VistaApuRespuesta:
    return VistaApuRespuesta.model_validate(vista, from_attributes=True)


class FilaPlanRespuesta(BaseModel):
    partida: str
    valores: dict[str, str]


class PuntoCurvaRespuesta(BaseModel):
    periodo: str
    monto: MontoHojaRespuesta
    acumulado: MontoHojaRespuesta
    porcentaje: MontoHojaRespuesta


class VistaPlanRespuesta(BaseModel):
    hay_plan: bool
    etiquetas: list[str]
    filas: list[FilaPlanRespuesta]
    curva: list[PuntoCurvaRespuesta]
    moneda: str
    mensaje: str | None


def vista_plan_a_respuesta(vista: VistaPlan) -> VistaPlanRespuesta:
    return VistaPlanRespuesta.model_validate(vista, from_attributes=True)


class VistaEquilibrioRespuesta(BaseModel):
    estado: str
    moneda: str
    venta: MontoHojaRespuesta
    costo_variable: MontoHojaRespuesta
    costo_fijo: MontoHojaRespuesta
    utilidad: MontoHojaRespuesta
    punto: MontoHojaRespuesta | None
    porcentaje: MontoHojaRespuesta | None
    periodo: str | None
    fraccion_periodo: str | None
    mensaje: str


def vista_equilibrio_a_respuesta(vista: VistaEquilibrio) -> VistaEquilibrioRespuesta:
    return VistaEquilibrioRespuesta.model_validate(vista, from_attributes=True)


class CampoParametroRespuesta(BaseModel):
    clave: str
    rotulo: str
    valor: str


class VistaParametrosRespuesta(BaseModel):
    campos: list[CampoParametroRespuesta]
    moneda_proyecto: str | None
    total: MontoHojaRespuesta
    puede_convertir: bool


def vista_parametros_a_respuesta(vista: VistaParametros) -> VistaParametrosRespuesta:
    return VistaParametrosRespuesta.model_validate(vista, from_attributes=True)


class RegistroCambioRespuesta(BaseModel):
    objeto: str
    clave: str
    campo: str
    antes: str
    despues: str
    fuente: str
    responsable: str
    fecha_hora: str


class TrazabilidadHojaRespuesta(BaseModel):
    versiones: list[VersionHojaRespuesta]
    registros: list[RegistroCambioRespuesta]
    vacio_mensaje: str | None


def trazabilidad_a_respuesta(vista: VistaTrazabilidad) -> TrazabilidadHojaRespuesta:
    return TrazabilidadHojaRespuesta(
        versiones=[version_a_respuesta(v) for v in vista.versiones],
        registros=[
            RegistroCambioRespuesta.model_validate(r, from_attributes=True) for r in vista.registros
        ],
        vacio_mensaje=vista.vacio_mensaje,
    )


class ColumnaPrecioRespuesta(BaseModel):
    clave: str
    rotulo: str
    numerica: bool


class FilaPrecioRespuesta(BaseModel):
    insumo: str
    codigo: str
    tipo: str
    precio: MontoHojaRespuesta
    lista: str
    moneda: str
    fecha_precio: str
    tasa: MontoHojaRespuesta | None
    fecha_tasa: str | None
    referencia: str
    cotizacion: str
    moneda_original: str
    precio_original: MontoHojaRespuesta | None
    fuente_tasa: str
    fuente: str
    propio: str
    erosion_usd: MontoHojaRespuesta | None
    erosion_bs: MontoHojaRespuesta | None
    erosion_pct: MontoHojaRespuesta | None
    erosion_indice: MontoHojaRespuesta | None
    estado: str


class PreciosHojaRespuesta(BaseModel):
    moneda: str
    fecha_evaluacion: str
    columnas: list[ColumnaPrecioRespuesta]
    filas: list[FilaPrecioRespuesta]


def precios_a_respuesta(vista: VistaPrecios) -> PreciosHojaRespuesta:
    return PreciosHojaRespuesta.model_validate(vista, from_attributes=True)


# --- la edicion del espacio (3c-1, E1) ---------------------------------------------------------
#
# Topes del diseño (§4.1, D-9, SUPUESTOS declarados): una celda ≤ 500 caracteres y filas por tabla
# ≤ 5000 orígenes, 1000 ambientes, 1000 fuentes, 5000 puntos y 20000 vértices. Una fila admite
# hasta 40 columnas de nombre ≤ 64 caracteres (hardening: la mayor tiene 13).

NombreDeColumna = Annotated[str, Field(max_length=64)]
FilaDeTabla = Annotated[dict[NombreDeColumna, Texto500], Field(max_length=40)]


class TablasEspacioCuerpo(BaseModel):
    """Las cinco tablas del editor del espacio, completas; una ausente cuenta como vacía."""

    model_config = ConfigDict(extra="forbid")

    origenes: Annotated[list[FilaDeTabla], Field(max_length=5000)] = Field(default_factory=list)
    ambientes: Annotated[list[FilaDeTabla], Field(max_length=1000)] = Field(default_factory=list)
    fuentes: Annotated[list[FilaDeTabla], Field(max_length=1000)] = Field(default_factory=list)
    puntos: Annotated[list[FilaDeTabla], Field(max_length=5000)] = Field(default_factory=list)
    tramos: Annotated[list[FilaDeTabla], Field(max_length=20000)] = Field(default_factory=list)

    def como_filas(self) -> dict[str, list[dict[str, str]]]:
        return {nombre: getattr(self, nombre) for nombre in type(self).model_fields}


class EdicionEspacio(BaseModel):
    """`rev` es el que la persona vio (`ResumenHoja.rev`); un entero, no texto ni decimal."""

    rev: Annotated[int, Field(strict=True, ge=0)]
    tablas: TablasEspacioCuerpo


class EdicionEspacioRespuesta(BaseModel):
    """El borrador ya recalculado: su `rev` nuevo, el resumen y la vista del espacio (como R5)."""

    rev: int
    resumen: ResumenHojaRespuesta
    espacio: VistaEspacioRespuesta
