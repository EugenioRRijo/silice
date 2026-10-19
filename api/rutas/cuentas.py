"""`/v1/cuentas` y `/v1/accesos`: las pestañas Cuentas y Accesos de Administración (migración).

Paridad con `ui/paginas/administracion.py` (`_pestana_cuentas`, `_pestana_accesos`), acción
`ADMINISTRAR_CUENTAS`. Toda la lógica es de `seguridad.cuentas` (la misma que usa Streamlit): aquí
solo el esquema HTTP, y los mensajes de error son los suyos, sin traza. Ninguna de estas operaciones
es `Sensible` en Streamlit (no llaman a `exigir_local`), así que no llevan `exigir_equipo_propio`.

- Solo con sesión de administrador (CSRF y `Origin` en las escrituras): la clave de API da 403,
  porque las cuentas las firma una persona (`actor`) y la clave no es una persona.
- La contraseña temporal la escribe el administrador (como en Streamlit); entra en el cuerpo de la
  petición y **nunca** se devuelve, ni se registra, ni va en la URL. Los 422 de validación del
  cuerpo no repiten lo enviado. Toda respuesta lleva `Cache-Control: no-store`.
- Ninguna respuesta lleva huellas ni campos de credenciales: una cuenta es `{id, login, nombre,
  roles, activa}`.

Contrato (todas devuelven 401 sin sesión, 403 sin el rol o con clave de API o sin CSRF):

- `GET /v1/cuentas` → `{cuentas: [...por usuario], aviso_arma_y_revisa}`.
- `POST /v1/cuentas` `{login, nombre, roles, contrasena_temporal}` → 201 `{cuenta, mensaje, aviso}`.
- `POST /v1/cuentas/{id}/roles` `{roles}` → `{cuenta, mensaje, aviso}`.
- `POST /v1/cuentas/{id}/desactivar | reactivar | desbloquear` → `{cuenta, mensaje, aviso: null}`.
- `POST /v1/cuentas/{id}/restablecer` `{contrasena_temporal}` → `{cuenta, mensaje, aviso: null}`.
- `GET /v1/accesos?limite=200` → `{maximo, eventos: [{id, fecha_hora, tipo, usuario, ip,
  detalle}]}`, los más nuevos primero; solo lectura.

Errores: 404 cuenta inexistente, 422 política o validación (incluye «Debe quedar al menos un
administrador activo.»), 409 si la sesión no tiene cuenta, 503 si la base no abre.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.rutas.sesion import Detalle
from api.sesion_web import ahora, exigir_clave_o_sesion
from api.sin_eco import RutaSinEco, sin_eco
from operacion.base_datos import ErrorDeBase
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, eventos
from seguridad.modelo import Usuario
from seguridad.permisos import Accion, Rol, aviso_de_roles
from seguridad.sesiones import SesionActiva

MAXIMO_ACCESOS = 200  # «Los 200 últimos eventos de acceso» de Streamlit
MENSAJE_CUERPO = "Revise los datos enviados: usuario, nombre, roles y contraseña como texto."
MENSAJE_SIN_SESION_DE_CUENTA = (
    "Las cuentas se administran con la sesión de un administrador, no con la clave de API."
)
MENSAJE_SIN_CUENTA = (
    "El acceso está apagado: aquí se pueden ver las cuentas, pero crearlas o cambiarlas "
    "exige entrar con una cuenta de administrador."
)
ACCION = Accion.ADMINISTRAR_CUENTAS

ERRORES_ESPERADOS = (
    cuentas.ErrorDeAcceso,
    cuentas.ContrasenaInvalida,
    PermissionError,
    LookupError,
    ValueError,
)


class _RutaCuentas(RutaSinEco):
    """`RutaSinEco` (el 422 sin eco) y, además, `Cache-Control: no-store` en TODA respuesta de
    estas rutas, también en las de error (401, 403, 404, 409, 422, 503): el `HTTPException` se
    vuelve la misma respuesta `{"detalle": ...}` de la aplicación, con la cabecera."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejador(request: Request) -> Response:
            try:
                respuesta = await original(request)
            except HTTPException as error:
                respuesta = JSONResponse(
                    status_code=error.status_code,
                    content={"detalle": error.detail},
                    headers=error.headers,
                )
            respuesta.headers["Cache-Control"] = "no-store"
            return respuesta

        return manejador


# Las mutaciones se serializan por defensa en profundidad. La raíz del «último administrador» ya
# está corregida en `seguridad/cuentas.py`: `cambiar_roles` y `desactivar` toman el bloqueo de
# escritura con `BEGIN IMMEDIATE` antes de comprobar y escribir, así que la garantía es de la base
# y vale para varios procesos y para Streamlit. Este candado solo evita esperas innecesarias dentro
# de un proceso. Se libera siempre (`with`), también ante excepciones.
_CANDADO = threading.Lock()


def _administrador(
    activa: Annotated[SesionActiva | None, Depends(exigir_clave_o_sesion(ACCION))],
) -> SesionActiva:
    if activa is None:
        raise HTTPException(status_code=403, detail=MENSAJE_SIN_SESION_DE_CUENTA)
    return activa


Administrador = Annotated[SesionActiva, Depends(_administrador)]

router = APIRouter(tags=["cuentas"], route_class=_RutaCuentas)


class CuentaRespuesta(BaseModel):
    id: int
    login: str
    nombre: str
    roles: list[str]
    activa: bool


class CuentasRespuesta(BaseModel):
    cuentas: list[CuentaRespuesta]
    aviso_arma_y_revisa: str = Field(
        description="El aviso que Streamlit muestra al elegir `arma` y `revisa` a la vez"
    )


class CuentaNueva(BaseModel):
    login: str = Field(max_length=200)
    nombre: str = Field(max_length=200)
    roles: list[Rol] = Field(max_length=len(Rol) * 2)
    contrasena_temporal: str = Field(max_length=1024)


class NuevosRoles(BaseModel):
    roles: list[Rol] = Field(max_length=len(Rol) * 2)


class ContrasenaTemporal(BaseModel):
    contrasena_temporal: str = Field(max_length=1024)


class ResultadoRespuesta(BaseModel):
    cuenta: CuentaRespuesta
    mensaje: str
    aviso: str | None = None


class EventoRespuesta(BaseModel):
    id: int
    fecha_hora: str
    tipo: str
    usuario: str
    ip: str
    detalle: str


class AccesosRespuesta(BaseModel):
    maximo: int
    eventos: list[EventoRespuesta]


def _cuenta(usuario: Usuario) -> CuentaRespuesta:
    return CuentaRespuesta(
        id=usuario.id,
        login=usuario.login,
        nombre=usuario.nombre,
        roles=[r for r in usuario.roles.split(",") if r],
        activa=usuario.activo,
    )


def _estado(error: Exception) -> int:
    if isinstance(error, PermissionError):
        return 403
    if isinstance(error, LookupError):
        return 404
    return 422  # política de contraseñas, usuario inválido o repetido, último administrador


def _actuar(
    activa: SesionActiva,
    accion: Callable[[Session, Usuario], Usuario | None],
    exito: str,
    *,
    aviso: bool = False,
    usuario_id: int | None = None,
) -> ResultadoRespuesta:
    """Corre `accion(bd, actor)` como la sesión del administrador. El mensaje de un error esperado
    sale tal cual (sin traza); la cuenta resultante se lee de la base (nunca de la petición)."""
    try:
        with _CANDADO, sesion_de_instalacion() as bd:
            actor = bd.get(Usuario, activa.usuario_id)
            if actor is None:
                raise HTTPException(status_code=409, detail=MENSAJE_SIN_CUENTA)
            try:
                resultado = accion(bd, actor)
            except ErrorDeBase:
                raise  # hereda de ValueError: va antes que los errores esperados (503, no 422)
            except ERRORES_ESPERADOS as error:
                raise HTTPException(status_code=_estado(error), detail=str(error)) from None
            destino = resultado
            if destino is None:
                destino = bd.get(Usuario, usuario_id)
            bd.refresh(destino)
            roles = [Rol(r) for r in destino.roles.split(",") if r]
            return ResultadoRespuesta(
                cuenta=_cuenta(destino),
                mensaje=exito,
                aviso=aviso_de_roles(roles) if aviso else None,
            )
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


_RESPUESTAS = {
    403: {"model": Detalle, "description": "Sin sesión de administrador, CSRF u origen."},
    404: {"model": Detalle, "description": "No hay una cuenta con ese id."},
    409: {"model": Detalle, "description": "La sesión no tiene cuenta (acceso apagado)."},
    422: {"model": Detalle, "description": "Validación o regla de cuentas; sin eco del cuerpo."},
}


@router.get("/v1/cuentas", response_model=CuentasRespuesta)
def listar_cuentas(_: Administrador) -> CuentasRespuesta:
    """Las cuentas por usuario (la tabla de la pestaña Cuentas)."""
    try:
        with sesion_de_instalacion() as bd:
            filas = bd.scalars(select(Usuario).order_by(Usuario.login)).all()
            return CuentasRespuesta(
                cuentas=[_cuenta(u) for u in filas],
                aviso_arma_y_revisa=aviso_de_roles([Rol.ARMA, Rol.REVISA]) or "",
            )
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post(
    "/v1/cuentas", response_model=ResultadoRespuesta, status_code=201, responses=_RESPUESTAS
)
@sin_eco(MENSAJE_CUERPO)
def crear_cuenta(datos: CuentaNueva, activa: Administrador) -> ResultadoRespuesta:
    """Alta con contraseña temporal: la persona deberá cambiarla al entrar. La contraseña no se
    devuelve."""
    roles = list(datos.roles)

    def crear(bd: Session, actor: Usuario) -> Usuario:
        return cuentas.crear_usuario(
            bd, actor, datos.login, datos.nombre, roles, datos.contrasena_temporal, ahora()
        )

    return _actuar(
        activa,
        crear,
        "Cuenta creada. La persona deberá cambiar la contraseña al entrar.",
        aviso=True,
    )


@router.post(
    "/v1/cuentas/{usuario_id}/roles", response_model=ResultadoRespuesta, responses=_RESPUESTAS
)
@sin_eco(MENSAJE_CUERPO)
def cambiar_roles(usuario_id: int, datos: NuevosRoles, activa: Administrador) -> ResultadoRespuesta:
    roles = list(datos.roles)
    return _actuar(
        activa,
        lambda bd, actor: cuentas.cambiar_roles(bd, actor, usuario_id, roles, ahora()),
        "Roles cambiados; sus sesiones se cerraron.",
        aviso=True,
    )


@router.post(
    "/v1/cuentas/{usuario_id}/desactivar",
    response_model=ResultadoRespuesta,
    responses=_RESPUESTAS,
)
def desactivar_cuenta(usuario_id: int, activa: Administrador) -> ResultadoRespuesta:
    def desactivar(bd: Session, actor: Usuario) -> None:
        cuentas.desactivar(bd, actor, usuario_id, ahora())

    return _actuar(
        activa,
        desactivar,
        "Cuenta desactivada; sus registros se conservan.",
        usuario_id=usuario_id,
    )


@router.post(
    "/v1/cuentas/{usuario_id}/reactivar",
    response_model=ResultadoRespuesta,
    responses=_RESPUESTAS,
)
def reactivar_cuenta(usuario_id: int, activa: Administrador) -> ResultadoRespuesta:
    def reactivar(bd: Session, actor: Usuario) -> None:
        cuentas.reactivar(bd, actor, usuario_id, ahora())

    return _actuar(activa, reactivar, "Cuenta reactivada.", usuario_id=usuario_id)


@router.post(
    "/v1/cuentas/{usuario_id}/desbloquear",
    response_model=ResultadoRespuesta,
    responses=_RESPUESTAS,
)
def desbloquear_cuenta(usuario_id: int, activa: Administrador) -> ResultadoRespuesta:
    def desbloquear(bd: Session, actor: Usuario) -> None:
        elegida = bd.get(Usuario, usuario_id)
        if elegida is None:
            raise LookupError(f"no hay una cuenta con id {usuario_id}")
        cuentas.desbloquear(bd, actor, elegida.login, ahora())

    return _actuar(activa, desbloquear, "Cuenta desbloqueada.", usuario_id=usuario_id)


@router.post(
    "/v1/cuentas/{usuario_id}/restablecer",
    response_model=ResultadoRespuesta,
    responses=_RESPUESTAS,
)
@sin_eco(MENSAJE_CUERPO)
def restablecer_cuenta(
    usuario_id: int, datos: ContrasenaTemporal, activa: Administrador
) -> ResultadoRespuesta:
    """Contraseña temporal nueva (no se devuelve): cierra las sesiones de la cuenta."""

    def restablecer(bd: Session, actor: Usuario) -> None:
        cuentas.restablecer(bd, actor, usuario_id, datos.contrasena_temporal, ahora())

    return _actuar(
        activa,
        restablecer,
        "Contraseña restablecida; sus sesiones se cerraron.",
        usuario_id=usuario_id,
    )


@router.get("/v1/accesos", response_model=AccesosRespuesta)
def listar_accesos(
    _: Administrador,
    limite: Annotated[int, Query(ge=1, le=MAXIMO_ACCESOS)] = MAXIMO_ACCESOS,
) -> AccesosRespuesta:
    """Los últimos eventos de acceso, los más nuevos primero. Solo lectura: no hay otro método."""
    try:
        with sesion_de_instalacion() as bd:
            return AccesosRespuesta(
                maximo=MAXIMO_ACCESOS,
                eventos=[
                    EventoRespuesta(
                        id=e.id,
                        fecha_hora=e.fecha_hora.isoformat(sep=" "),
                        tipo=e.tipo,
                        usuario=e.login_intentado,
                        ip=e.ip_cliente,
                        detalle=e.detalle,
                    )
                    for e in eventos.ultimos(bd, limite)
                ],
            )
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
