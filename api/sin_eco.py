"""Un 422 que no repite lo enviado (RM-4; revisión de seguridad de la ola 4).

El 422 de validación de FastAPI devuelve cada valor rechazado en `input`: en una ruta con una
contraseña, esa contraseña volvería en la respuesta. Un router que usa `route_class=RutaSinEco`
contesta `{"detalle": <mensaje fijo>}`: el de `sin_eco(...)` en el punto final o, si no lo marca,
`RutaSinEco.mensaje_por_omision`. El resto de la API conserva el 422 de FastAPI.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute


def sin_eco(mensaje: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Fija el mensaje fijo del 422 de un punto final (`RutaSinEco`)."""

    def marcar(punto_final: Callable[..., Any]) -> Callable[..., Any]:
        punto_final.mensaje_sin_eco = mensaje  # type: ignore[attr-defined]
        return punto_final

    return marcar


class RutaSinEco(APIRoute):
    """Ruta cuyo 422 de validación no repite lo enviado. Subclasee y fije `mensaje_por_omision`
    para el mensaje de los puntos finales que no usan `sin_eco`."""

    mensaje_por_omision = "Los datos enviados no son válidos."

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()
        mensaje = getattr(self.endpoint, "mensaje_sin_eco", self.mensaje_por_omision)

        async def manejador(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError:
                return JSONResponse(status_code=422, content={"detalle": mensaje})

        return manejador
