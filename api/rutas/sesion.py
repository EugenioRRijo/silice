"""`/v1/sesion`: entrar, consultar y salir desde el navegador (RT-9, RF-113; plan sesión 2, 2.3a).

Estas rutas **no** llevan la clave de API (`CON_CLAVE`): son la puerta de la interfaz nueva, que
no tiene secretos. Las protege lo mismo que a la interfaz clásica: `seguridad.cuentas.autenticar`
con su freno global, el bloqueo de 15 minutos tras cinco fallos y el mismo mensaje exista o no
el usuario; la IP del cliente queda en el registro de accesos.

- `POST` `{login, contrasena}` → 200 `{login, nombre, roles, csrf}` y la cookie de sesión;
  401 credenciales malas, 423 bloqueada, 403 si la cuenta debe cambiar su contraseña (sin cookie)
  o si un `Origin` presente no es el de la instalación (CSRF de acceso).
- `GET` → 200 con el mismo cuerpo, o 401 (y borra la cookie que ya no sirve).
- `DELETE` (exige CSRF y `Origin`) → 204, cierra la ficha y borra la cookie.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
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
from seguridad import cuentas, sesiones
from seguridad.permisos import Rol
from seguridad.sesiones import SesionActiva

router = APIRouter(prefix="/v1/sesion", tags=["sesion"])


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
        423: {"model": Detalle, "description": "Cuenta bloqueada por intentos fallidos."},
    },
)
def entrar(datos: Credenciales, request: Request, response: Response) -> SesionRespuesta:
    """Entra con la cuenta de la instalación y deja la cookie de sesión. No hay cookie si la
    cuenta debe cambiar su contraseña: eso se hace en la interfaz clásica."""
    if "origin" in request.headers and not origen_propio(request):
        raise HTTPException(status_code=403, detail=MENSAJE_ORIGEN)
    momento = ahora()
    try:
        with sesion_de_instalacion() as sesion:
            try:
                usuario = cuentas.autenticar(
                    sesion, datos.login, datos.contrasena, momento, ip=_ip(request)
                )
            except cuentas.CuentaBloqueada:
                raise HTTPException(status_code=423, detail=cuentas.MENSAJE_BLOQUEO) from None
            except cuentas.ErrorDeAcceso:
                raise HTTPException(status_code=401, detail=cuentas.MENSAJE_FALLO) from None
            if usuario.debe_cambiar_clave:
                raise HTTPException(status_code=403, detail=MENSAJE_CAMBIAR_CLAVE)
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
