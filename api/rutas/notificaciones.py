"""`/v1/notificaciones`: notificaciones persistentes por persona durante 30 días (C11, servidor).

Cada persona ve y toca solo las suyas (la sesión manda; la clave de API da 403 porque no es una
persona). Las escrituras exigen CSRF y `Origin` propio (`exigir_clave_o_sesion`). Toda respuesta,
también las de error, lleva `Cache-Control: no-store` (`RutaSinCache`), y el 422 de forma responde
`{"detalle": <mensaje fijo>}` sin repetir lo enviado (`RutaSinEco`).

Contrato:
- `GET /v1/notificaciones` -> 200 `{notificaciones, sin_leer, retencion_dias, maximo}`: descarta y
  borra las de más de 30 días de la cuenta, devuelve hasta 200, las más nuevas primero.
- `POST /v1/notificaciones` `{gravedad, titulo, detalle?, enlace?}` -> 201 con la notificación
  creada (`{id, gravedad, titulo, detalle, enlace, creada, leida}`).
- `POST /v1/notificaciones/leidas` `{ids}` o `{todas: true}` -> 200 `{marcadas, sin_leer}`.

C11b (`docs/especificaciones/2026-11-26-notificaciones-por-evento.md`):
- `GET /v1/notificaciones` antes de listar hace el barrido perezoso de lo que vence con la fecha,
  solo para quien lista (`aplicacion.avisos_por_evento.barrer`): el recordatorio de lo que espera
  su dictamen desde 2 días hábiles y las compras por pedir de las obras de la carpeta abierta.
  Escribe, así que su sesión de la instalación es la de escritura (`BEGIN IMMEDIATE`), pero lee
  la carpeta y las preferencias con la diferida: el cerrojo de escritura se toma después de leer
  la carpeta, solo para emitir y listar (orden caso→instalación).
- `GET /v1/notificaciones/preferencias` -> 200 `{categorias: [{categoria, titulo, descripcion,
  activa, aplica, obligatoria}]}`: las cinco categorías de la cuenta de la sesión.
- `PUT /v1/notificaciones/preferencias` `{categorias: [{categoria, activa}]}` -> 200 con la misma
  forma; 422 con el motivo si la categoría no existe, está repetida o es obligatoria para su rol
  (quien revisa no apaga `por_dictaminar`). Solo las propias.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.dependencias import (
    SesionInstalacionDep,
    SesionInstalacionEscrituraDep,
    abridor_de_la_carpeta,
    carpeta_de_la_empresa,
    carpeta_de_la_peticion,
)
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco, sin_eco
from aplicacion import avisos_por_evento, notificaciones
from aplicacion.avisos_por_evento import CATEGORIAS, Preferencia, PreferenciaInvalida
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

MENSAJE_FORMA = (
    "La notificación no es válida: revise la gravedad, el título, el detalle y el enlace."
)
MENSAJE_FORMA_LEIDAS = (
    "Indique qué notificaciones marcar: sus números (ids) o todas (todas: true)."
)
MENSAJE_FORMA_PREFERENCIAS = (
    "Las preferencias no son válidas: indique cada categoría por su nombre y si queda activa."
)
#: El mayor `id` que cabe en el INTEGER de SQLite (64 bits con signo).
_MAYOR_ID = 2**63 - 1


class _RutaNotificaciones(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco`."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(tags=["notificaciones"], route_class=_RutaNotificaciones)


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
    ids: list[Annotated[int, Field(gt=0, le=_MAYOR_ID)]] | None = Field(
        default=None, max_length=MAXIMO_NOTIFICACIONES * 2
    )
    todas: bool = False


class MarcarLeidasRespuesta(BaseModel):
    marcadas: int
    sin_leer: int


class PreferenciaDeNotificacionRespuesta(BaseModel):
    categoria: str
    titulo: str
    descripcion: str
    activa: bool
    aplica: bool = Field(description="Si a la cuenta le llega esta categoría por su rol")
    obligatoria: bool = Field(description="Si su rol no la deja apagar")


class PreferenciasDeNotificacionRespuesta(BaseModel):
    categorias: list[PreferenciaDeNotificacionRespuesta]


class PreferenciaDeNotificacionCambio(BaseModel):
    categoria: str = Field(max_length=40)
    activa: bool


class PreferenciasDeNotificacionCambio(BaseModel):
    categorias: list[PreferenciaDeNotificacionCambio] = Field(max_length=len(CATEGORIAS) * 2)


def _preferencias(lista: list[Preferencia]) -> PreferenciasDeNotificacionRespuesta:
    return PreferenciasDeNotificacionRespuesta(
        categorias=[
            PreferenciaDeNotificacionRespuesta(
                categoria=p.categoria,
                titulo=p.titulo,
                descripcion=p.descripcion,
                activa=p.activa,
                aplica=p.aplica,
                obligatoria=p.obligatoria,
            )
            for p in lista
        ]
    )


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
    request: Request,
    activa: Persona,
    lectura: SesionInstalacionDep,
    instalacion: SesionInstalacionEscrituraDep,
) -> NotificacionesRespuesta:
    """Las notificaciones vigentes (últimos 30 días) de la cuenta actual, más nuevas primero,
    después de crear las que vencen hoy para ella (recordatorios y compras, C11b)."""
    momento = ahora()
    avisos_por_evento.barrer(
        instalacion,
        activa,
        momento,
        carpeta_empresa=carpeta_de_la_empresa(),
        caso=carpeta_de_la_peticion(request),
        abrir_carpeta=abridor_de_la_carpeta(request),
        lectura=lectura,
    )
    items = notificaciones.listar(instalacion, activa.usuario_id, momento)
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
@sin_eco(MENSAJE_FORMA_LEIDAS)
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


@router.get("/v1/notificaciones/preferencias", response_model=PreferenciasDeNotificacionRespuesta)
def leer_preferencias(
    activa: Persona, instalacion: SesionInstalacionDep
) -> PreferenciasDeNotificacionRespuesta:
    """Qué categorías de notificaciones recibe la cuenta actual (C11b)."""
    return _preferencias(avisos_por_evento.preferencias(instalacion, activa.usuario_id))


@router.put("/v1/notificaciones/preferencias", response_model=PreferenciasDeNotificacionRespuesta)
@sin_eco(MENSAJE_FORMA_PREFERENCIAS)
def fijar_preferencias(
    datos: PreferenciasDeNotificacionCambio,
    activa: Persona,
    instalacion: SesionInstalacionEscrituraDep,
) -> PreferenciasDeNotificacionRespuesta:
    """Enciende o apaga categorías de la cuenta actual; las que no nombra quedan como estaban."""
    try:
        lista = avisos_por_evento.fijar_preferencias(
            instalacion,
            activa.usuario_id,
            [(c.categoria, c.activa) for c in datos.categorias],
        )
    except PreferenciaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return _preferencias(lista)
