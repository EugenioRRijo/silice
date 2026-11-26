"""`/v1/notificaciones`: notificaciones persistentes por persona durante 30 días (C11, servidor).

Cada persona ve y toca solo las suyas (la sesión manda; la clave de API da 403 porque no es una
persona). Las escrituras exigen CSRF y `Origin` propio (`exigir_clave_o_sesion`). Toda respuesta,
también las de error, lleva `Cache-Control: no-store` (`RutaSinCache`).

Contrato:
- `GET /v1/notificaciones` -> 200 `{notificaciones, sin_leer, retencion_dias, maximo}`: descarta y
  borra las de más de 30 días de la cuenta, devuelve hasta 200, las más nuevas primero.
- `POST /v1/notificaciones` `{gravedad, titulo, detalle?, enlace?}` -> 201 con la notificación
  creada (`{id, gravedad, titulo, detalle, enlace, creada, leida}`).
- `POST /v1/notificaciones/leidas` `{ids}` o `{todas: true}` -> 200 `{marcadas, sin_leer}`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencias import SesionInstalacionDep, SesionInstalacionEscrituraDep
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from aplicacion import notificaciones
from aplicacion.notificaciones import (
    DIAS_RETENCION,
    MAXIMO_NOTIFICACIONES,
    DatosNotificacion,
    ItemNotificacion,
)
from seguridad.sesiones import SesionActiva

MENSAJE_CON_CLAVE = (
    "Las notificaciones son de una persona: entre con su cuenta, no con la clave de API."
)

router = APIRouter(tags=["notificaciones"], route_class=RutaSinCache)


def _persona(
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(None))],
) -> SesionActiva:
    if activa is None:
        raise HTTPException(status_code=403, detail=MENSAJE_CON_CLAVE)
    return activa


Persona = Annotated[SesionActiva, Depends(_persona)]


class EnlaceNotificacion(BaseModel):
    texto: str = Field(default="", max_length=2000)
    ruta: str = Field(default="", max_length=2000)


class NotificacionNueva(BaseModel):
    gravedad: str = Field(max_length=40)
    titulo: str = Field(max_length=2000)
    detalle: str = Field(default="", max_length=4000)
    enlace: EnlaceNotificacion | None = None


class NotificacionRespuesta(BaseModel):
    id: int
    gravedad: str
    titulo: str
    detalle: str
    enlace: EnlaceNotificacion | None
    creada: str
    leida: bool


class NotificacionesRespuesta(BaseModel):
    notificaciones: list[NotificacionRespuesta]
    sin_leer: int
    retencion_dias: int
    maximo: int


class MarcarLeidasEntrada(BaseModel):
    ids: list[int] | None = Field(default=None, max_length=MAXIMO_NOTIFICACIONES * 2)
    todas: bool = False


class MarcarLeidasRespuesta(BaseModel):
    marcadas: int
    sin_leer: int


def _serializar(item: ItemNotificacion) -> NotificacionRespuesta:
    enlace = (
        EnlaceNotificacion(texto=item.enlace_texto, ruta=item.enlace_ruta)
        if item.enlace_texto and item.enlace_ruta
        else None
    )
    return NotificacionRespuesta(
        id=item.id,
        gravedad=item.gravedad,
        titulo=item.titulo,
        detalle=item.detalle,
        enlace=enlace,
        creada=item.creada.isoformat(timespec="seconds"),
        leida=item.leida,
    )


@router.get("/v1/notificaciones", response_model=NotificacionesRespuesta)
def listar_notificaciones(
    activa: Persona,
    instalacion: SesionInstalacionDep,
) -> NotificacionesRespuesta:
    """Las notificaciones vigentes (últimos 30 días) de la cuenta actual, más nuevas primero."""
    items = notificaciones.listar(instalacion, activa.usuario_id, ahora())
    return NotificacionesRespuesta(
        notificaciones=[_serializar(item) for item in items],
        sin_leer=sum(1 for item in items if not item.leida),
        retencion_dias=DIAS_RETENCION,
        maximo=MAXIMO_NOTIFICACIONES,
    )


@router.post("/v1/notificaciones", response_model=NotificacionRespuesta, status_code=201)
def crear_notificacion(
    datos: NotificacionNueva,
    activa: Persona,
    instalacion: SesionInstalacionEscrituraDep,
) -> NotificacionRespuesta:
    """Guarda una notificación para la cuenta actual."""
    entrada = DatosNotificacion(
        gravedad=datos.gravedad,
        titulo=datos.titulo,
        detalle=datos.detalle,
        enlace_texto=datos.enlace.texto if datos.enlace is not None else "",
        enlace_ruta=datos.enlace.ruta if datos.enlace is not None else "",
    )
    try:
        creada = notificaciones.agregar(instalacion, activa.usuario_id, entrada, ahora())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return _serializar(creada)


@router.post("/v1/notificaciones/leidas", response_model=MarcarLeidasRespuesta)
def marcar_notificaciones_leidas(
    datos: MarcarLeidasEntrada,
    activa: Persona,
    instalacion: SesionInstalacionEscrituraDep,
) -> MarcarLeidasRespuesta:
    """Marca como leídas las notificaciones indicadas por `ids` o todas las de la cuenta actual."""
    try:
        marcadas = notificaciones.marcar_leidas(
            instalacion,
            activa.usuario_id,
            ids=datos.ids,
            todas=datos.todas,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    sin_leer = notificaciones.contar_sin_leer(instalacion, activa.usuario_id, ahora())
    return MarcarLeidasRespuesta(marcadas=marcadas, sin_leer=sin_leer)
