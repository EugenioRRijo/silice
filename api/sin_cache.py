"""`Cache-Control: no-store` en TODA respuesta de un router, también en las de error.

Un router con `route_class=RutaSinCache` contesta sin que el navegador guarde nada: ni lo que
lee (existencias de la arenera, historial de auditorías con nombres de archivo y hallazgos de la
empresa) ni sus rechazos (401, 403, 404, 422).

Las excepciones HTTP **no se convierten en respuesta aquí**: se les añade la cabecera y se vuelven
a lanzar, para que el manejador de la aplicación las formatee (`{"detalle": ...}`). Atraparlas y
contestar desde la ruta haría que las dependencias con `yield` (la sesión de `instalacion.db`)
vieran una salida normal y confirmaran una escritura a medias. El 422 de validación, que ocurre
antes de que la ruta escriba nada, conserva el cuerpo estándar de FastAPI con la cabecera.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

SIN_CACHE = "no-store"


class RutaSinCache(APIRoute):
    """Ruta cuya respuesta, de éxito o de error, lleva `Cache-Control: no-store`."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejador(request: Request) -> Response:
            try:
                respuesta = await original(request)
            except HTTPException as error:
                error.headers = {**(error.headers or {}), "Cache-Control": SIN_CACHE}
                raise
            except RequestValidationError as error:
                respuesta = await request_validation_exception_handler(request, error)
            respuesta.headers["Cache-Control"] = SIN_CACHE
            return respuesta

        return manejador
