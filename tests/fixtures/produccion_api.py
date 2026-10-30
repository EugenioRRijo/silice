"""Lo compartido por las pruebas de la API de produccion. Datos FICTICIOS.

Solo funciones simples (sin `@pytest.fixture`, como `sesion_web.py`): cada modulo de prueba declara
sus propias fixtures y las llama. La instalacion migrada con sus cuentas (admin, ana y rita) y la
copia a la carpeta de datos de cada prueba salen de `sesion_web`. INV-052: lo compartido entre
pruebas vive en `tests/fixtures/`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api.main import app
from operacion.instalacion import sesion_de_instalacion
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.sesion_web import CSRF, ORIGEN, cliente, csrf, entrar, ficha_de


def cliente_con_clave() -> TestClient:
    """Cliente desde 127.0.0.1 con una clave de API real de la instalacion temporal."""
    return TestClient(
        app,
        base_url=ANFITRION,
        client=IP_LOCAL,
        headers={CABECERA: crear_clave_de_prueba()},
        raise_server_exceptions=False,
    )


def contar(modelo) -> int:
    with sesion_de_instalacion() as sesion:
        return sesion.scalar(select(func.count()).select_from(modelo))


class Web:
    """Un navegador ya dentro con una cuenta: la cookie queda en el tarro del cliente y las
    peticiones que escriben llevan `X-Silice-CSRF` y `Origin` (lo que haria la interfaz nueva)."""

    def __init__(self, login: str) -> None:
        self.cliente = cliente(app)
        entrada = entrar(self.cliente, login)
        assert entrada.status_code == 200, entrada.text
        self.ficha = ficha_de(entrada)

    def cabeceras(self) -> dict[str, str]:
        return {CSRF: csrf(self.ficha), "Origin": ORIGEN}

    def get(self, ruta: str, **kw):
        return self.cliente.get(ruta, **kw)

    def post(self, ruta: str, **kw):
        return self.cliente.post(ruta, headers=self.cabeceras(), **kw)
