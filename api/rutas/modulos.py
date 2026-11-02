"""`/v1/modulos`: especialidades y módulos activables por instalación (plan vial, Tarea 19).

- `GET /` → `{"modulos": [{clave, nombre, activo, cambiado_por, cambiado_el}]}`, los cuatro en el
  orden de `aplicacion.modulos.MODULOS`. Lo lee el marco para ocultar lo apagado: sesión de
  cualquier rol (o clave de API).
- `PUT /{clave}` `{"activo": bool}` → la misma lista, ya con el cambio. Solo el administrador
  (`Accion.ACTIVAR_MODULOS`), con cuenta: la clave de API no sirve. Una clave que no es de un
  módulo es 404; un cuerpo sin la forma esperada, 422.

Apagar un módulo no borra nada: es un registro nuevo (`modulo_cambio`, con quién y cuándo), y los
datos del módulo siguen en su base. Los routers de producción, vial y riesgo responden 404 con el
detalle de D-V-4 mientras estén apagados (`api.acceso_modulos`).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StrictBool

from api.acceso_modulos import CUALQUIER_ROL
from api.admin_acceso import administrar
from api.dependencias import SesionInstalacionDep
from api.sesion_web import ahora
from api.sin_cache import RutaSinCache
from aplicacion.modulos import MODULOS, EstadoDeModulo, estado_de_los_modulos, fijar_modulo
from seguridad.permisos import Accion
from seguridad.sesiones import SesionActiva

router = APIRouter(prefix="/v1/modulos", tags=["modulos"], route_class=RutaSinCache)
ADMIN = Depends(administrar(Accion.ACTIVAR_MODULOS))

MENSAJE_SIN_MODULO = "No existe ese módulo: use producción, vial, edificación o riesgo."

__all__ = ["MENSAJE_SIN_MODULO", "router"]


class EspecialidadRespuesta(BaseModel):
    clave: str
    nombre: str
    activo: bool
    cambiado_por: str | None
    cambiado_el: str | None


class EspecialidadesRespuesta(BaseModel):
    modulos: list[EspecialidadRespuesta]


class CambioDeEspecialidad(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activo: StrictBool


def _respuesta(estados: list[EstadoDeModulo]) -> EspecialidadesRespuesta:
    return EspecialidadesRespuesta(
        modulos=[
            EspecialidadRespuesta(
                clave=e.clave,
                nombre=e.nombre,
                activo=e.activo,
                cambiado_por=e.cambiado_por,
                cambiado_el=None if e.cambiado_el is None else e.cambiado_el.isoformat(),
            )
            for e in estados
        ]
    )


@router.get("", response_model=EspecialidadesRespuesta, dependencies=[Depends(CUALQUIER_ROL)])
def ver(instalacion: SesionInstalacionDep) -> EspecialidadesRespuesta:
    """El estado de los cuatro módulos."""
    return _respuesta(estado_de_los_modulos(instalacion))


@router.put("/{clave}", response_model=EspecialidadesRespuesta)
def cambiar(
    clave: str,
    cuerpo: CambioDeEspecialidad,
    activa: Annotated[SesionActiva, ADMIN],
    instalacion: SesionInstalacionDep,
) -> EspecialidadesRespuesta:
    """Enciende o apaga un módulo (un registro nuevo; los datos del módulo no se tocan)."""
    if clave not in MODULOS:
        raise HTTPException(status_code=404, detail=MENSAJE_SIN_MODULO)
    fijar_modulo(instalacion, clave, cuerpo.activo, usuario=activa.login, ahora=ahora())
    return _respuesta(estado_de_los_modulos(instalacion))
