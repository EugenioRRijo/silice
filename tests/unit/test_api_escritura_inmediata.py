"""Las rutas que crean una version, un proyecto o un presupuesto abren `BEGIN IMMEDIATE`.

Con la sesion comun (`sesion_api`, `BEGIN` diferido) la transaccion empieza leyendo: si entre esa
lectura y la primera escritura otra peticion escribe y confirma, SQLite no puede ascender la
lectura a escritura sobre una instantanea vieja y responde `database is locked` en el acto, sin
esperar el `busy_timeout`. Con `sesion_de_escritura_api` quien escribe toma el bloqueo antes de
leer y el otro espera (`api/dependencias.py`, SL-E12). Se mira lo que FastAPI inyecta de verdad
(el arbol de dependencias de cada ruta), no el texto de la firma.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from api.dependencias import sesion_api, sesion_de_escritura_api
from api.main import app

#: (metodo, ruta) de cada ruta que guarda una version, un proyecto o un presupuesto.
QUE_ESCRIBEN = [
    ("POST", "/proyectos"),
    ("POST", "/presupuestos"),
    ("POST", "/presupuestos/importar"),
    ("POST", "/presupuestos/{codigo}/actualizacion"),
    ("POST", "/presupuestos/revalorar"),
    ("POST", "/presupuestos/{codigo}/descartar"),
    ("POST", "/v1/control/recuperacion/elegir"),
]


def _rutas(router) -> Iterator[APIRoute]:
    """Como en `test_api_acceso_por_ruta.py`: FastAPI >= 0.140 no aplana `include_router`."""
    for ruta in router.routes:
        if isinstance(ruta, APIRoute):
            yield ruta
        elif hasattr(ruta, "original_router"):
            yield from _rutas(ruta.original_router)


def _ruta(metodo: str, camino: str) -> APIRoute:
    halladas = [r for r in _rutas(app.router) if r.path == camino and metodo in r.methods]
    assert len(halladas) == 1, (metodo, camino, halladas)
    return halladas[0]


def _llamadas(dependiente: Dependant) -> Iterator[Callable[..., Any]]:
    for hija in dependiente.dependencies:
        if hija.call is not None:
            yield hija.call
        yield from _llamadas(hija)


@pytest.mark.parametrize(("metodo", "camino"), QUE_ESCRIBEN)
def test_la_ruta_que_escribe_usa_la_sesion_de_escritura(metodo: str, camino: str) -> None:
    llamadas = set(_llamadas(_ruta(metodo, camino).dependant))
    assert sesion_de_escritura_api in llamadas
    assert sesion_api not in llamadas


def test_la_guardia_distingue_las_dos_sesiones() -> None:
    """No pasa en vacio: una ruta que solo lee sigue con la sesion comun."""
    llamadas = set(_llamadas(_ruta("GET", "/presupuestos").dependant))
    assert sesion_api in llamadas and sesion_de_escritura_api not in llamadas
