"""Lo compartido por las pruebas de la API de produccion: la instalacion migrada con sus tres
cuentas (admin, ana y rita), el cliente con clave de API, el navegador con sesion (`Web`) y el
conteo de filas. Datos FICTICIOS. Vive aqui porque un modulo de prueba no importa de otro (INV-052).
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api.main import app
from operacion import config
from operacion.base_datos import Destino, preparar_base
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas
from seguridad.base import abrir_sesion, crear_motor
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

NUEVA = "otra contrasena larga de prueba"
COOKIE = "silice_sesion"
CABECERA_CSRF = "X-Silice-CSRF"
CONTRASENAS = {"admin": CONTRASENA, "ana": NUEVA, "rita": NUEVA}


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    """Una `instalacion.db` ya migrada, una vez por módulo (patrón de `test_api_clave.py`), con tres
    cuentas por el camino real: admin (administrador), ana (arma) y rita (revisa)."""
    carpeta = tmp_path_factory.mktemp("plantilla_produccion")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor(plantilla)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()  # cierra el WAL: la copia lleva todo
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)
    cuentas.FRENO.reiniciar()  # el freno global es del proceso: ninguna prueba hereda fallos
    yield
    cuentas.FRENO.reiniciar()


@pytest.fixture
def http() -> TestClient:
    """Cliente desde 127.0.0.1 con una clave de API real de la instalación temporal."""
    return TestClient(
        app,
        base_url=ANFITRION,
        client=IP_LOCAL,
        headers={CABECERA: crear_clave_de_prueba()},
        raise_server_exceptions=False,
    )


def _contar(modelo) -> int:
    with sesion_de_instalacion() as sesion:
        return sesion.scalar(select(func.count()).select_from(modelo))


def _csrf(ficha: str) -> str:
    """Oráculo del anti-CSRF (RS2-4): `sha256("csrf:" + ficha)` en hexadecimal."""
    return hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()


class Web:
    """Un navegador ya dentro con una cuenta: la cookie queda en el tarro del cliente y las
    peticiones que escriben llevan `X-Silice-CSRF` y `Origin` (lo que haría la interfaz nueva)."""

    def __init__(self, login: str) -> None:
        self.cliente = TestClient(
            app, base_url=ANFITRION, client=IP_LOCAL, raise_server_exceptions=False
        )
        entrada = self.cliente.post(
            "/v1/sesion", json={"login": login, "contrasena": CONTRASENAS[login]}
        )
        assert entrada.status_code == 200, entrada.text
        self.ficha = entrada.cookies.get(COOKIE)
        assert self.ficha

    def cabeceras(self) -> dict[str, str]:
        return {CABECERA_CSRF: _csrf(self.ficha), "Origin": ANFITRION}

    def get(self, ruta: str, **kw):
        return self.cliente.get(ruta, **kw)

    def post(self, ruta: str, **kw):
        return self.cliente.post(ruta, headers=self.cabeceras(), **kw)
