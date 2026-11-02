"""`GET /v1/tablero`: el tablero del proyecto para la interfaz nueva (sesion 2b, ola 4).

La misma lectura que la pagina «Tablero del proyecto» de Streamlit (`aplicacion.tablero`, antes
`ui.tablero`): tarjetas de la version vigente, anillos y tarjetas del control de obra, la curva de
plan y avance, el desglose del costo, las partidas de mayor peso y el comparativo de versiones.
Solo lectura (RU-10): no abre la version ni escribe.

Acceso: `LEER_PROYECTO`, por clave de API o por sesion del navegador (RM-3). Los montos, porcentajes
e indices viajan como texto ya presentado (con los decimales de presentacion). Los numeros que se
dibujan (`valor`, `fraccion`) viajan tambien como texto decimal exacto: la interfaz los convierte
solo para trazar el grafico, nunca para mostrar ni para calcular. Un proyecto que no existe en el
caso responde 404; uno sin version guardada, 200 con `version` nulo (la pantalla dice como armarla).
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from api.dependencias import SesionDep
from api.sesion_web import exigir_clave_o_sesion
from aplicacion import tablero
from aplicacion.estilo import indice, porcentaje
from aplicacion.proyectos import resolver_proyecto
from core.catalog import Catalogo
from seguridad.permisos import Accion

router = APIRouter(
    prefix="/v1/tablero",
    tags=["tablero"],
    dependencies=[Depends(exigir_clave_o_sesion(Accion.LEER_PROYECTO))],
)

_CERO = Decimal(0)
_UNO = Decimal(1)


class TarjetaRespuesta(BaseModel):
    rotulo: str
    valor: str
    detalle: str = ""
    #: El monto sin redondear (texto decimal) de una tarjeta de dinero; vacío en las demás (VB-21).
    exacto: str = ""


class AnilloRespuesta(BaseModel):
    """Un anillo de progreso: `texto` es lo que se lee en el centro; `fraccion`, lo que se dibuja
    (nula si no hay dato). `favorable` es verdadero si el indice llega a 1; nulo si no aplica."""

    rotulo: str
    fraccion: str | None
    texto: str
    favorable: bool | None = None


class ControlRespuesta(BaseModel):
    disponible: bool
    motivo: str = ""
    anillos: list[AnilloRespuesta] = Field(default_factory=list)
    tarjetas: list[TarjetaRespuesta] = Field(default_factory=list)


class PuntoRespuesta(BaseModel):
    orden: int
    periodo: str
    valor: str


class SerieRespuesta(BaseModel):
    serie: str
    puntos: list[PuntoRespuesta]


class CurvasRespuesta(BaseModel):
    titulo: str
    series: list[SerieRespuesta] = Field(default_factory=list)


class RubroRespuesta(BaseModel):
    rubro: str
    monto: str
    peso: str
    valor: str


class ParetoRespuesta(BaseModel):
    partida: str
    descripcion: str
    total: str
    peso: str
    acumulado: str
    valor: str


class VersionRespuesta(BaseModel):
    version: str
    fecha: str
    motivo: str
    costo_directo: str
    total: str
    vigente: bool
    valor: str


class TableroRespuesta(BaseModel):
    proyecto: str
    version: str | None = None
    fecha: str | None = None
    moneda: str | None = None
    renglones: int = 0
    tarjetas: list[TarjetaRespuesta] = Field(default_factory=list)
    control: ControlRespuesta | None = None
    curvas: CurvasRespuesta | None = None
    desglose: list[RubroRespuesta] = Field(default_factory=list)
    pareto: list[ParetoRespuesta] = Field(default_factory=list)
    versiones: list[VersionRespuesta] = Field(default_factory=list)


def _numero(valor: object) -> str:
    """Un numero de grafico (float de `aplicacion.tablero`) como texto decimal, sin notacion
    cientifica."""
    return format(Decimal(repr(float(valor))), "f")  # type: ignore[arg-type]


def _tarjetas(tarjetas: list[tablero.Tarjeta]) -> list[TarjetaRespuesta]:
    return [
        TarjetaRespuesta(rotulo=t.rotulo, valor=t.valor, detalle=t.detalle, exacto=t.exacto)
        for t in tarjetas
    ]


def _fraccion(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def _favorable(valor: Decimal | None) -> bool:
    return valor is not None and valor >= _UNO


def _control(datos: tablero.DatosTablero) -> ControlRespuesta:
    indicadores = datos.control.indicadores
    if indicadores is None:
        return ControlRespuesta(disponible=False, motivo=datos.control.motivo)
    avance = tablero.avance_fisico(indicadores)
    return ControlRespuesta(
        disponible=True,
        anillos=[
            AnilloRespuesta(
                rotulo="Avance fisico", fraccion=_fraccion(avance), texto=porcentaje(avance)
            ),
            AnilloRespuesta(
                rotulo="SPI (plazo)",
                fraccion=_fraccion(indicadores.spi),
                texto=indice(indicadores.spi),
                favorable=_favorable(indicadores.spi),
            ),
            AnilloRespuesta(
                rotulo="CPI (costo)",
                fraccion=_fraccion(indicadores.cpi),
                texto=indice(indicadores.cpi),
                favorable=_favorable(indicadores.cpi),
            ),
        ],
        tarjetas=_tarjetas(
            tablero.tarjetas_de_control(datos.control, datos.elaboracion.presupuesto.moneda)
        ),
    )


def _curvas(datos: tablero.DatosTablero) -> CurvasRespuesta:
    presupuesto = datos.elaboracion.presupuesto
    con_control = datos.control.indicadores is not None
    filas = tablero.filas_de_curvas(presupuesto, datos.control)
    series: dict[str, list[PuntoRespuesta]] = {}
    for fila in filas:
        series.setdefault(str(fila["Serie"]), []).append(
            PuntoRespuesta(
                orden=int(fila["Orden"]),  # type: ignore[call-overload]
                periodo=str(fila["Periodo"]),
                valor=_numero(fila["Acumulado"]),
            )
        )
    return CurvasRespuesta(
        titulo="Valor ganado (PV, EV, AC)" if con_control else "Plan acumulado",
        series=[SerieRespuesta(serie=nombre, puntos=puntos) for nombre, puntos in series.items()],
    )


def _tablero(datos: tablero.DatosTablero) -> TableroRespuesta:
    presupuesto = datos.elaboracion.presupuesto
    return TableroRespuesta(
        proyecto=datos.proyecto,
        version=datos.codigo,
        fecha=datos.fecha.isoformat(),
        moneda=presupuesto.moneda,
        renglones=len(presupuesto.partidas),
        tarjetas=_tarjetas(tablero.tarjetas_del_presupuesto(datos)),
        control=_control(datos),
        curvas=_curvas(datos),
        desglose=[
            RubroRespuesta(
                rubro=str(f["Rubro"]),
                monto=str(f["Monto"]),
                peso=str(f["Peso"]),
                valor=_numero(f["monto"]),
            )
            for f in tablero.filas_de_desglose(presupuesto)
        ],
        pareto=[
            ParetoRespuesta(
                partida=str(f["Partida"]),
                descripcion=str(f["Descripcion"]),
                total=str(f["Total"]),
                peso=str(f["Peso"]),
                acumulado=str(f["Acumulado"]),
                valor=_numero(f["monto"]),
            )
            for f in tablero.filas_pareto(presupuesto)
        ],
        versiones=[
            VersionRespuesta(
                version=str(f["Version"]),
                fecha=str(f["Fecha"]),
                motivo=str(f["Motivo"]),
                costo_directo=str(f["Costo directo"]),
                total=str(f["Total"]),
                vigente=f["Vigente"] == "si",
                valor=_numero(f["total"]),
            )
            for f in datos.versiones
        ],
    )


@router.get("", response_model=TableroRespuesta)
def leer_tablero(
    sesion: SesionDep,
    proyecto: str = Query(
        min_length=1,
        description="Nombre del proyecto en el caso abierto.",
    ),
) -> TableroRespuesta:
    """El tablero de la version vigente del proyecto (`LEER_PROYECTO`)."""
    encontrado = resolver_proyecto(sesion, proyecto)  # codigo de /v1/proyectos o nombre (V-11)
    if encontrado is None:
        raise HTTPException(
            status_code=404, detail=f"El proyecto «{proyecto}» no existe en este caso."
        )
    proyecto = encontrado.nombre
    try:
        datos = tablero.leer_tablero(sesion, Catalogo(sesion), proyecto)
    except (SQLAlchemyError, ValueError, LookupError) as error:
        raise HTTPException(
            status_code=409, detail=f"No se pudo leer el proyecto: {error}"
        ) from error
    if datos is None:
        return TableroRespuesta(proyecto=proyecto)
    return _tablero(datos)
