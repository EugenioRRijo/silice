"""La interfaz nueva servida por el propio FastAPI en `/app` (RT-1, RT-2, RF-112, RNF-22).

`/app` es estático y público, **sin secretos** (RT-9): lo que pide datos lo hace con la cookie de
`/v1/sesion`. Sirve lo que `npm run build` deja en `frontend-desktop/dist` (`DIST`, que las pruebas
parchean), con `html=True` para que `/app/` entregue `index.html`. La carpeta se mira en cada
petición: si falta, `/app` responde 404 con el mensaje de cómo compilarla, sin impedir que la API
arranque. `GET /app` redirige 307 a `/app/`.

Toda respuesta de `/app` lleva la CSP del plan de la sesión 2 (`default-src 'self'`, sin
`unsafe-eval` ni anfitriones externos: RNF-08), `nosniff` y `no-referrer`; el HTML además
`Cache-Control: no-cache` (los recursos de Vite llevan huella en el nombre). `'unsafe-inline'` en
estilos queda solo mientras Carbon o Univer lo exijan (lo comprueba la tarea 2.4 en el navegador).
La protección de red y de hosts (`api.proteccion`) envuelve también este montaje.

`GET /` no es parte del producto: la suite de escritorio abre `/app/` y la raíz redirige allí (307).
Solo con `SILICE_PORTADA_WEB=1` en el entorno sirve la portada web de pruebas, que compila
`npm run build:portada` (`DIST/portada.html`) y que el instalador no lleva; sin esa variable,
`/app/portada.html` tampoco se sirve aunque esté en la carpeta.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as ErrorHttp
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

from operacion.config import RAIZ

PREFIJO = "/app"
DIST: Path = RAIZ / "frontend-desktop" / "dist"
MENSAJE_SIN_COMPILAR = "La interfaz nueva no está compilada (npm run build en frontend-desktop)."
VARIABLE_PORTADA = "SILICE_PORTADA_WEB"
ARCHIVO_PORTADA = "portada.html"
MENSAJE_PORTADA_SIN_COMPILAR = (
    "La portada de pruebas no está compilada (npm run build:portada en frontend-desktop)."
)
MENSAJES = {404: "No existe ese archivo de la interfaz.", 405: "La interfaz solo admite GET."}
CSP = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    )
)
CABECERAS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def portada_activa() -> bool:
    """La portada web de pruebas, encendida solo con `SILICE_PORTADA_WEB=1` (se lee en cada
    petición)."""
    return os.environ.get(VARIABLE_PORTADA) == "1"


def con_cabeceras(respuesta: Response) -> Response:
    """Las cabeceras de seguridad de `/app`; al HTML, además, `Cache-Control: no-cache`."""
    respuesta.headers.update(CABECERAS)
    if respuesta.headers.get("content-type", "").startswith("text/html"):
        respuesta.headers["Cache-Control"] = "no-cache"
    return respuesta


class InterfazNueva:
    """Aplicación ASGI de `/app`: `StaticFiles` sobre `DIST` (leído en cada petición), sus
    errores en el formato `{"detalle": ...}` de la API y las cabeceras de seguridad."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # ningún websocket por aquí
            await send({"type": "websocket.close", "code": 1008})
            return
        carpeta = DIST
        if not carpeta.is_dir():
            respuesta: Response = JSONResponse({"detalle": MENSAJE_SIN_COMPILAR}, status_code=404)
        else:
            estaticos = StaticFiles(directory=carpeta, html=True, check_dir=False)
            ruta = estaticos.get_path(scope)
            if not portada_activa() and _es_la_portada(carpeta, ruta):
                respuesta = JSONResponse({"detalle": MENSAJES[404]}, status_code=404)
            else:
                respuesta = await _servir(estaticos, ruta, scope)
        await con_cabeceras(respuesta)(scope, receive, send)


async def _servir(estaticos: StaticFiles, ruta: str, scope: Scope) -> Response:
    try:
        return await estaticos.get_response(ruta, scope)
    except ErrorHttp as error:
        detalle = MENSAJES.get(error.status_code, str(error.detail))
        return JSONResponse({"detalle": detalle}, status_code=error.status_code)


def _es_la_portada(carpeta: Path, ruta: str) -> bool:
    """¿La ruta pedida abre el mismo archivo que `DIST/portada.html`? Se compara el archivo y no
    la grafía: en Windows `Portada.HTML`, `portada.html.` y `portada.html::$DATA` lo abren."""
    try:
        portada = os.stat(carpeta / ARCHIVO_PORTADA)
        pedido = os.stat(os.path.join(carpeta, ruta))
    except (OSError, ValueError):
        return False
    return os.path.samestat(portada, pedido)


def raiz(request: Request) -> Response:
    """`GET /` → `/app/` (307); con `SILICE_PORTADA_WEB=1`, la portada de pruebas compilada por
    Vite (`DIST/portada.html`) o un 404 que dice cómo compilarla."""
    if not portada_activa():
        return redirigir(request)
    compilada = DIST / ARCHIVO_PORTADA
    if not compilada.is_file():
        sin_compilar = JSONResponse({"detalle": MENSAJE_PORTADA_SIN_COMPILAR}, status_code=404)
        return con_cabeceras(sin_compilar)
    return con_cabeceras(HTMLResponse(compilada.read_text(encoding="utf-8")))


def redirigir(_request: Request) -> Response:
    """`/app` → `/app/` (307), con las mismas cabeceras."""
    return con_cabeceras(RedirectResponse(f"{PREFIJO}/", status_code=307))


def montar(app: FastAPI) -> None:
    """Registra `/` y `/app` (fuera del esquema OpenAPI y sin clave: son estáticos y públicos)."""
    app.add_route("/", raiz, methods=["GET", "HEAD"], include_in_schema=False)
    app.add_route(PREFIJO, redirigir, methods=["GET", "HEAD"], include_in_schema=False)
    app.mount(PREFIJO, InterfazNueva(), name="interfaz")
