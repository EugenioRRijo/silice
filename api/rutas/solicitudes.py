"""`/v1/solicitudes`: el registro con código de 20 caracteres (C9a; spec
`2026-11-26-registro-con-codigo` §6).

Toda la lógica es de `seguridad.solicitudes`; aquí solo el esquema HTTP y la traducción de sus
errores. Toda respuesta lleva `Cache-Control: no-store` (también las de error: el código viaja una
vez) y los 422 de validación no repiten lo enviado (la contraseña y el código van en el cuerpo,
nunca en la URL ni en el registro). En las dos rutas públicas (`POST /v1/solicitudes` y
`POST /v1/solicitudes/canjear`), la puerta de `Origin` corre antes de leer el cuerpo
(`_PuertaPrevia`, como en `api.rutas.primer_arranque`): un `Origin` ajeno siempre responde 403,
nunca 422.

- `POST /v1/solicitudes` (cualquiera, sin sesión) `{nombre, correo, login, contrasena}` → 201
  `{mensaje}`; 403 con un `Origin` presente y ajeno (antes del cuerpo); 409 login en uso (de una
  cuenta o de una solicitud viva, sin decir cuál); 422 datos; 429 pasado el tope (5 por equipo en
  una hora, 50 pendientes).
- `GET /v1/solicitudes` (`administrar_cuentas`) → `{solicitudes: [{id, nombre, login, correo,
  creada, estado, papel, vence, reutilizada}]}`, las más nuevas primero; solo lectura (calcula
  `vencida` al responder sin escribir en la base).
- `POST /v1/solicitudes/{id}/aprobar` (`administrar_cuentas`) `{papel}` (`arma` o `revisa`) →
  `{codigo: "XXXX-XXXX-XXXX-XXXX-XXXX", vence, mailto}`: la única vez que viaja el código.
- `POST /v1/solicitudes/{id}/rechazar` (`administrar_cuentas`) → `{mensaje}`.
- `POST /v1/solicitudes/canjear` (cualquiera, sin sesión) `{login, contrasena, codigo}` → abre la
  sesión con `api.rutas.sesion.abrir_sesion_web`, la misma puerta de `POST /v1/sesion`: el mismo
  cuerpo, la misma cookie, 403 por `Origin` (antes del cuerpo), 423 bloqueada y 429 con
  `Retry-After`; 401 genérico (también si el aprobador fue revocado).

Las rutas del administrador: 401 sin sesión, 403 sin el rol, con clave de API o sin CSRF, 404 si
la solicitud no existe, 409 si ya se resolvió (rechazada o usada) o si su login ya es una cuenta,
422 con otro papel y 503 si la base no abre o está ocupada.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.rutas.cuentas import MENSAJE_SIN_CUENTA, Administrador
from api.rutas.sesion import Detalle, SesionRespuesta, abrir_sesion_web
from api.sesion_web import MENSAJE_ORIGEN, ahora, origen_propio
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco, sin_eco
from operacion.base_datos import ErrorDeBase
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, solicitudes
from seguridad.cuentas import Dormir
from seguridad.modelo import Usuario
from seguridad.sesiones import SesionActiva

MENSAJE_PEDIDO_INVALIDO = (
    "Escriba su nombre, su correo, su usuario y su contraseña como texto (la contraseña admite "
    f"hasta {cuentas.MAXIMO_CONTRASENA} caracteres)."
)
MENSAJE_PAPEL_INVALIDO = "Indique el papel como texto: arma o revisa."
MENSAJE_CANJE_INVALIDO = (
    "Escriba su usuario, su contraseña y el código como texto (la contraseña admite hasta "
    f"{cuentas.MAXIMO_CONTRASENA} caracteres)."
)

_RUTAS_PUBLICAS = frozenset({"/v1/solicitudes", "/v1/solicitudes/canjear"})


class _PuertaPrevia(APIRoute):
    """Comprueba `Origin` antes de leer el cuerpo en `POST /v1/solicitudes` y
    `POST /v1/solicitudes/canjear`: un cuerpo inválido o JSON roto con `Origin` ajeno responde
    403, nunca 422."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()
        if "POST" not in self.methods or self.path not in _RUTAS_PUBLICAS:
            return original

        async def manejador(request: Request) -> Response:
            if (
                request.method == "POST"
                and "origin" in request.headers
                and not origen_propio(request)
            ):
                raise HTTPException(status_code=403, detail=MENSAJE_ORIGEN)
            return await original(request)

        return manejador


class _RutaSolicitudes(RutaSinCache, _PuertaPrevia, RutaSinEco):
    """De fuera adentro: `no-store` en todo (también en errores), puerta de `Origin` antes del
    cuerpo en las rutas públicas, 422 sin eco y la ruta."""


router = APIRouter(tags=["solicitudes"], route_class=_RutaSolicitudes)


class SolicitudNueva(BaseModel):
    nombre: str = Field(max_length=200)
    correo: str = Field(max_length=300)
    login: str = Field(max_length=120)
    contrasena: str = Field(max_length=cuentas.MAXIMO_CONTRASENA)


class Mensaje(BaseModel):
    mensaje: str


class SolicitudRespuesta(BaseModel):
    id: int
    nombre: str
    login: str
    correo: str
    creada: datetime
    estado: str = Field(description="pendiente, aprobada, rechazada, usada o vencida")
    papel: str | None = Field(description="arma o revisa; lo fija el administrador al aprobar")
    vence: datetime | None = Field(description="Cuándo deja de valer el código de una aprobada")
    reutilizada: bool = Field(
        description="True si este usuario ya se había pedido antes y se rechazó o venció"
    )


class SolicitudesRespuesta(BaseModel):
    solicitudes: list[SolicitudRespuesta]


class Papel(BaseModel):
    papel: str = Field(max_length=20, description="arma (arma presupuestos) o revisa")


class AprobacionRespuesta(BaseModel):
    codigo: str = Field(description="XXXX-XXXX-XXXX-XXXX-XXXX; solo viaja en esta respuesta")
    vence: datetime
    mailto: str = Field(description="Enlace para el programa de correo del equipo")


class Canje(BaseModel):
    login: str = Field(max_length=120)
    contrasena: str = Field(max_length=cuentas.MAXIMO_CONTRASENA)
    codigo: str = Field(max_length=200)


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _fila(solicitud: solicitudes.SolicitudListada) -> SolicitudRespuesta:
    return SolicitudRespuesta(
        id=solicitud.id,
        nombre=solicitud.nombre,
        login=solicitud.login,
        correo=solicitud.correo,
        creada=solicitud.creada,
        estado=solicitud.estado,
        papel=solicitud.papel,
        vence=solicitud.vence,
        reutilizada=solicitud.reutilizada,
    )


def _estado(error: ValueError | LookupError | PermissionError) -> int:
    if isinstance(error, PermissionError):
        return 403
    if isinstance(error, LookupError):
        return 404
    if isinstance(error, solicitudes.LoginEnUso | solicitudes.SolicitudResuelta):
        return 409
    if isinstance(error, solicitudes.DemasiadasSolicitudes):
        return 429
    return 422


def _en_la_instalacion[Resultado](hacer: Callable[[Session], Resultado]) -> Resultado:
    """Corre `hacer(bd)` en la base de la instalación: los errores esperados salen con su
    mensaje y su código (`_estado`), sin traza; 503 si la base no abre o está ocupada."""
    try:
        with sesion_de_instalacion() as bd:
            try:
                return hacer(bd)
            except (ErrorDeBase, cuentas.BaseOcupada):
                raise  # heredan de ValueError: 503, no 422
            except (ValueError, LookupError, PermissionError) as error:
                raise HTTPException(status_code=_estado(error), detail=str(error)) from None
    except (ErrorDeBase, cuentas.BaseOcupada) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def _como_administrador[Resultado](
    activa: SesionActiva, hacer: Callable[[Session, Usuario], Resultado]
) -> Resultado:
    """`hacer(bd, actor)` con la cuenta de la sesión como actor; 409 si la sesión no la tiene."""

    def con_actor(bd: Session) -> Resultado:
        actor = cuentas.cuenta_por_id(bd, activa.usuario_id)
        if actor is None:
            raise HTTPException(status_code=409, detail=MENSAJE_SIN_CUENTA)
        return hacer(bd, actor)

    return _en_la_instalacion(con_actor)


_DE_ADMINISTRADOR = {
    403: {"model": Detalle, "description": "Sin sesión de administrador, CSRF u origen."},
    404: {"model": Detalle, "description": "No hay una solicitud con ese id."},
    409: {"model": Detalle, "description": "Ya se resolvió, o su usuario ya es una cuenta."},
    422: {"model": Detalle, "description": "Papel distinto de arma o revisa; sin eco."},
}


@router.post(
    "/v1/solicitudes",
    response_model=Mensaje,
    status_code=201,
    responses={
        403: {"model": Detalle, "description": "Un `Origin` presente y ajeno."},
        409: {"model": Detalle, "description": "El usuario ya está en uso."},
        422: {"model": Detalle, "description": "Datos inválidos (no repite lo enviado)."},
        429: {"model": Detalle, "description": "Demasiadas solicitudes pendientes."},
    },
)
@sin_eco(MENSAJE_PEDIDO_INVALIDO)
def pedir_cuenta(datos: SolicitudNueva, request: Request) -> Mensaje:
    """Pide una cuenta: guarda una solicitud (no una cuenta) que el administrador aprobará."""

    def pedir(bd: Session) -> Mensaje:
        solicitudes.solicitar(
            bd, datos.nombre, datos.correo, datos.login, datos.contrasena, ahora(), ip=_ip(request)
        )
        return Mensaje(mensaje=solicitudes.MENSAJE_RECIBIDA)

    return _en_la_instalacion(pedir)


@router.get("/v1/solicitudes", response_model=SolicitudesRespuesta)
def listar_solicitudes(activa: Administrador) -> SolicitudesRespuesta:
    """Las solicitudes, las más nuevas primero (solo lectura; `vencida` se calcula al responder)."""
    return _como_administrador(
        activa,
        lambda bd, actor: SolicitudesRespuesta(
            solicitudes=[_fila(s) for s in solicitudes.listar(bd, actor, ahora())]
        ),
    )


@router.post(
    "/v1/solicitudes/{solicitud_id}/aprobar",
    response_model=AprobacionRespuesta,
    responses=_DE_ADMINISTRADOR,
)
@sin_eco(MENSAJE_PAPEL_INVALIDO)
def aprobar_solicitud(
    solicitud_id: int, datos: Papel, activa: Administrador
) -> AprobacionRespuesta:
    """Aprueba con el papel elegido y devuelve el código, la única vez que viaja."""

    def aprobar(bd: Session, actor: Usuario) -> AprobacionRespuesta:
        aprobacion = solicitudes.aprobar(bd, actor, solicitud_id, datos.papel, ahora())
        return AprobacionRespuesta(
            codigo=aprobacion.codigo, vence=aprobacion.vence, mailto=aprobacion.mailto
        )

    return _como_administrador(activa, aprobar)


@router.post(
    "/v1/solicitudes/{solicitud_id}/rechazar",
    response_model=Mensaje,
    responses=_DE_ADMINISTRADOR,
)
def rechazar_solicitud(solicitud_id: int, activa: Administrador) -> Mensaje:
    def rechazar(bd: Session, actor: Usuario) -> Mensaje:
        solicitudes.rechazar(bd, actor, solicitud_id, ahora())
        return Mensaje(mensaje=solicitudes.MENSAJE_RECHAZADA)

    return _como_administrador(activa, rechazar)


@router.post(
    "/v1/solicitudes/canjear",
    response_model=SesionRespuesta,
    responses={
        401: {"model": Detalle, "description": "Usuario, contraseña o código no válidos."},
        403: {"model": Detalle, "description": "Un `Origin` presente y ajeno."},
        422: {"model": Detalle, "description": "Cuerpo inválido (no repite lo enviado)."},
        423: {"model": Detalle, "description": "Usuario bloqueado por intentos fallidos."},
        429: {"model": Detalle, "description": "Freno global: reintentar tras `Retry-After`."},
    },
)
@sin_eco(MENSAJE_CANJE_INVALIDO)
def canjear_codigo(
    datos: Canje, request: Request, response: Response
) -> SesionRespuesta | JSONResponse:
    """Canjea el código: crea la cuenta con su papel y abre la sesión como `POST /v1/sesion`."""

    def verificar(bd: Session, momento: datetime, ip: str, dormir: Dormir) -> Usuario:
        return solicitudes.canjear(
            bd, datos.login, datos.contrasena, datos.codigo, momento, ip=ip, dormir=dormir
        )

    return abrir_sesion_web(request, response, datos.login, verificar)
