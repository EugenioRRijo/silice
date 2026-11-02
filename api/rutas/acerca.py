"""`GET /v1/acerca`: versión, revisiones de las dos bases, carpeta de datos y módulos instalados
(ola 1 de la sesión 2b; paridad con la página «Acerca de Sílice», RF-99). Solo lee: no crea ni
migra nada. La lógica vive en `aplicacion.acerca` (RM-1), la misma que usa la página de Streamlit.

Acceso (RM-3): la clave de API o la sesión de **cualquier rol**, como la página de Streamlit
(`accion=None` en `ui/app.py`). Ruling de seguridad: la carpeta de datos es una ruta del servidor
(suele llevar el nombre de usuario del equipo) y esta API se alcanza desde otras PC de la red local;
`carpeta_datos` solo viaja al administrador (`Accion.CAMBIAR_CARPETA_DE_DATOS`) y a la clave de API
(una integración con la clave ya es de confianza de administración); quien arma o revisa recibe
`null`. Lo demás (versión, revisiones, módulos) no es sensible.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencias import VARIABLE_BASE, ruta_de_url, url_por_defecto
from api.sesion_web import exigir_clave_o_sesion
from aplicacion import acerca
from operacion.config import ruta_caso_por_defecto
from seguridad.permisos import Accion, permitido
from seguridad.sesiones import SesionActiva

router = APIRouter(tags=["acerca"])

_CUALQUIER_ROL = exigir_clave_o_sesion(None)


class ModuloRespuesta(BaseModel):
    nombre: str
    instalado: bool


class AcercaRespuesta(BaseModel):
    version: str
    semver: str
    revision_instalacion: str
    head_instalacion: str
    revision_caso: str
    head_caso: str
    #: Ruta del servidor; `None` para quien no administra (ver el ruling del módulo).
    carpeta_datos: str | None
    modulos: list[ModuloRespuesta]


def _ruta_del_caso() -> Path:
    """El caso del proceso: `APU_BASE` o el por defecto de la carpeta de datos."""
    url = os.environ.get(VARIABLE_BASE, "").strip() or url_por_defecto()
    return ruta_de_url(url) or ruta_caso_por_defecto()


@router.get("/v1/acerca", response_model=AcercaRespuesta)
def ver_acerca(
    activa: Annotated[SesionActiva | None, Depends(_CUALQUIER_ROL)],
) -> AcercaRespuesta:
    """Datos de «Acerca de»; sin crear ni migrar ninguna base. Con sesión, `carpeta_datos` solo
    para quien administra; con clave de API, siempre."""
    datos = acerca.datos_acerca(_ruta_del_caso())
    ve_la_carpeta = activa is None or permitido(activa.roles, Accion.CAMBIAR_CARPETA_DE_DATOS)
    return AcercaRespuesta(
        version=datos.version,
        semver=datos.semver,
        revision_instalacion=datos.revision_instalacion,
        head_instalacion=datos.head_instalacion,
        revision_caso=datos.revision_caso,
        head_caso=datos.head_caso,
        carpeta_datos=datos.carpeta_datos if ve_la_carpeta else None,
        modulos=[ModuloRespuesta(nombre=n, instalado=i) for n, i in datos.modulos],
    )
