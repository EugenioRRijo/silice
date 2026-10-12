"""Adaptador de las pruebas a la protección de la API (RF-98): una clave real en la
`instalacion.db` temporal y un `TestClient` que llega desde el propio equipo con ella.

Es el único sitio de las pruebas que conoce la forma de `seguridad.claves_api`.
"""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from api.main import app
from operacion.instalacion import sesion_de_instalacion
from seguridad import claves_api

CABECERA = claves_api.CABECERA
ANFITRION = "http://127.0.0.1:8000"
IP_LOCAL = ("127.0.0.1", 50000)


def crear_clave_de_prueba() -> str:
    """Una clave vigente `<identificador>.<secreto>` en la instalación de la prueba."""
    with sesion_de_instalacion() as sesion:
        clave, _ = claves_api.crear(sesion, "prueba de la API", "pruebas", datetime.now())
    return clave


def cliente_de_prueba() -> TestClient:
    """`TestClient` de `api.main.app` desde 127.0.0.1, con el `Host` permitido y la clave."""
    return TestClient(
        app, base_url=ANFITRION, client=IP_LOCAL, headers={CABECERA: crear_clave_de_prueba()}
    )
