"""`/v1/obras`: los datos de la mesa de control, el inicio de «Presupuestos y obras» (MOD-4a).

Rutas finas sobre `aplicacion.mesa` (diseño de módulos §6 y §12.6):

- `GET /v1/obras/resumen` (`LEER_PROYECTO`: arma y revisa) → `{moneda, hoy, cifras, conversiones,
  fuera_de_suma, obras}`. `cifras` trae solo las que se pueden calcular, en el orden valor ganado,
  avance; `moneda` es aquella en que se sumaron (la de la carpeta o, sin ella, la de las obras si
  todas comparten una; `null` si no se sumó nada). Cada obra lleva su etapa con el texto de la
  interfaz, su total, el avance real y el planificado (EV y PV sobre BAC, en %), qué pasa y el
  siguiente paso.
- `GET /v1/obras/pendientes` (`EDITAR_HOJA`: arma) → `{grupos: [{clave, titulo, items}]}`; solo los
  grupos con alguna fuente registrada, aunque estén vacíos (el front quita los vacíos).

Montos, índices y porcentajes viajan como **texto** con punto decimal (nunca como número JSON);
la interfaz los formatea en es-VE sin recalcular. `hoy` es el día del reloj del servidor. Una obra
en la otra moneda se suma con la tasa del BCV de su corte (`tasa_aplicable`, a lo sumo 7 días);
sin tasa va a `fuera_de_suma`. Toda respuesta lleva `Cache-Control: no-store`; un fallo de la
base es un 503 con un mensaje fijo (el texto del error lleva el SQL); el 422 no repite lo enviado.
Las dos rutas solo leen.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.acceso import EDITAR, LEER
from api.dependencias import SesionDep, ruta_de_url, url_de_la_peticion, url_del_proceso
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion.listas_para_armar import moneda_de_la_carpeta
from aplicacion.mesa import (
    ETAPA_TEXTO,
    Cifra,
    ObraEnMesa,
    Siguiente,
    TasaDelBcv,
    cifras_de_la_mesa,
    moneda_de_la_suma,
    obras_de_la_mesa,
    pendientes,
)
from aplicacion.proyectos import obras_de_las_carpetas
from core.catalog import Catalogo
from core.catalog.indices import TasaNoDisponible, tasa_aplicable
from operacion.base_datos import listar_casos
from seguridad.permisos import Accion, permitido
from seguridad.sesiones import SesionActiva

MENSAJE_FORMA = "La consulta de la mesa de control no es válida."
MENSAJE_BASE = "No se pudo leer la carpeta de trabajo. Intente de nuevo."
_CENTESIMA = Decimal("0.01")
_DECIMA = Decimal("0.1")
_CIEN = Decimal(100)


class _RutaObras(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (como en la Hoja)."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(prefix="/v1/obras", tags=["obras"], route_class=_RutaObras)


class SiguienteRespuesta(BaseModel):
    texto: str = Field(description="El texto del botón")
    pagina: str = Field(description="La pantalla a la que lleva (`id` de la ruta del front)")


class CifraRespuesta(BaseModel):
    clave: str
    titulo: str
    actual: str
    meta: str
    delta: str
    delta_pct: str | None
    sentido: str = Field(description="«rendimiento»: más es mejor")
    detalle: str | None


class ConversionRespuesta(BaseModel):
    obra: str = Field(description="El nombre de la obra convertida")
    moneda: str = Field(description="La moneda de la obra")
    tasa: str = Field(description="Bs por USD")
    fecha: str = Field(description="El corte de la obra (ISO)")
    fecha_tasa: str = Field(description="La fecha valor de la tasa del BCV (ISO)")


class ObraRespuesta(BaseModel):
    codigo: str
    nombre: str
    cliente: str
    etapa: str
    etapa_texto: str
    version: str | None
    total: str | None
    moneda: str
    avance_real: str | None = Field(description="EV ÷ BAC × 100, a 0,1")
    avance_plan: str | None = Field(description="PV ÷ BAC × 100, a 0,1")
    que_pasa: str | None
    siguiente: SiguienteRespuesta | None


class ResumenRespuesta(BaseModel):
    moneda: str | None
    hoy: str
    cifras: list[CifraRespuesta]
    conversiones: list[ConversionRespuesta]
    fuera_de_suma: list[str]
    obras: list[ObraRespuesta]


class PendienteRespuesta(BaseModel):
    obra: str = Field(description="El código de la obra")
    obra_nombre: str
    texto: str
    accion: SiguienteRespuesta


class GrupoRespuesta(BaseModel):
    clave: str
    titulo: str
    items: list[PendienteRespuesta]


class PendientesRespuesta(BaseModel):
    grupos: list[GrupoRespuesta]


def _texto(valor: Decimal | None) -> str | None:
    return None if valor is None else str(valor)


def _siguiente(paso: Siguiente | None) -> SiguienteRespuesta | None:
    return None if paso is None else SiguienteRespuesta(texto=paso.texto, pagina=paso.pagina)


def _porcentaje(parte: Decimal | None, bac: Decimal | None) -> str | None:
    if parte is None or bac is None or bac == 0:
        return None
    return str((parte / bac * _CIEN).quantize(_DECIMA, rounding=ROUND_HALF_UP))


def _cifra(cifra: Cifra) -> CifraRespuesta:
    return CifraRespuesta(
        clave=cifra.clave,
        titulo=cifra.titulo,
        actual=str(cifra.actual),
        meta=str(cifra.meta),
        delta=str(cifra.delta),
        delta_pct=_texto(cifra.delta_pct),
        sentido=cifra.sentido,
        detalle=cifra.detalle,
    )


def _obra(obra: ObraEnMesa) -> ObraRespuesta:
    return ObraRespuesta(
        codigo=obra.codigo,
        nombre=obra.nombre,
        cliente=obra.cliente,
        etapa=obra.etapa,
        etapa_texto=ETAPA_TEXTO[obra.etapa],
        version=obra.version,
        total=None
        if obra.total is None
        else str(obra.total.quantize(_CENTESIMA, rounding=ROUND_HALF_UP)),
        moneda=obra.moneda,
        avance_real=_porcentaje(obra.ev, obra.bac),
        avance_plan=_porcentaje(obra.pv, obra.bac),
        que_pasa=obra.que_pasa,
        siguiente=_siguiente(obra.siguiente),
    )


def _tasa_del_bcv(sesion: Session) -> Callable[[date], TasaDelBcv | None]:
    def tasa(fecha: date) -> TasaDelBcv | None:
        try:
            aplicable = tasa_aplicable(sesion, fecha)
        except TasaNoDisponible:
            return None
        return TasaDelBcv(aplicable.valor, aplicable.fecha)

    return tasa


def _resumen(sesion: Session, hoy: date) -> ResumenRespuesta:
    obras = obras_de_la_mesa(sesion, Catalogo(sesion), hoy)
    de_la_carpeta = moneda_de_la_carpeta(sesion, hoy)
    cifras = cifras_de_la_mesa(obras, de_la_carpeta, _tasa_del_bcv(sesion))
    return ResumenRespuesta(
        moneda=moneda_de_la_suma(obras, de_la_carpeta),
        hoy=hoy.isoformat(),
        cifras=[_cifra(c) for c in (cifras.valor_ganado, cifras.avance) if c is not None],
        conversiones=[
            ConversionRespuesta(
                obra=c.obra,
                moneda=c.moneda,
                tasa=str(c.tasa),
                fecha=c.fecha.isoformat(),
                fecha_tasa=c.fecha_tasa.isoformat(),
            )
            for c in cifras.conversiones
        ],
        fuera_de_suma=list(cifras.fuera_de_suma),
        obras=[_obra(obra) for obra in obras],
    )


@router.get("/resumen", response_model=ResumenRespuesta, dependencies=LEER)
def resumen(sesion: SesionDep) -> ResumenRespuesta:
    """Las cifras de las obras en ejecución y la tabla de obras de la carpeta de trabajo."""
    try:
        return _resumen(sesion, ahora().date())
    except SQLAlchemyError:
        # El texto de un error de base lleva el SQL y sus parámetros: no sale por la API.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE) from None


@router.get("/pendientes", response_model=PendientesRespuesta, dependencies=EDITAR)
def pendientes_de_la_mesa(sesion: SesionDep) -> PendientesRespuesta:
    """Lo que requiere atención en las obras de la carpeta, agrupado."""
    try:
        grupos = pendientes(sesion, ahora().date())
    except SQLAlchemyError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE) from None
    return PendientesRespuesta(
        grupos=[
            GrupoRespuesta(
                clave=grupo.clave,
                titulo=grupo.titulo,
                items=[
                    PendienteRespuesta(
                        obra=item.obra,
                        obra_nombre=item.obra_nombre,
                        texto=item.texto,
                        accion=SiguienteRespuesta(
                            texto=item.accion.texto, pagina=item.accion.pagina
                        ),
                    )
                    for item in grupo.items
                ],
            )
            for grupo in grupos
        ]
    )


TITULO_DE_LA_EMPRESA = "Carpeta de la empresa"


class ObraDeCarpetaRespuesta(BaseModel):
    carpeta: str | None = Field(
        description="El nombre que acepta `POST /v1/casos/actual`; `null`: la carpeta de la empresa"
    )
    carpeta_titulo: str = Field(
        description="«Carpeta de la empresa» para `null`; si no, el nombre sin extensión"
    )
    obra_id: int
    obra: str
    version_codigo: str | None = Field(description="La versión vigente; `null` si no tiene")


class ObrasTodasRespuesta(BaseModel):
    carpeta_actual: str | None = Field(
        description="La carpeta abierta en esta sesión; `null` si es la de la empresa"
    )
    carpeta_actual_titulo: str = Field(
        description="El título de esa carpeta, como `carpeta_titulo`, aunque no tenga obras"
    )
    obras: list[ObraDeCarpetaRespuesta]


def _titulo_de_carpeta(carpeta: str | None) -> str:
    return TITULO_DE_LA_EMPRESA if carpeta is None else Path(carpeta).stem


def _carpetas_visibles(
    request: Request, activa: SesionActiva | None
) -> tuple[str | None, list[tuple[str | None, Path]]]:
    """La carpeta abierta (`None` si es la de la empresa) y las que esta cuenta puede listar: todas
    con `CAMBIAR_CASO`; si no, solo la abierta (la clave de API ve el caso del proceso y no elige
    otra). Nunca ofrece una obra que al abrirla diera 403."""
    empresa = ruta_de_url(url_del_proceso())
    abierta = ruta_de_url(url_de_la_peticion(request))
    es_empresa = abierta is None or abierta == empresa
    actual = None if es_empresa else abierta.name  # type: ignore[union-attr]
    if activa is not None and permitido(activa.roles, Accion.CAMBIAR_CASO):
        propias = None if empresa is None else empresa.resolve()
        todas: list[tuple[str | None, Path]] = [(None, empresa)] if empresa is not None else []
        todas.extend((r.name, r) for r in listar_casos() if r.resolve() != propias)
        return actual, todas
    if es_empresa:
        return actual, [] if empresa is None else [(None, empresa)]
    return actual, [(actual, abierta)]  # type: ignore[list-item]


@router.get("/todas", response_model=ObrasTodasRespuesta)
def obras_de_todas_las_carpetas(
    request: Request,
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(Accion.LEER_PROYECTO))],
) -> ObrasTodasRespuesta:
    """Las obras de todas las carpetas (con `CAMBIAR_CASO`) o solo las de la carpeta abierta. Abre
    cada base en solo lectura; una carpeta ilegible se omite."""
    actual, carpetas = _carpetas_visibles(request, activa)
    return ObrasTodasRespuesta(
        carpeta_actual=actual,
        carpeta_actual_titulo=_titulo_de_carpeta(actual),
        obras=[
            ObraDeCarpetaRespuesta(
                carpeta=o.carpeta,
                carpeta_titulo=_titulo_de_carpeta(o.carpeta),
                obra_id=o.obra_id,
                obra=o.obra,
                version_codigo=o.version_codigo,
            )
            for o in obras_de_las_carpetas(carpetas)
        ],
    )
