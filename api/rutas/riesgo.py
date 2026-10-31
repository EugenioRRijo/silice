"""`/v1/riesgo`: el riesgo de la obra y el informe de mejora de la estimación (plan vial, fase C).

- `POST /mejora` `{costo_final_real, presupuesto_original, estimacion_silice}` → 200
  `{error_original_pct, error_silice_pct, mejora_pp}`, todo texto con punto decimal. Cálculo puro
  (`aplicacion.riesgo.mejora`): no toca la base ni la carpeta abierta (Tarea 15).
- `GET /insumos?proyecto=&version=` → los insumos de los APU de la versión (sin las mezclas que se
  recalculan con su receta), los componentes de esas recetas, las series que admite la moneda del
  presupuesto y el inicio de la línea base, si hay: lo que la pantalla ofrece para el mapa (T16).
- `POST /proyeccion` `{proyecto, version, inicio, meses, trayectorias, semilla, ventana_meses,
  mapa}` → percentiles 50 y 80, reserva (P80 − total base), contribución por insumo, meses usados
  y supuestos (Tarea 16, D-V-3). `inicio` nulo: el de la línea base de la versión; sin ella, 422.
  El mapa es `{descripción del insumo o código del componente de la receta: serie}`.
- `POST /comprobacion` `{proyecto, version, meses, trayectorias_por_corte, semilla, ventana_meses,
  mapa}` → los cortes móviles con su P50, P80 y lo real, la cobertura exacta y en porcentaje (dos
  decimales), cuántos cayeron dentro y `n_cortes`. Lleva su propio `trayectorias_por_corte`, 500
  por omisión: con 2.000 tarda varias veces más (bitácora de la fase C). Lee la historia hasta el
  último día del mes anterior a hoy.

- `GET /reportes/{tipo}` → un libro .xlsx (Tarea 21, `aplicacion.reportes_viales`) con una hoja de
  portada que dice de dónde sale cada cifra. `riesgo`: `proyecto`, `version`, `mapa` (un objeto
  JSON de insumo a serie, en texto), `inicio`, `meses`, `trayectorias`, `semilla`, `ventana_meses`
  y, con `comprobar=true`, la comprobación hacia atrás (`trayectorias_por_corte`); `mejora`:
  `costo_final_real`, `presupuesto_original` y `estimacion_silice` como texto con punto decimal.
  Mismo acceso que el resto (`ver_riesgo`), solo lee y no deja caché; tipo que no existe, 404.

Proyección y comprobación calculan y no guardan nada: leen la carpeta del caso (`SesionDep`) y la
instalación (el cálculo publicado de la mezcla propia). Montos como **texto con punto decimal,
exactos** (`format(x, "f")`, sin exponente); la pantalla redondea al presentar. Errores del cálculo
(pocos meses, serie que no se admite, falta de tasa, sin inicio): 422 con el mensaje; obra o versión
que no existe: 404. Los números enteros de la forma van como enteros JSON.

Acceso: `Accion.VER_RIESGO` (arma, revisa y administrador), con clave de API o sesión web (cookie
más `X-Silice-CSRF` y `Origin`, porque el método escribe). Las cifras entran como **texto con punto
decimal**, igual que en el resto de la API (la coma es cosa del front, `cifraEscrita.ts`); un texto
que no es decimal, un costo real que no es positivo o una estimación negativa es 422 con
`{"detalle": ...}`. Un cuerpo o una consulta sin la forma esperada es 422 con un mensaje fijo que
no repite lo enviado (`_RutaRiesgo`, como `_RutaVial`): `MENSAJE_MEJORA` en `/mejora` y
`MENSAJE_FORMA` en las demás.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    TypeAdapter,
    ValidationError,
)

from api.dependencias import SesionDep, SesionInstalacionDep
from api.rutas.hoja_exportar import TIPO_XLSX
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import reportes_viales
from aplicacion.riesgo import obra
from aplicacion.riesgo.mejora import mejora_de_estimacion
from seguridad.permisos import Accion

VER_RIESGO = exigir_clave_o_sesion(Accion.VER_RIESGO)

MENSAJE_FORMA = (
    "Los datos del riesgo no tienen la forma esperada: envíe la obra y la versión, el mapa como "
    "insumo y serie (texto), y los meses, las trayectorias, la semilla y la ventana como números "
    "enteros dentro de sus topes."
)
MENSAJE_MEJORA = (
    "Envíe el costo final real, el presupuesto original y la estimación de Sílice, cada uno como "
    "texto con punto decimal, por ejemplo 1250.50."
)


class _RutaRiesgo(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (como `_RutaVial`)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(
    prefix="/v1/riesgo",
    tags=["riesgo"],
    dependencies=[Depends(VER_RIESGO)],
    route_class=_RutaRiesgo,
)

__all__ = ["MENSAJE_FORMA", "MENSAJE_MEJORA", "VER_RIESGO", "hoy", "router"]

#: Un decimal con punto, sin exponente, NaN ni infinito (lo mismo que el resto de la API).
_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")


class MejoraEntrada(BaseModel):
    costo_final_real: StrictStr  # decimal con punto
    presupuesto_original: StrictStr  # decimal con punto
    estimacion_silice: StrictStr  # decimal con punto


class MejoraRespuesta(BaseModel):
    error_original_pct: str  # dos decimales, con punto
    error_silice_pct: str
    mejora_pp: str  # negativa si Sílice acertó menos que el original


def _decimal(nombre: str, texto: str) -> Decimal:
    if not _DECIMAL.fullmatch(texto.strip()):
        raise HTTPException(
            status_code=422,
            detail=f"{nombre}: escriba un número decimal con punto, por ejemplo 1250.50.",
        )
    return Decimal(texto.strip())


@router.post("/mejora", response_model=MejoraRespuesta)
@sin_eco(MENSAJE_MEJORA)
def informe_de_mejora(cuerpo: MejoraEntrada) -> MejoraRespuesta:
    real = _decimal("costo_final_real", cuerpo.costo_final_real)
    original = _decimal("presupuesto_original", cuerpo.presupuesto_original)
    silice = _decimal("estimacion_silice", cuerpo.estimacion_silice)
    try:
        mejora = mejora_de_estimacion(real, original, silice)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return MejoraRespuesta(
        error_original_pct=_texto(mejora.error_original_pct),
        error_silice_pct=_texto(mejora.error_silice_pct),
        mejora_pp=_texto(mejora.mejora_pp),
    )


# --- Tarea 16: la obra ------------------------------------------------------------------------

#: Topes de la forma: cortan una petición que tardaría horas (D-V-3 son 2.000, 36 y 6).
MAX_TRAYECTORIAS = 20_000
MAX_TRAYECTORIAS_POR_CORTE = 2_000
MAX_MESES = 60
MAX_VENTANA = 240
MAX_MAPA = 500
#: Aviso de la Tarea 14: con 500 trayectorias por corte la comprobación tarda unos 20 s.
TRAYECTORIAS_POR_CORTE = 500

Texto = Annotated[StrictStr, Field(min_length=1, max_length=500)]
VersionCodigo = Annotated[StrictStr, Field(min_length=1, max_length=40)]
Meses = Annotated[StrictInt, Field(ge=1, le=MAX_MESES)]
Semilla = Annotated[StrictInt, Field(ge=0, le=2**31 - 1)]
Ventana = Annotated[StrictInt, Field(ge=12, le=MAX_VENTANA)]
Mapa = Annotated[dict[Texto, Texto], Field(max_length=MAX_MAPA)]


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProyeccionEntrada(_Estricto):
    proyecto: Texto
    version: VersionCodigo
    inicio: date | None = None  # nulo: el de la línea base de la versión
    meses: Meses = 6
    trayectorias: Annotated[StrictInt, Field(ge=1, le=MAX_TRAYECTORIAS)] = 2000
    semilla: Semilla = 1
    ventana_meses: Ventana = 36
    mapa: Mapa = {}


class ComprobacionEntrada(_Estricto):
    proyecto: Texto
    version: VersionCodigo
    meses: Meses = 6
    trayectorias_por_corte: Annotated[StrictInt, Field(ge=1, le=MAX_TRAYECTORIAS_POR_CORTE)] = (
        TRAYECTORIAS_POR_CORTE
    )
    semilla: Semilla = 1
    ventana_meses: Ventana = 36
    mapa: Mapa = {}


class SerieRespuesta(BaseModel):
    codigo: str
    nombre: str


class MezclaRespuesta(BaseModel):
    insumo: str  # la descripción de la mezcla propia en el APU
    calculo: int  # el n.º del cálculo publicado del que sale su receta


class InsumosRespuesta(BaseModel):
    proyecto: str
    version: str
    moneda: str
    insumos: list[str]
    componentes: list[str]
    mezclas: list[MezclaRespuesta]
    series: list[SerieRespuesta]
    inicio_linea_base: date | None


class ContribucionRespuesta(BaseModel):
    insumo: str
    monto: str  # exacto, punto decimal


class ProyeccionRespuesta(BaseModel):
    proyecto: str
    version: str
    moneda: str
    inicio: date
    inicio_de: str  # «linea_base» o «declarado»
    meses: int
    trayectorias: int
    semilla: int
    total_base: str
    p50: str
    p80: str
    reserva: str  # P80 − total base; negativa si sale así (no se recorta)
    contribucion: list[ContribucionRespuesta]  # de mayor a menor
    meses_usados: int
    supuestos: list[str]
    mezclas: list[MezclaRespuesta]


class CorteRespuesta(BaseModel):
    corte: date
    p50: str
    p80: str
    real: str
    dentro: bool  # real <= P80


class ComprobacionRespuesta(BaseModel):
    proyecto: str
    version: str
    moneda: str
    meses: int
    trayectorias_por_corte: int
    semilla: int
    cortes: list[CorteRespuesta]
    cobertura: str  # exacta: dentro ÷ n_cortes
    cobertura_pct: str  # dos decimales, mitad hacia arriba
    dentro: int
    n_cortes: int
    mezclas: list[MezclaRespuesta]


def hoy() -> date:
    """El día del servidor (las pruebas lo fijan aquí)."""
    return ahora().date()


def _texto(valor: Decimal) -> str:
    return format(valor, "f")


def _mezclas(mezclas: dict[str, int]) -> list[MezclaRespuesta]:
    return [MezclaRespuesta(insumo=d, calculo=n) for d, n in sorted(mezclas.items())]


Proyecto = Annotated[str, Query(min_length=1, max_length=500)]
Version = Annotated[str, Query(min_length=1, max_length=40)]


@router.get("/insumos", response_model=InsumosRespuesta)
def insumos_de_la_obra(
    sesion: SesionDep, instalacion: SesionInstalacionDep, proyecto: Proyecto, version: Version
) -> InsumosRespuesta:
    """Los insumos de la versión y las series que puede seguir cada uno."""
    datos = obra.insumos_de_la_obra(sesion, instalacion, proyecto, version)
    return InsumosRespuesta(
        proyecto=datos.proyecto,
        version=datos.version,
        moneda=datos.moneda,
        insumos=datos.insumos,
        componentes=datos.componentes,
        mezclas=_mezclas(datos.mezclas),
        series=[SerieRespuesta(codigo=s.codigo, nombre=s.nombre) for s in datos.series],
        inicio_linea_base=datos.inicio_linea_base,
    )


@router.post("/proyeccion", response_model=ProyeccionRespuesta)
def proyeccion_de_la_obra(
    cuerpo: ProyeccionEntrada, sesion: SesionDep, instalacion: SesionInstalacionDep
) -> ProyeccionRespuesta:
    """La proyección del riesgo de precios de la versión (no guarda nada)."""
    r = obra.proyectar_obra(
        sesion,
        instalacion,
        cuerpo.proyecto,
        cuerpo.version,
        cuerpo.mapa,
        inicio=cuerpo.inicio,
        meses=cuerpo.meses,
        trayectorias=cuerpo.trayectorias,
        semilla=cuerpo.semilla,
        ventana_meses=cuerpo.ventana_meses,
    )
    p = r.proyeccion
    return ProyeccionRespuesta(
        proyecto=r.proyecto,
        version=r.version,
        moneda=r.moneda,
        inicio=r.inicio,
        inicio_de=r.inicio_de,
        meses=r.parametros.meses,
        trayectorias=r.parametros.trayectorias,
        semilla=p.semilla,
        total_base=_texto(p.total_base),
        p50=_texto(p.percentiles[50]),
        p80=_texto(p.percentiles[80]),
        reserva=_texto(p.reserva),
        contribucion=[ContribucionRespuesta(insumo=d, monto=_texto(m)) for d, m in p.contribucion],
        meses_usados=p.meses_usados,
        supuestos=list(p.supuestos),
        mezclas=_mezclas(r.mezclas),
    )


@router.post("/comprobacion", response_model=ComprobacionRespuesta)
def comprobacion_de_la_obra(
    cuerpo: ComprobacionEntrada, sesion: SesionDep, instalacion: SesionInstalacionDep
) -> ComprobacionRespuesta:
    """La comprobación hacia atrás de la versión con cortes móviles (no guarda nada)."""
    r = obra.comprobar_obra(
        sesion,
        instalacion,
        cuerpo.proyecto,
        cuerpo.version,
        cuerpo.mapa,
        hoy=hoy(),
        meses=cuerpo.meses,
        trayectorias=cuerpo.trayectorias_por_corte,
        semilla=cuerpo.semilla,
        ventana_meses=cuerpo.ventana_meses,
    )
    c = r.comprobacion
    return ComprobacionRespuesta(
        proyecto=r.proyecto,
        version=r.version,
        moneda=r.moneda,
        meses=r.parametros.meses,
        trayectorias_por_corte=r.parametros.trayectorias,
        semilla=r.parametros.semilla,
        cortes=[
            CorteRespuesta(
                corte=x.corte,
                p50=_texto(x.p50),
                p80=_texto(x.p80),
                real=_texto(x.real),
                dentro=x.dentro,
            )
            for x in c.cortes
        ],
        cobertura=_texto(c.cobertura),
        cobertura_pct=_texto((c.cobertura * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)),
        dentro=sum(1 for x in c.cortes if x.dentro),
        n_cortes=c.n_cortes,
        mezclas=_mezclas(r.mezclas),
    )


# --- Tarea 21: los reportes en Excel ----------------------------------------------------------

MENSAJE_REPORTE_RIESGO = (
    "El reporte de riesgo pide la obra (proyecto), la versión (version) y el mapa de series "
    "(mapa) como un objeto JSON de insumo a serie, en texto."
)
_MAPA_EN_TEXTO = TypeAdapter(Mapa)


def _mapa_de_la_consulta(texto: str) -> dict[str, str]:
    try:
        return _MAPA_EN_TEXTO.validate_json(texto)
    except ValidationError:
        raise HTTPException(status_code=422, detail=MENSAJE_REPORTE_RIESGO) from None


def _libro_de_mejora(
    costo_final_real: str | None, presupuesto_original: str | None, estimacion_silice: str | None
) -> bytes:
    if costo_final_real is None or presupuesto_original is None or estimacion_silice is None:
        raise HTTPException(status_code=422, detail=MENSAJE_MEJORA)
    real = _decimal("costo_final_real", costo_final_real)
    original = _decimal("presupuesto_original", presupuesto_original)
    silice = _decimal("estimacion_silice", estimacion_silice)
    try:
        mejora = mejora_de_estimacion(real, original, silice)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return reportes_viales.informe_de_mejora(
        mejora, costo_final_real=real, presupuesto_original=original, estimacion_silice=silice
    )


def _libro(contenido: bytes, tipo: str, *partes: str) -> Response:
    nombre = reportes_viales.nombre_de_reporte(tipo, *partes)
    return Response(
        content=contenido,
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get(
    "/reportes/{tipo}",
    response_class=Response,
    responses={200: {"content": {TIPO_XLSX: {}}, "description": "El libro .xlsx del reporte."}},
)
def descargar_reporte(
    tipo: str,
    sesion: SesionDep,
    instalacion: SesionInstalacionDep,
    proyecto: Annotated[str | None, Query(min_length=1, max_length=500)] = None,
    version: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    mapa: Annotated[str, Query(max_length=100_000)] = "{}",
    inicio: date | None = None,
    meses: Annotated[int, Query(ge=1, le=MAX_MESES)] = 6,
    trayectorias: Annotated[int, Query(ge=1, le=MAX_TRAYECTORIAS)] = 2000,
    semilla: Annotated[int, Query(ge=0, le=2**31 - 1)] = 1,
    ventana_meses: Annotated[int, Query(ge=12, le=MAX_VENTANA)] = 36,
    comprobar: bool = False,
    trayectorias_por_corte: Annotated[int, Query(ge=1, le=MAX_TRAYECTORIAS_POR_CORTE)] = (
        TRAYECTORIAS_POR_CORTE
    ),
    costo_final_real: Annotated[str | None, Query(max_length=60)] = None,
    presupuesto_original: Annotated[str | None, Query(max_length=60)] = None,
    estimacion_silice: Annotated[str | None, Query(max_length=60)] = None,
) -> Response:
    """Un reporte de riesgo o de mejora en Excel (`aplicacion.reportes_viales`); solo lee."""
    if tipo == "mejora":
        return _libro(
            _libro_de_mejora(costo_final_real, presupuesto_original, estimacion_silice), "mejora"
        )
    if tipo != "riesgo":
        raise HTTPException(status_code=404, detail=f"No existe el reporte «{tipo[:40]}».")
    if proyecto is None or version is None:
        raise HTTPException(status_code=422, detail=MENSAJE_REPORTE_RIESGO)
    declarado = _mapa_de_la_consulta(mapa)
    proyectada = obra.proyectar_obra(
        sesion,
        instalacion,
        proyecto,
        version,
        declarado,
        inicio=inicio,
        meses=meses,
        trayectorias=trayectorias,
        semilla=semilla,
        ventana_meses=ventana_meses,
    )
    comprobada = None
    if comprobar:
        comprobada = obra.comprobar_obra(
            sesion,
            instalacion,
            proyecto,
            version,
            declarado,
            hoy=hoy(),
            meses=meses,
            trayectorias=trayectorias_por_corte,
            semilla=semilla,
            ventana_meses=ventana_meses,
        )
    contenido = reportes_viales.informe_de_riesgo(proyectada, comprobada, mapa=declarado)
    return _libro(contenido, "riesgo", proyectada.proyecto, version)
