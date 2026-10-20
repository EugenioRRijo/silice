"""Esquemas de `/v1/hoja` (T10, 3b-1; diseño §4.2 y §4.3).

Los montos viajan como `Monto {texto, exacto}`: `texto` a dos decimales (como la página clásica) y
`exacto` sin redondear; ningún `float` en el JSON. Los conteos son enteros. Las rebanadas 3b-2 y
3b-3 añaden aquí las vistas de cada pestaña.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from aplicacion.hoja_vista import (
    BaseAbierta,
    Monto,
    ResumenHoja,
    VistaApu,
    VistaEspacio,
    VistaPlan,
    VistaPresupuesto,
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
