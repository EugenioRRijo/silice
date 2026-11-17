"""Acceso de las rutas de Administración (`/v1/admin/*`): solo con la sesión de una cuenta.

Administrar la instalación es de una persona con rol, no de una integración: la clave de API pasa
`exigir_clave_o_sesion`, pero aquí se rechaza con 403 (una clave filtrada no puede crear otras
claves, cambiar la empresa ni bajar respaldos). Lo que toca un secreto exige además el propio equipo
(`exigir_equipo_propio`, RM-4). Quien llega trae su `SesionActiva`: su `login` firma los cambios.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request

from api.sesion_web import exigir_clave_o_sesion, exigir_equipo_propio
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from seguridad.permisos import Accion, Sensible
from seguridad.sesiones import SesionActiva

MENSAJE_SOLO_CUENTA = "Administrar la instalación exige entrar con una cuenta de administrador."


class RutaDeAdministracion(RutaSinCache, RutaSinEco):
    """Ninguna respuesta de Administracion se guarda en el navegador (huellas, etiquetas, rutas),
    tampoco un 401, un 403 o un 422: una dependencia que pusiera la cabecera solo alcanza a la
    respuesta de exito, porque el rechazo lo arma el manejador de `HTTPException` con una nueva.
    El orden importa: `RutaSinCache` envuelve a `RutaSinEco` (el 422 sin eco tambien sale con la
    cabecera)."""


def _solo_cuenta(
    base: Callable[[Request], SesionActiva | None],
    nombre: str,
    mensaje: str = MENSAJE_SOLO_CUENTA,
) -> Callable[[Request], SesionActiva]:
    def dependencia(request: Request) -> SesionActiva:
        activa = base(request)
        if activa is None:
            raise HTTPException(status_code=403, detail=mensaje)
        return activa

    dependencia.__name__ = nombre
    return dependencia


def cuenta_con(accion: Accion, mensaje: str) -> Callable[[Request], SesionActiva]:
    """Sesión con el rol de `accion` y la clave de API rechazada con 403 y `mensaje` (la hoja del
    proyecto, T10: «se edita y se guarda con una cuenta»). `administrar` es el caso particular con
    el mensaje de Administración."""
    return _solo_cuenta(exigir_clave_o_sesion(accion), f"cuenta_con_{accion.value}", mensaje)


def administrar(accion: Accion) -> Callable[[Request], SesionActiva]:
    """Sesión con el rol de `accion`; la clave de API no sirve."""
    return _solo_cuenta(exigir_clave_o_sesion(accion), f"administrar_{accion.value}")


def administrar_en_el_equipo(sensible: Sensible) -> Callable[[Request], SesionActiva]:
    """Como `administrar`, con el rol de lo sensible y desde el propio equipo (403 con motivo)."""
    return _solo_cuenta(
        exigir_equipo_propio(sensible), f"administrar_en_el_equipo_{sensible.value}"
    )
