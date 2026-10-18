"""`/v1/casos`: el caso de la sesión del navegador (RM-2, ola 0a de la sesión 2b).

- `GET /v1/casos` → `{actual: {nombre, ruta_relativa}, casos: [{nombre, ruta_relativa}]}`: el caso
  de esta petición (`api.dependencias.url_de_la_peticion`) y los `.db` de la carpeta de casos
  (`operacion.base_datos.listar_casos`). Lo ve cualquier rol con sesión, y la clave de API (que ve
  el caso del proceso). **Ninguna ruta absoluta**: `ruta_relativa` es relativa a la carpeta de
  datos (`casos/obra.db`); un caso del proceso fuera de ella (un `APU_BASE` de otra carpeta) solo
  muestra su nombre.
- `POST /v1/casos/actual` `{nombre}` (CSRF y `Origin`; `CAMBIAR_CASO`, como «Cambiar de caso» del
  Inicio, `ui.caso.abrir_caso`): el nombre pasa por `resolver_caso` (sin `..`, rutas, unidades ni
  nombres reservados: 422) y debe estar en `listar_casos` (404). El caso se prepara con
  `preparar_base` al abrir su motor (503 si no se puede, y no queda elegido) y se guarda para la
  ficha (`api.caso_web`). Con la clave de API, 409: las integraciones trabajan en el caso del
  proceso (`APU_BASE`), que fija quien arranca la API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api import caso_web
from api.acceso import CUALQUIER_ROL
from api.dependencias import obtener_motor, ruta_de_url, url_de_la_peticion, url_de_ruta
from api.rutas.sesion import Detalle
from api.sesion_web import exigir_clave_o_sesion
from operacion import config
from operacion.base_datos import RutaDeCasoRechazada, listar_casos, resolver_caso
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

MENSAJE_NO_ESTA = "El caso «{nombre}» no está en la carpeta de casos: elija uno de la lista."
MENSAJE_CON_CLAVE = (
    "Con la clave de API se trabaja en el caso del proceso (APU_BASE); el caso se elige por "
    "sesión desde la interfaz."
)

router = APIRouter(prefix="/v1/casos", tags=["casos"])


class CasoRespuesta(BaseModel):
    nombre: str
    ruta_relativa: str


class CasosRespuesta(BaseModel):
    actual: CasoRespuesta | None = Field(
        description="El caso de esta sesión; `null` solo si el proceso no usa un archivo SQLite"
    )
    casos: list[CasoRespuesta]


class EleccionCaso(BaseModel):
    nombre: str = Field(max_length=200, description="El nombre de un caso de la lista")


def _describir(ruta: Path) -> CasoRespuesta:
    """El nombre y la ruta relativa a la carpeta de datos; fuera de ella, solo el nombre."""
    try:
        relativa = ruta.resolve().relative_to(config.carpeta_datos().resolve()).as_posix()
    except ValueError:
        relativa = ruta.name
    return CasoRespuesta(nombre=ruta.name, ruta_relativa=relativa)


@router.get("", response_model=CasosRespuesta, dependencies=CUALQUIER_ROL)
def consultar_casos(request: Request) -> CasosRespuesta:
    """El caso de esta sesión y los de la carpeta de casos, por nombre. No abre ninguna base."""
    ruta = ruta_de_url(url_de_la_peticion(request))
    return CasosRespuesta(
        actual=None if ruta is None else _describir(ruta),
        casos=[_describir(caso) for caso in listar_casos()],
    )


@router.post(
    "/actual",
    response_model=CasoRespuesta,
    responses={
        403: {"model": Detalle, "description": "Sin `CAMBIAR_CASO`, o sin CSRF u origen propio."},
        404: {"model": Detalle, "description": "El caso no está en la carpeta de casos."},
        409: {"model": Detalle, "description": "Con la clave de API no se elige caso."},
        422: {"model": Detalle, "description": "El nombre lleva rutas, `..` o no es válido."},
        503: {"model": Detalle, "description": "El caso no se puede preparar (más nuevo...)."},
    },
)
def elegir_caso(
    datos: EleccionCaso,
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(Accion.CAMBIAR_CASO))],
) -> CasoRespuesta:
    """Fija el caso de esta ficha de sesión (lo olvida al salir o expirar)."""
    if activa is None:
        raise HTTPException(status_code=409, detail=MENSAJE_CON_CLAVE)
    try:
        ruta = resolver_caso(datos.nombre)
    except RutaDeCasoRechazada as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    if ruta not in {caso.resolve() for caso in listar_casos()}:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ESTA.format(nombre=ruta.name))
    obtener_motor(url_de_ruta(ruta))  # prepara la base una vez (503 si no se puede)
    caso_web.fijar(activa.huella_ficha, ruta)
    return _describir(ruta)
