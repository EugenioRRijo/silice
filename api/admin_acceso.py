"""Acceso de las rutas de Administración (`/v1/admin/*`): solo con la sesión de una cuenta.

Administrar la instalación es de una persona con rol, no de una integración: la clave de API pasa
`exigir_clave_o_sesion`, pero aquí se rechaza con 403 (una clave filtrada no puede crear otras
claves, cambiar la empresa ni bajar respaldos). Lo que toca un secreto exige además el propio equipo
(`exigir_equipo_propio`, RM-4). Quien llega trae su `SesionActiva`: su `login` firma los cambios.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request, Response

from api.sesion_web import exigir_clave_o_sesion, exigir_equipo_propio
from seguridad.permisos import Accion, Sensible
from seguridad.sesiones import SesionActiva

MENSAJE_SOLO_CUENTA = "Administrar la instalación exige entrar con una cuenta de administrador."


def sin_cache(response: Response) -> None:
    """Ninguna respuesta de Administracion se guarda en el navegador (huellas, etiquetas, rutas)."""
    response.headers["Cache-Control"] = "no-store"


def _solo_cuenta(
    base: Callable[[Request], SesionActiva | None], nombre: str
) -> Callable[[Request], SesionActiva]:
    def dependencia(request: Request) -> SesionActiva:
        activa = base(request)
        if activa is None:
            raise HTTPException(status_code=403, detail=MENSAJE_SOLO_CUENTA)
        return activa

    dependencia.__name__ = nombre
    return dependencia


def administrar(accion: Accion) -> Callable[[Request], SesionActiva]:
    """Sesión con el rol de `accion`; la clave de API no sirve."""
    return _solo_cuenta(exigir_clave_o_sesion(accion), f"administrar_{accion.value}")


def administrar_en_el_equipo(sensible: Sensible) -> Callable[[Request], SesionActiva]:
    """Como `administrar`, con el rol de lo sensible y desde el propio equipo (403 con motivo)."""
    return _solo_cuenta(
        exigir_equipo_propio(sensible), f"administrar_en_el_equipo_{sensible.value}"
    )
