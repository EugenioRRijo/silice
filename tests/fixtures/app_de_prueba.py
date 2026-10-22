"""Una aplicación FastAPI de prueba con los routers que aún no monta `api/main.py`.

En la migración final (bloque B) `api/main.py` lo edita solo el orquestador: el implementador
entrega la línea `include_router` en su informe. Mientras tanto, las pruebas de un router nuevo lo
montan aquí con lo mismo que pone `api.main` alrededor de cada ruta: la sesión (`/v1/sesion`, para
entrar con cookie), los manejadores de error con `{"detalle": ...}` y `proteger` (tope de cuerpo,
filtro de redes y de hosts). Como `tests/unit/test_api_equipo_propio.py`, que arma la suya.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException

from api import main
from api.proteccion import proteger
from api.rutas import sesion as rutas_sesion


def app_con(*routers: APIRouter) -> FastAPI:
    """Una aplicación con la sesión, los `routers` dados y las protecciones de `api.main`."""
    prueba = FastAPI()
    prueba.add_exception_handler(HTTPException, main.manejar_http_exception)
    prueba.add_exception_handler(LookupError, main.manejar_lookup_error)
    prueba.add_exception_handler(ValueError, main.manejar_value_error)
    prueba.include_router(rutas_sesion.router)
    for router in routers:
        prueba.include_router(router)
    proteger(prueba)
    return prueba
