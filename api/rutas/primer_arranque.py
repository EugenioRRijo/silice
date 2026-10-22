"""`/v1/primer-arranque`: el primer administrador de una instalación nueva (BCP-1; diseño §3).

Dos rutas **públicas** (sin clave de API ni cookie), pero solo para el propio equipo:

- `GET` → `{sin_cuentas, archivo_presente, modo, politica}`. Nada más: sin nombres ni rutas, sin
  el código ni su huella. No escribe (el código se emite al arrancar, nunca desde una petición).
- `POST /reclamo` `{codigo, usuario, nombre, contrasena, tambien_arma}` → 201 con el mismo cuerpo
  que `POST /v1/sesion` y la cookie de sesión.

La puerta (`Origin` propio y presente, solo en el `POST`; propio equipo en las dos) corre en la ruta
**antes de leer el cuerpo**: un cuerpo inválido, vacío o con JSON roto nunca da 422 a quien no pasa
(403). Después, en este orden: forma del cuerpo (422 fijo), forma del usuario y de la contraseña
(422 con el texto de la política, **antes de mirar el código**: un código bueno y uno malo con datos
mal formados responden igual, y ninguno gasta un intento) y el reclamo, con el mismo freno global y
bloqueo de 5 fallos que el acceso (429 con `Retry-After`, 423, 401 con un solo texto para código
errado, usado, caducado o inexistente, 503 si la base está ocupada). El código ni la contraseña se
registran, se devuelven ni se imprimen; el 422 no repite lo enviado. Todas las respuestas, también
las de error, llevan `Cache-Control: no-store`.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool

from api import caso_web
from api.esquemas_bienvenida import (
    PoliticaDeContrasena,
    PrimerArranqueRespuesta,
    ReclamoDeInstalacion,
)
from api.rutas.sesion import (
    MENSAJE_FRENO,
    Detalle,
    SesionRespuesta,
    _cuerpo,
    _Frenado,
    _no_dormir,
)
from api.sesion_web import (
    COOKIE,
    MENSAJE_ORIGEN,
    MENSAJE_SIN_SESION,
    ahora,
    origen_propio,
    poner_cookie,
)
from api.sin_cache import RutaSinCache
from api.sin_eco import RutaSinEco
from aplicacion import equipo
from operacion import config, primer_arranque
from operacion.base_datos import ErrorDeBase
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, eventos, sesiones

MENSAJE_CUERPO = (
    "Escriba el código, el usuario, el nombre y la contraseña como texto (la contraseña admite "
    f"hasta {cuentas.MAXIMO_CONTRASENA} caracteres)."
)
MENSAJE_BASE = "No se pudo abrir la base de la instalación: avise al administrador del equipo."

_registro = logging.getLogger("silice.api")


def _es_el_propio_equipo(request: Request) -> bool:
    return equipo.ip_es_local(request.client.host if request.client else None)


async def _exigir_puerta(request: Request) -> None:
    """403 si no es el propio equipo y, en el `POST`, si falta `Origin` o no es propio. El `Origin`
    se mira primero: una página ajena en el navegador de la persona no puede falsificarlo."""
    if request.method == "POST" and not origen_propio(request):
        raise HTTPException(status_code=403, detail=MENSAJE_ORIGEN)
    if not await run_in_threadpool(_es_el_propio_equipo, request):
        raise HTTPException(status_code=403, detail=equipo.MENSAJE_REMOTO)


class _PuertaPrevia(APIRoute):
    """La puerta corre antes de leer el cuerpo (FastAPI lo lee antes de resolver dependencias)."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejador(request: Request) -> Response:
            await _exigir_puerta(request)
            return await original(request)

        return manejador


class _RutaPrimerArranque(RutaSinCache, _PuertaPrevia, RutaSinEco):
    """De fuera adentro: `no-store` en todo, la puerta, el 422 sin eco, la ruta."""

    mensaje_por_omision = MENSAJE_CUERPO


router = APIRouter(
    prefix="/v1/primer-arranque", tags=["primer-arranque"], route_class=_RutaPrimerArranque
)


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.get(
    "",
    response_model=PrimerArranqueRespuesta,
    responses={
        403: {"model": Detalle, "description": "No es el propio equipo."},
        503: {"model": Detalle, "description": "La base de la instalación no abre."},
    },
)
def estado_del_primer_arranque() -> PrimerArranqueRespuesta:
    """Lo que la bienvenida puede saber antes de entrar. Solo desde el propio equipo; no escribe."""
    try:
        with sesion_de_instalacion() as sesion:
            actual = primer_arranque.estado(sesion, config.carpeta_datos())
    except ErrorDeBase:
        _registro.exception("no se pudo leer el estado del primer arranque")
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    return PrimerArranqueRespuesta(
        sin_cuentas=actual.sin_cuentas,
        archivo_presente=actual.archivo_presente,
        modo=actual.modo,  # type: ignore[arg-type]
        politica=PoliticaDeContrasena(
            minimo=cuentas.MINIMO_CONTRASENA, maximo=cuentas.MAXIMO_CONTRASENA
        ),
    )


@router.post(
    "/reclamo",
    status_code=201,
    response_model=SesionRespuesta,
    responses={
        401: {"model": Detalle, "description": "Código no válido, usado o caducado."},
        403: {"model": Detalle, "description": "Sin `Origin` propio, o no es el propio equipo."},
        422: {
            "model": Detalle,
            "description": "Cuerpo inválido o contraseña fuera de la política.",
        },
        423: {"model": Detalle, "description": "Cinco códigos errados: bloqueado 15 minutos."},
        429: {"model": Detalle, "description": "Freno global: reintentar tras `Retry-After`."},
        503: {"model": Detalle, "description": "La base de la instalación está ocupada."},
    },
)
def reclamar(
    datos: ReclamoDeInstalacion, request: Request, response: Response
) -> SesionRespuesta | JSONResponse:
    """Canjea el código: crea el primer administrador (o devuelve el acceso con un código de
    restablecimiento) y abre su sesión."""
    try:  # la forma ANTES que el código: no distingue un código bueno de uno malo
        login = cuentas.validar_login(datos.usuario)
        cuentas.validar_contrasena(datos.contrasena, login)
    except ValueError as error:  # `ContrasenaInvalida` también lo es: texto de la política
        raise HTTPException(status_code=422, detail=str(error)) from None
    momento = ahora()
    try:
        with sesion_de_instalacion() as sesion:
            try:
                usuario = cuentas.reclamar_instalacion(
                    sesion,
                    datos.codigo,
                    login,
                    datos.nombre,
                    datos.contrasena,
                    momento,
                    config.carpeta_datos(),
                    ip=_ip(request),
                    dormir=_no_dormir,
                    ademas_arma=datos.tambien_arma,
                )
            except _Frenado as frenado:
                eventos.registrar(
                    sesion,
                    "bloqueo",
                    momento,
                    login="(codigo)",
                    ip=_ip(request),
                    detalle="freno global",
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
                raise HTTPException(status_code=401, detail=cuentas.MENSAJE_CODIGO) from None
            except ValueError as error:
                if str(error) != cuentas.MENSAJE_BASE_OCUPADA:
                    raise
                raise HTTPException(status_code=503, detail=cuentas.MENSAJE_BASE_OCUPADA) from None
            anterior = request.cookies.get(COOKIE)
            if anterior:  # la ficha que traía el navegador se cierra (puede ser de otra persona)
                sesiones.cerrar(sesion, anterior, "salida", momento)
                caso_web.olvidar(sesiones.huella_de(anterior))
            ficha = sesiones.abrir(sesion, usuario, momento)
            activa = sesiones.validar(sesion, ficha, momento)
    except ErrorDeBase:
        _registro.exception("no se pudo abrir la base de la instalación en el primer arranque")
        raise HTTPException(status_code=503, detail=MENSAJE_BASE) from None
    if activa is None:  # la cuenta cambió entre las dos lecturas: no hay sesión que dar
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    poner_cookie(response, ficha)
    return _cuerpo(ficha, activa)
