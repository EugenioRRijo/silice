"""Acceso del navegador a la API por cuenta y cookie de sesión (RT-9; RS2-4, RS2-5, RS2-6).

La interfaz nueva (`/app`) no lleva secretos: la persona entra con su cuenta de la instalación
(`POST /v1/sesion`, `api.rutas.sesion`) y recibe la ficha de `seguridad.sesiones.abrir` en la
cookie `silice_sesion` (`HttpOnly`, `SameSite=Strict`, `Path=/`, de sesión). La clave de API
(`X-Silice-Clave`) sigue siendo para las integraciones.

Anti-CSRF sin migración (RS2-4): `csrf_de(ficha) = sha256("csrf:" + ficha)`, que la API recalcula
desde la cookie y entrega en el cuerpo de `POST/GET /v1/sesion`. Toda petición con cookie que no
sea GET ni HEAD exige ese valor en `X-Silice-CSRF` (comparado con `hmac.compare_digest`) y un
`Origin` igual a `http://<Host>`; sin `Origin`, 403. El `Host` ya lo filtra
`TrustedHostMiddleware` (`api.proteccion`).

Cookie sin `Secure` (RS2-6): la red local va por HTTP (`operacion/config.py`); se revisa en la
sesión 5. Nada de la ficha se registra ni viaja en un cuerpo JSON.

Ola 0a de la sesión 2b: la ficha de una cuenta con la contraseña temporal (`debe_cambiar_clave`)
es la «cookie restringida»: `exigir_sesion` (y con ella toda ruta protegida) la rechaza con 403
`MENSAJE_CAMBIAR_CLAVE`; solo sirven con ella `GET` y `DELETE /v1/sesion` y
`POST /v1/sesion/contrasena`, que no pasan por aquí. La restricción la lee `sesiones.validar` de la
base en cada petición: no hay una segunda cookie que robar. `exigir_clave_o_sesion(None)` acepta
cualquier rol (lo que todos ven, como la lista de casos); `exigir_equipo_propio` es RM-4.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from datetime import datetime

from fastapi import HTTPException, Request, Response

from api import caso_web
from api.proteccion import exigir_clave_api
from aplicacion import equipo
from operacion.base_datos import ErrorDeBase
from operacion.instalacion import sesion_de_instalacion
from seguridad import claves_api, sesiones
from seguridad.permisos import ROL_DE_LO_SENSIBLE, Accion, PermisoDenegado, Sensible, exigir
from seguridad.sesiones import SesionActiva

COOKIE = "silice_sesion"
CABECERA_CSRF = "X-Silice-CSRF"
METODOS_SEGUROS = frozenset({"GET", "HEAD"})
MENSAJE_SIN_SESION = "Sesión ausente o vencida: entre de nuevo con su cuenta."
MENSAJE_CSRF = "Falta la comprobación anti-CSRF de la sesión o no coincide."
MENSAJE_ORIGEN = "La petición no viene de la interfaz de esta instalación."
MENSAJE_CAMBIAR_CLAVE = "Su contraseña es temporal: elija una propia antes de seguir."


def csrf_de(ficha: str) -> str:
    """El token anti-CSRF de una ficha: `sha256("csrf:" + ficha)` en hexadecimal (RS2-4)."""
    return hashlib.sha256(b"csrf:" + ficha.encode("utf-8")).hexdigest()


def poner_cookie(respuesta: Response, ficha: str) -> None:
    """`silice_sesion` de sesión (sin `Max-Age`), `HttpOnly`, `SameSite=Strict`, sin `Secure`."""
    respuesta.set_cookie(COOKIE, ficha, path="/", httponly=True, samesite="strict", secure=False)


def borrar_cookie(respuesta: Response) -> None:
    respuesta.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict", secure=False)


def ahora() -> datetime:
    """El reloj de la sesión (el mismo reloj local que usa la interfaz clásica)."""
    return datetime.now()


def sesion_vigente(request: Request) -> tuple[str, SesionActiva] | None:
    """La ficha de la cookie y su sesión vigente, o `None` (sin cookie, cerrada o expirada:
    `sesiones.validar` cierra la expirada y aquí se olvida su caso). 503 si la base de la
    instalación no abre."""
    ficha = request.cookies.get(COOKIE)
    if not ficha:
        return None
    try:
        with sesion_de_instalacion() as sesion:
            activa = sesiones.validar(sesion, ficha, ahora())
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if activa is None:
        caso_web.olvidar(sesiones.huella_de(ficha))
        return None
    return ficha, activa


def exigir_sesion(request: Request) -> tuple[str, SesionActiva]:
    """401 sin sesión vigente; 403 si la cuenta debe cambiar su contraseña primero."""
    vigente = sesion_vigente(request)
    if vigente is None:
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    if vigente[1].debe_cambiar_clave:
        raise HTTPException(status_code=403, detail=MENSAJE_CAMBIAR_CLAVE)
    return vigente


def origen_propio(request: Request) -> bool:
    """True si `Origin` es `http://<Host>` (sin distinguir mayúsculas). Falso si falta."""
    origen = request.headers.get("origin")
    anfitrion = request.headers.get("host")
    return bool(origen and anfitrion) and origen.lower() == f"http://{anfitrion}".lower()


def exigir_csrf_y_origen(request: Request, ficha: str) -> None:
    """En todo método que no sea GET ni HEAD: `X-Silice-CSRF` correcto y `Origin` propio (403)."""
    if request.method in METODOS_SEGUROS:
        return
    presentado = request.headers.get(CABECERA_CSRF, "").encode("utf-8")
    if not hmac.compare_digest(presentado, csrf_de(ficha).encode("ascii")):
        raise HTTPException(status_code=403, detail=MENSAJE_CSRF)
    if not origen_propio(request):
        raise HTTPException(status_code=403, detail=MENSAJE_ORIGEN)


def exigir_clave_o_sesion(accion: Accion | None) -> Callable[[Request], SesionActiva | None]:
    """Dependencia de las rutas que usan la interfaz nueva y las integraciones (RS2-5, RM-3).

    Con la cabecera `X-Silice-Clave` (aunque venga vacía) se comporta como `exigir_clave_api`
    y no mira la cookie. Sin ella: cookie vigente (401), contraseña ya cambiada (403), CSRF y
    `Origin` en métodos que escriben (403) y un rol con `accion` (403; con `None`, cualquier
    rol). Devuelve la sesión del navegador, o `None` por clave.
    """

    def dependencia(request: Request) -> SesionActiva | None:
        if claves_api.CABECERA in request.headers:
            exigir_clave_api(request)
            return None
        ficha, activa = exigir_sesion(request)
        exigir_csrf_y_origen(request, ficha)
        if accion is not None:
            try:
                exigir(activa.roles, accion)
            except PermisoDenegado as error:
                raise HTTPException(status_code=403, detail=str(error)) from None
        return activa

    sufijo = "cualquier_rol" if accion is None else accion.value
    dependencia.__name__ = f"exigir_clave_o_sesion_{sufijo}"
    return dependencia


def exigir_equipo_propio(sensible: Sensible) -> Callable[[Request], SesionActiva | None]:
    """«Solo desde el propio equipo» (RM-4; S3 §5.6): `exigir_clave_o_sesion` con el rol de lo
    sensible (`ROL_DE_LO_SENSIBLE`) y, además, el criterio de `ui.sesion.exigir_local`
    (`aplicacion.equipo`) con la IP del par TCP (`request.client.host`): 403 con su motivo. La
    clave de API no exime del equipo. Un proxy local anula esta comprobación, como ya documenta
    `api.proteccion`."""
    por_rol = exigir_clave_o_sesion(ROL_DE_LO_SENSIBLE[sensible])

    def dependencia(request: Request) -> SesionActiva | None:
        activa = por_rol(request)
        ip = request.client.host if request.client else None
        permitida, motivo = equipo.operacion_sensible_permitida(ip)
        if not permitida:
            raise HTTPException(status_code=403, detail=motivo)
        return activa

    dependencia.__name__ = f"exigir_equipo_propio_{sensible.value}"
    return dependencia
