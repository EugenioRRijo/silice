"""El navegador ante la API: cuentas reales, cookie de sesión y anti-CSRF (ola 0a de la sesión 2b).

Lo comparten las pruebas de la ola 0a (`test_api_casos.py`, `test_api_acceso_por_ruta.py`,
`test_api_equipo_propio.py`, `test_api_sesion_contrasena.py`); INV-052: lo compartido entre pruebas
vive en `tests/fixtures/`. Oráculos propios, ninguno sale del código bajo prueba: el CSRF se
recalcula con `hashlib` (`sha256("csrf:" + ficha)`, RS2-4) y los roles de cada cuenta los fija
`CUENTAS` a mano.

`plantilla_con_cuentas` crea una vez por módulo una `instalacion.db` migrada con cuatro cuentas por
el camino real (`seguridad.cuentas`); `copiar_instalacion` la deja en la carpeta de datos temporal
de cada prueba (la fija `tests/conftest.py`).
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from operacion import config
from operacion.base_datos import Destino, preparar_base
from seguridad import cuentas, sesiones
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Usuario
from tests.fixtures.claves_api import ANFITRION
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

NUEVA = "otra contrasena larga de prueba"
ORIGEN = ANFITRION  # http://127.0.0.1:8000: el mismo anfitrión que el `Host` del cliente
COOKIE = "silice_sesion"
CSRF = "X-Silice-CSRF"
MENSAJE_PERMISO = "Su cuenta no tiene permiso para esta acción."
#: Login -> (contraseña vigente, roles). `tomas` conserva la temporal: debe cambiarla.
CUENTAS: dict[str, tuple[str, frozenset[str]]] = {
    "admin": (CONTRASENA, frozenset({"administrador"})),
    "ana": (NUEVA, frozenset({"arma"})),
    "rita": (NUEVA, frozenset({"revisa"})),
    "tomas": (CONTRASENA, frozenset({"arma"})),
}


def csrf(ficha: str) -> str:
    return hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()


def plantilla_con_cuentas(carpeta: Path) -> Path:
    """`instalacion.db` migrada con admin (administrador), ana (arma), rita (revisa) y tomas
    (arma, con la contraseña temporal sin cambiar), sin sesiones abiertas."""
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor(plantilla)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        persona(sesion, admin, "tomas", ("arma",))
        for usuario in sesion.scalars(select(Usuario)):
            sesiones.cerrar_todas(sesion, usuario.id, "plantilla")
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()  # cierra el WAL: la copia lleva todo
    return plantilla


def copiar_instalacion(plantilla: Path) -> None:
    """La plantilla en la `instalacion.db` de la carpeta de datos de esta prueba."""
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(plantilla, destino)
    cuentas.FRENO.reiniciar()  # el freno global es del proceso: ninguna prueba hereda fallos


def cliente(aplicacion: FastAPI, ip: str = "127.0.0.1") -> TestClient:
    return TestClient(
        aplicacion, base_url=ANFITRION, client=(ip, 50000), raise_server_exceptions=False
    )


def entrar(navegador: TestClient, login: str, contrasena: str | None = None, **extra):
    clave = CUENTAS[login][0] if contrasena is None else contrasena
    return navegador.post("/v1/sesion", json={"login": login, "contrasena": clave}, **extra)


def ficha_de(respuesta) -> str:
    ficha = respuesta.cookies.get(COOKIE)
    assert ficha, respuesta.headers.get("set-cookie")
    return ficha


def con_cuenta(aplicacion: FastAPI, login: str, ip: str = "127.0.0.1") -> tuple[TestClient, str]:
    """Un navegador ya dentro con `login` (la cookie queda en su tarro) y su ficha."""
    navegador = cliente(aplicacion, ip)
    respuesta = entrar(navegador, login)
    assert respuesta.status_code == 200, respuesta.text
    return navegador, ficha_de(respuesta)


def protegida(ficha: str, origen: str | None = ORIGEN) -> dict[str, str]:
    """Las cabeceras de un método que escribe: el CSRF de la ficha y el `Origin` propio."""
    cabeceras = {CSRF: csrf(ficha)}
    if origen is not None:
        cabeceras["Origin"] = origen
    return cabeceras
