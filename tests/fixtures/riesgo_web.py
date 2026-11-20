"""El armado por HTTP de las pruebas de «Riesgo de la obra» (`/v1/riesgo`), compartido por
`tests/integration/test_api_riesgo.py` y `tests/integration/test_api_riesgo_mapa.py`.

Una instalación con cuentas y la carpeta del caso con la vía ficticia de `riesgo_obra.py`
(«Vía Ficticia Riesgo»), copiadas desde una plantilla por módulo de pruebas. Datos FICTICIOS.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from api import caso_web, dependencias
from operacion import config
from seguridad import cuentas
from tests.fixtures.produccion_api import Web
from tests.fixtures.riesgo_obra import ARCHIVO, crear_via
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

__all__ = ["en_la_via", "instalacion_con_la_via", "plantillas_de_la_via"]


def plantillas_de_la_via(carpeta: Path) -> dict[str, Path]:
    """La instalación con cuentas y la vía, una vez por módulo de pruebas."""
    return {"instalacion": plantilla_con_cuentas(carpeta), "via": crear_via(carpeta / ARCHIVO)}


@contextmanager
def instalacion_con_la_via(
    plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Copia la instalación y la vía de las plantillas; al salir, olvida casos, motores y frenos."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / ARCHIVO).write_bytes(plantillas["via"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    try:
        yield
    finally:
        caso_web.olvidar_todo()
        dependencias.cerrar_motores()
        cuentas.FRENO.reiniciar()


def en_la_via(login: str = "ana") -> Web:
    """La sesión de `login` con la vía elegida como caso actual."""
    web = Web(login)
    elegida = web.post("/v1/casos/actual", json={"nombre": ARCHIVO})
    assert elegida.status_code == 200, elegida.text
    return web
