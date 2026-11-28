"""`/v1/obras/{codigo}/entrega`: la fecha de entrega al cliente de una obra (Lote G5; especificación
`docs/especificaciones/2026-11-26-notificaciones-por-evento.md` §4).

Rutas finas sobre `aplicacion.entrega_de_obra`, sobre la carpeta de trabajo de la petición:

- `GET /v1/obras/{codigo}/entrega` (`LEER_PROYECTO`: arma y revisa, o clave de API) →
  `{proyecto, fecha_entrega, actualizada, actualizada_por}`. `codigo` es el código de la obra (el
  `id` como texto, como en `GET /v1/proyectos` y `GET /v1/obras/resumen`) o su nombre.
- `PUT /v1/obras/{codigo}/entrega` (`EDITAR_HOJA`: arma, o clave de API) `{fecha_entrega}` →
  `{proyecto, fecha_entrega, actualizada, actualizada_por}`. `fecha_entrega` es opcional
  (`aaaa-mm-dd` o `null` para quitarla) y no puede estar en el pasado al fijarla (422). Va sobre la
  sesión de escritura (`BEGIN IMMEDIATE`). Cada cambio deja el evento «fecha de entrega» en el
  registro de accesos de la instalación (obra, valor anterior y nuevo, quién); se escribe después
  de la carpeta (orden caso→instalación) y se confirma antes que ella: no hay cambio sin rastro.

Toda respuesta lleva `Cache-Control: no-store` (`RutaSinCache`) y el 422 de forma no repite lo
enviado (`RutaSinEco`). Un fallo de la base devuelve 503 con un mensaje fijo.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from api.acceso import LEER
from api.dependencias import (
    USUARIO_API,
    SesionDeEscrituraDep,
    SesionDep,
    SesionInstalacionEscrituraDep,
    carpeta_de_la_peticion,
)
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion.entrega_de_obra import (
    EntregaDeLaObra,
    EntregaInvalida,
    ObraNoExiste,
    cambiar_entrega,
    leer_entrega,
    registrar_cambio,
)
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_FORMA = (
    "La fecha de entrega al cliente no es válida: indíquela como aaaa-mm-dd o déjela vacía."
)
MENSAJE_BASE = "No se pudo leer o guardar la fecha de entrega en la carpeta de trabajo."
_LARGO_OBRA = 200


class _RutaEntregaObra(RutaSinCache, RutaSinEco):
    """El orden importa: `RutaSinCache` envuelve a `RutaSinEco`."""

    mensaje_por_omision = MENSAJE_FORMA


router = APIRouter(prefix="/v1/obras", tags=["obras"], route_class=_RutaEntregaObra)
EDITAR_HOJA = Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))
CodigoObra = Annotated[str, Path(min_length=1, max_length=_LARGO_OBRA)]


class EntregaDeObraPeticion(BaseModel):
    fecha_entrega: date | None = Field(
        default=None,
        description="Fecha de entrega al cliente (aaaa-mm-dd), o null para quitarla",
    )


class EntregaDeObraRespuesta(BaseModel):
    proyecto: str = Field(description="El código de la obra")
    fecha_entrega: str | None = Field(
        description="La fecha de entrega al cliente (aaaa-mm-dd), o null si no tiene"
    )
    actualizada: str | None = Field(
        default=None,
        description="Cuándo se actualizó por última vez (ISO), o null",
    )
    actualizada_por: str | None = Field(
        default=None,
        description="Quién fijó o quitó la fecha, o null",
    )


def _a_respuesta(entrega: EntregaDeLaObra) -> EntregaDeObraRespuesta:
    return EntregaDeObraRespuesta(
        proyecto=entrega.proyecto_codigo,
        fecha_entrega=None if entrega.fecha_entrega is None else entrega.fecha_entrega.isoformat(),
        actualizada=None if entrega.actualizada is None else entrega.actualizada.isoformat(),
        actualizada_por=entrega.actualizada_por,
    )


@router.get("/{codigo}/entrega", response_model=EntregaDeObraRespuesta, dependencies=LEER)
def obtener_entrega_de_la_obra(sesion: SesionDep, codigo: CodigoObra) -> EntregaDeObraRespuesta:
    """Lee la fecha de entrega al cliente de la obra `codigo` en la carpeta abierta."""
    try:
        return _a_respuesta(leer_entrega(sesion, codigo))
    except ObraNoExiste as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE) from None


@router.put(
    "/{codigo}/entrega",
    response_model=EntregaDeObraRespuesta,
    dependencies=[EDITAR_HOJA],
)
def actualizar_entrega_de_la_obra(
    request: Request,
    sesion: SesionDeEscrituraDep,
    instalacion: SesionInstalacionEscrituraDep,
    codigo: CodigoObra,
    datos: EntregaDeObraPeticion,
    activa: Annotated[SesionActiva | None, EDITAR_HOJA],
) -> EntregaDeObraRespuesta:
    """Fija o quita (`null`) la fecha de entrega al cliente de la obra `codigo` y deja el rastro."""
    responsable = USUARIO_API if activa is None else activa.usuario
    momento = ahora()
    try:
        cambio = cambiar_entrega(
            sesion,
            codigo,
            datos.fecha_entrega,
            responsable=responsable,
            ahora=momento,
        )
        registrar_cambio(
            instalacion,
            cambio,
            carpeta=carpeta_de_la_peticion(request),
            login=USUARIO_API if activa is None else activa.login,
            usuario_id=None if activa is None else activa.usuario_id,
            ip=request.client.host if request.client else "",
            ahora=momento,
        )
        instalacion.commit()
        sesion.commit()
    except ObraNoExiste as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None
    except EntregaInvalida as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
    except SQLAlchemyError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE) from None
    return _a_respuesta(cambio.entrega)
