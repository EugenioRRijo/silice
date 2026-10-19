"""Administración, pestaña «Claves de API» (UC-21; RF-98; RM-3 y RM-4).

Paridad con `_pestana_api` de `ui/paginas/administracion.py`, sobre `seguridad.claves_api`:

- `GET /v1/admin/claves-api` → `[{id, etiqueta, nombre, estado, ultimo_uso}]`; nunca el secreto.
- `POST /v1/admin/claves-api` `{nombre}` → `{id, etiqueta, secreto}`: el secreto se muestra **una
  vez** (`Cache-Control: no-store`), no se guarda en claro ni se registra.
- `POST /v1/admin/claves-api/{id}/revocar`.

Rol: `ADMINISTRAR_RED_Y_API`, solo con sesión; crear y revocar exigen además el propio equipo
(`Sensible.CLAVE_DE_API`).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select

from api.admin_acceso import administrar, administrar_en_el_equipo, sin_cache
from api.sesion_web import ahora
from api.sin_eco import RutaSinEco as _RutaSinEco
from api.sin_eco import sin_eco as _sin_eco
from operacion.instalacion import sesion_de_instalacion
from seguridad import claves_api
from seguridad.modelo import ClaveApi
from seguridad.permisos import Accion, Sensible
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = "Indique para qué es la clave como texto."

router = APIRouter(
    prefix="/v1/admin/claves-api",
    tags=["administracion"],
    dependencies=[Depends(sin_cache)],
    route_class=_RutaSinEco,
)
ADMIN = Depends(administrar(Accion.ADMINISTRAR_RED_Y_API))
EN_EL_EQUIPO = Depends(administrar_en_el_equipo(Sensible.CLAVE_DE_API))


class ClaveRespuesta(BaseModel):
    id: int
    etiqueta: str
    nombre: str
    estado: str
    ultimo_uso: str | None


class ClaveCreada(BaseModel):
    id: int
    etiqueta: str
    secreto: str


class NuevaClave(BaseModel):
    nombre: str


def _fila(clave: ClaveApi) -> ClaveRespuesta:
    return ClaveRespuesta(
        id=clave.id,
        etiqueta=claves_api.etiqueta(clave),
        nombre=clave.nombre,
        estado="revocada" if clave.revocada else "vigente",
        ultimo_uso=clave.ultimo_uso.isoformat(sep=" ") if clave.ultimo_uso else None,
    )


@router.get("", response_model=list[ClaveRespuesta], dependencies=[ADMIN])
def listar() -> list[ClaveRespuesta]:
    with sesion_de_instalacion() as bd:
        return [_fila(c) for c in bd.scalars(select(ClaveApi).order_by(ClaveApi.id))]


@router.post("", response_model=ClaveCreada)
@_sin_eco(MENSAJE_CUERPO_INVALIDO)
def crear(
    datos: NuevaClave, response: Response, activa: Annotated[SesionActiva, EN_EL_EQUIPO]
) -> ClaveCreada:
    """Crea la clave; el secreto sale aquí y no se vuelve a poder leer."""
    response.headers["Cache-Control"] = "no-store"
    with sesion_de_instalacion() as bd:
        try:
            secreto, fila = claves_api.crear(bd, datos.nombre, activa.login, ahora())
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        return ClaveCreada(id=fila.id, etiqueta=claves_api.etiqueta(fila), secreto=secreto)


@router.post("/{clave_id}/revocar", response_model=ClaveRespuesta)
def revocar(clave_id: int, activa: Annotated[SesionActiva, EN_EL_EQUIPO]) -> ClaveRespuesta:
    with sesion_de_instalacion() as bd:
        try:
            claves_api.revocar(bd, clave_id, activa.login, ahora())
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from None
        return _fila(bd.get(ClaveApi, clave_id))  # type: ignore[arg-type]
