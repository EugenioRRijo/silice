"""Protección de la API en el producto (RF-98; spec S5 §8.3).

Cuatro capas, ninguna sustituye a la otra: (1) la clave de acceso en cada ruta (**el control**),
(2) `TrustedHostMiddleware` contra el *DNS rebinding* (un `Host` ajeno da 400), (3) un filtro que
responde 403 a quien no llega desde el bucle local ni desde una red privada (defensa adicional al
cortafuegos: un túnel o proxy local anula esta capa y la regla «solo desde este equipo») y (4) un
tope de 20 MiB al cuerpo de la petición (413, sin leerlo entero).

La clave viaja en la cabecera `X-Silice-Clave: <identificador>.<secreto>` y se comprueba con
`seguridad.claves_api` contra `instalacion.db`. `exigir_clave_api` vive aquí, y no en el
`api/seguridad.py` que describe el plan de S3-4, para no pisar ese archivo: cuando S3-4 se
fusione, sus rutas pueden usar cualquiera de las dos y la clave sigue siendo la misma.
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from operacion.base_datos import ErrorDeBase
from operacion.instalacion import sesion_de_instalacion
from seguridad import claves_api, eventos

VARIABLE_DIRECCION = "SILICE_DIRECCION"
VARIABLE_PRODUCTO = "SILICE_PRODUCTO"
ANFITRIONES_BASE = ("127.0.0.1", "localhost")
LIMITE_CUERPO = 20 * 1024 * 1024  # 20 971 520 B; con un byte más, 413
MENSAJE_SIN_CLAVE = "Clave de API ausente, desconocida o revocada."


def en_producto(entorno: Mapping[str, str] | None = None) -> bool:
    return (os.environ if entorno is None else entorno).get(VARIABLE_PRODUCTO) == "1"


def opciones_documentacion(entorno: Mapping[str, str] | None = None) -> dict[str, None]:
    """En el producto no se publican `/docs`, `/redoc` ni `/openapi.json` (el esquema sigue
    exportado en `docs/api.json`)."""
    if en_producto(entorno):
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


def anfitriones_permitidos(direccion: str | None) -> list[str]:
    hosts = list(ANFITRIONES_BASE)
    try:
        ip = ipaddress.ip_address(direccion or "")
    except ValueError:
        return hosts
    if ip.version == 4 and ip.is_private and not ip.is_unspecified and str(ip) not in hosts:
        hosts.append(str(ip))
    return hosts


def ip_permitida(host: str | None) -> bool:
    try:
        ip = ipaddress.ip_address(host or "")
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback or ip.is_private


def exigir_clave_api(request: Request) -> None:
    """Dependencia de toda ruta menos `/salud`: sin clave vigente, 401 con `{"detalle": ...}`.
    El mismo mensaje para clave ausente, mal formada, desconocida o revocada."""
    presentada = request.headers.get(claves_api.CABECERA)
    ahora = datetime.now()
    try:
        with sesion_de_instalacion() as sesion:
            if claves_api.verificar(sesion, presentada, ahora) is not None:
                return
            eventos.registrar(
                sesion,
                "fallo",
                ahora,
                login="(api)",
                ip=request.client.host if request.client else "",
                detalle="clave de api",
            )
            sesion.commit()
    except ErrorDeBase as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    raise HTTPException(status_code=401, detail=MENSAJE_SIN_CLAVE)


class SoloRedesPrivadas:
    """Middleware ASGI: 403 (o cierre del websocket) a quien no es de bucle local ni privada."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            cliente = scope.get("client")
            if not ip_permitida(cliente[0] if cliente else None):
                if scope["type"] == "http":
                    respuesta = JSONResponse(
                        {"detalle": "Acceso denegado: Sílice solo atiende a la red local."},
                        status_code=403,
                    )
                    await respuesta(scope, receive, send)
                else:
                    await send({"type": "websocket.close", "code": 1008})
                return
        await self.app(scope, receive, send)


class _CuerpoExcedido(Exception):  # noqa: N818
    pass


class LimiteDeCuerpo:
    """Middleware ASGI puro: 413 sin leer el cuerpo entero. Mira `Content-Length` y, si falta o
    miente, cuenta los bytes a medida que llegan."""

    def __init__(self, app: ASGIApp, limite: int = LIMITE_CUERPO) -> None:
        self.app = app
        self.limite = limite

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declarado = dict(scope["headers"]).get(b"content-length")
        if declarado is not None and declarado.isdigit() and int(declarado) > self.limite:
            await self._rechazar(send)
            return
        total = 0
        empezo = False
        excedido = False

        async def recibir() -> Message:
            nonlocal total, excedido
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                total += len(mensaje.get("body", b""))
                if total > self.limite:
                    excedido = True
                    raise _CuerpoExcedido
            return mensaje

        async def enviar(mensaje: Message) -> None:
            nonlocal empezo
            if excedido:
                # FastAPI convierte la excepcion del tope en un 400 al leer un cuerpo JSON: lo que
                # la aplicacion conteste despues de exceder el tope se sustituye por el 413 fijo
                if not empezo:
                    empezo = True
                    await self._rechazar(send)
                return
            empezo = empezo or mensaje["type"] == "http.response.start"
            await send(mensaje)

        try:
            await self.app(scope, recibir, enviar)
        except _CuerpoExcedido:
            if not empezo:
                await self._rechazar(send)

    async def _rechazar(self, send: Send) -> None:
        cuerpo = b'{"detalle":"El cuerpo de la peticion excede el maximo de 20 MiB."}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(cuerpo)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": cuerpo})


def proteger(app: FastAPI, entorno: Mapping[str, str] | None = None) -> None:
    """Instala el tope de cuerpo, el filtro de redes y el de hosts. Si S3 ya había puesto un
    `TrustedHostMiddleware` con su lista, se reemplaza por el de la IP elegida (uno solo)."""
    fuente = os.environ if entorno is None else entorno
    app.user_middleware = [m for m in app.user_middleware if m.cls is not TrustedHostMiddleware]
    app.add_middleware(LimiteDeCuerpo)
    app.add_middleware(SoloRedesPrivadas)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=anfitriones_permitidos(fuente.get(VARIABLE_DIRECCION))
    )
