"""`/v1/sesion`: entrar, consultar y salir desde el navegador (RT-9, RF-113; plan sesión 2, 2.3a).

Estas rutas **no** llevan la clave de API (`CON_CLAVE`): son la puerta de la interfaz nueva, que
no tiene secretos. Las protege lo mismo que a la interfaz clásica: `seguridad.cuentas.autenticar`
con su freno global, el bloqueo de 15 minutos tras cinco fallos y el mismo mensaje exista o no
el usuario; la IP del cliente queda en el registro de accesos.

- `POST` `{login, contrasena}` → 200 `{login, nombre, roles, csrf}` y la cookie de sesión;
  401 credenciales malas, 423 bloqueada, 403 si la cuenta debe cambiar su contraseña (sin cookie)
  o si un `Origin` presente no es el de la instalación (CSRF de acceso), 429 con `Retry-After`
  si el freno global pide esperar (RS2-11: la API no duerme en su hilo; el intento frenado no
  llega a verificar la contraseña) y 422 con un mensaje fijo, sin repetir lo enviado, si el
  cuerpo no es válido. Si el navegador trae la cookie de una ficha anterior, se cierra.
- `GET` → 200 con el mismo cuerpo, o 401 (y borra la cookie que ya no sirve).
- `DELETE` (exige CSRF y `Origin`) → 204, cierra la ficha y borra la cookie.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field

from api.sesion_web import (
    COOKIE,
    MENSAJE_CAMBIAR_CLAVE,
    MENSAJE_ORIGEN,
    MENSAJE_SIN_SESION,
    ahora,
    borrar_cookie,
    csrf_de,
    exigir_csrf_y_origen,
    origen_propio,
    poner_cookie,
    sesion_vigente,
)
from operacion.base_datos import ErrorDeBase
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, eventos, sesiones
from seguridad.permisos import Rol
from seguridad.sesiones import SesionActiva

MENSAJE_CUERPO_INVALIDO = (
    "Escriba el usuario y la contraseña como texto (la contraseña admite hasta "
    f"{cuentas.MAXIMO_CONTRASENA} caracteres)."
)
MENSAJE_FRENO = (
    "Demasiados intentos fallidos en este equipo. Espere unos segundos y vuelva a probar."
)


class _RutaSinEco(APIRoute):
    """El 422 de validación de estas rutas no repite lo enviado (la contraseña viajaría de
    vuelta en `input`): `{"detalle": <mensaje fijo>}`. El resto de la API conserva el de FastAPI."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejador(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError:
                return JSONResponse(status_code=422, content={"detalle": MENSAJE_CUERPO_INVALIDO})

        return manejador


router = APIRouter(prefix="/v1/sesion", tags=["sesion"], route_class=_RutaSinEco)


class _Frenado(Exception):  # noqa: N818
    """El freno global pidió esperar: la ruta responde 429 en vez de dormir en su hilo."""

    def __init__(self, segundos: float) -> None:
        super().__init__(segundos)
        self.segundos = segundos


def _no_dormir(segundos: float) -> None:
    """El `dormir` que la API pasa a `cuentas.autenticar` (RS2-11): no duerme, avisa."""
    raise _Frenado(segundos)


class Credenciales(BaseModel):
    login: str = Field(max_length=120)
    contrasena: str = Field(max_length=cuentas.MAXIMO_CONTRASENA)


class SesionRespuesta(BaseModel):
    login: str
    nombre: str
    roles: list[str]
    csrf: str


class Detalle(BaseModel):
    detalle: str


def _cuerpo(ficha: str, activa: SesionActiva) -> SesionRespuesta:
    return SesionRespuesta(
        login=activa.login,
        nombre=activa.nombre,
        roles=[rol.value for rol in Rol if rol in activa.roles],
        csrf=csrf_de(ficha),
    )


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post(
    "",
    response_model=SesionRespuesta,
    responses={
        401: {"model": Detalle, "description": "Usuario o contraseña incorrectos."},
        403: {"model": Detalle, "description": "Debe cambiar la contraseña, u origen ajeno."},
        422: {"model": Detalle, "description": "Cuerpo inválido (no repite lo enviado)."},
        423: {"model": Detalle, "description": "Cuenta bloqueada por intentos fallidos."},
        429: {"model": Detalle, "description": "Freno global: reintentar tras `Retry-After`."},
    },
)
def entrar(
    datos: Credenciales, request: Request, response: Response
) -> SesionRespuesta | JSONResponse:
    """Entra con la cuenta de la instalación y deja la cookie de sesión. No hay cookie si la
    cuenta debe cambiar su contraseña: eso se hace en la interfaz clásica."""
    if "origin" in request.headers and not origen_propio(request):
        raise HTTPException(status_code=403, detail=MENSAJE_ORIGEN)
    momento = ahora()
    try:
        with sesion_de_instalacion() as sesion:
            try:
                usuario = cuentas.autenticar(
                    sesion, datos.login, datos.contrasena, momento, ip=_ip(request),
                    dormir=_no_dormir,
                )
            except _Frenado as frenado:
                eventos.registrar(
                    sesion, "bloqueo", momento, ip=_ip(request), detalle="freno global",
                    login=cuentas.normalizar_login(datos.login)[:60],
                )
                sesion.commit()
                return JSONResponse(
                    status_code=429,
                    content={"detalle": MENSAJE_FRENO},
                    headers={"Retry-After": str(max(1, math.ceil(frenado.segundos)))},
                )
            except cuentas.CuentaBloqueada:
                raise HTTPException(status_code=423, detail=cuentas.MENSAJE_BLOQUEO) from None
            except cuentas.ErrorDeAcceso:
                raise HTTPException(status_code=401, detail=cuentas.MENSAJE_FALLO) from None
            if usuario.debe_cambiar_clave:
                raise HTTPException(status_code=403, detail=MENSAJE_CAMBIAR_CLAVE)
            anterior = request.cookies.get(COOKIE)
            if anterior:  # volver a entrar desde el mismo navegador cierra la ficha anterior
                sesiones.cerrar(sesion, anterior, "salida", momento)
            ficha = sesiones.abrir(sesion, usuario, momento)
            activa = sesiones.validar(sesion, ficha, momento)
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if activa is None:  # la cuenta cambió entre las dos lecturas: no hay sesión que dar
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    poner_cookie(response, ficha)
    return _cuerpo(ficha, activa)


@router.get(
    "",
    response_model=SesionRespuesta,
    responses={
        401: {"model": Detalle, "description": "Sin sesión vigente."},
        403: {"model": Detalle, "description": "La cuenta debe cambiar su contraseña."},
    },
)
def consultar(request: Request) -> SesionRespuesta | JSONResponse:
    """La sesión vigente del navegador, con su token anti-CSRF."""
    vigente = sesion_vigente(request)
    if vigente is None:
        respuesta = JSONResponse(status_code=401, content={"detalle": MENSAJE_SIN_SESION})
        if COOKIE in request.cookies:
            borrar_cookie(respuesta)
        return respuesta
    ficha, activa = vigente
    if activa.debe_cambiar_clave:
        raise HTTPException(status_code=403, detail=MENSAJE_CAMBIAR_CLAVE)
    return _cuerpo(ficha, activa)


@router.delete(
    "",
    status_code=204,
    response_class=Response,
    responses={
        401: {"model": Detalle, "description": "Sin sesión vigente."},
        403: {"model": Detalle, "description": "Falta el CSRF o el origen no es propio."},
    },
)
def salir(request: Request) -> Response:
    """Cierra la sesión del navegador (exige CSRF y `Origin`) y borra la cookie."""
    vigente = sesion_vigente(request)
    if vigente is None:
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    ficha, _ = vigente
    exigir_csrf_y_origen(request, ficha)
    try:
        with sesion_de_instalacion() as sesion:
            sesiones.cerrar(sesion, ficha, "salida", ahora())
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    respuesta = Response(status_code=204)
    borrar_cookie(respuesta)
    return respuesta
