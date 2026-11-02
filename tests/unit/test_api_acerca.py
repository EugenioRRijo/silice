"""`GET /v1/acerca`: versión, revisiones de las dos bases, carpeta de datos y módulos (ola 1 de la
sesión 2b; paridad con `ui/paginas/acerca.py`, RF-99; RM-1, RM-3).

Se ejerce sobre `api.main.app` real. La instalación de la prueba lleva una clave de API y tres
cuentas por el camino real: `admin` (administrador), `ana` (arma) y `rita` (revisa). La cuenta con
contraseña temporal no llega a tener cookie (`POST /v1/sesion` responde 403): no se ejerce aquí.

Oráculos, ninguno sale del código bajo prueba:

- La versión se lee del texto de `pyproject.toml` y la revisión de cada base, de su tabla
  `alembic_version` con `sqlite3` (no con `operacion.base_datos`), como en `test_ui_acerca.py`.
- Los módulos y su orden son los rótulos de la pantalla, escritos aquí a mano.
- Ruling de seguridad: la carpeta de datos es una ruta del servidor (puede llevar el nombre de
  usuario del equipo); solo la ve el administrador y la clave de API. Arma y revisa reciben `null`.
"""

from __future__ import annotations

import ast
import hashlib
import re
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.main import app
from operacion import config
from operacion.base_datos import Destino, preparar_base
from seguridad import cuentas, sesiones
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Usuario
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

RUTA = "/v1/acerca"
NUEVA = "otra contrasena larga de prueba"
CUENTAS = {"admin": CONTRASENA, "ana": NUEVA, "rita": NUEVA}
COOKIE = "silice_sesion"
MENSAJE_SIN_SESION = "Sesión ausente o vencida: entre de nuevo con su cuenta."
MODULOS = [
    "Similitud de partidas",
    "Anomalías de precios",
    "Planos IFC",
    "Planos DXF",
    "Informes PDF",
    "Datos del BCV",
    "Asistente de IA",
]
CAMPOS = {
    "version",
    "semver",
    "revision_instalacion",
    "head_instalacion",
    "revision_caso",
    "head_caso",
    "carpeta_datos",
    "modulos",
}


# --- Ayudas ---------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    carpeta = tmp_path_factory.mktemp("plantilla_acerca")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor(plantilla)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        for usuario in sesion.scalars(select(Usuario)):
            sesiones.cerrar_todas(sesion, usuario.id, "plantilla")
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> Iterator[None]:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_plantilla, destino)
    cuentas.FRENO.reiniciar()
    yield
    cuentas.FRENO.reiniciar()


def _cliente(**extra) -> TestClient:
    return TestClient(
        app, base_url=ANFITRION, client=IP_LOCAL, raise_server_exceptions=False, **extra
    )


def _con_clave() -> TestClient:
    return _cliente(headers={CABECERA: crear_clave_de_prueba()})


def _con_cuenta(login: str) -> TestClient:
    cliente = _cliente()
    r = cliente.post("/v1/sesion", json={"login": login, "contrasena": CUENTAS[login]})
    assert r.status_code == 200, r.text
    assert r.cookies.get(COOKIE)
    return cliente


def _version_de_pyproject() -> str:
    texto = (config.RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    proyecto = texto.split("[project]", 1)[1]
    return re.search(r'(?m)^version\s*=\s*"([^"]+)"', proyecto).group(1)


def _revision_en_disco(ruta: Path) -> str:
    with closing(sqlite3.connect(ruta)) as conexion:
        (revision,) = conexion.execute("SELECT version_num FROM alembic_version").fetchone()
    return revision


def _preparar_bases() -> tuple[str, str]:
    preparar_base(config.ruta_caso_por_defecto())
    return (
        _revision_en_disco(config.ruta_instalacion()),
        _revision_en_disco(config.ruta_caso_por_defecto()),
    )


# --- Acceso ---------------------------------------------------------------------------------


def test_sin_clave_ni_sesion_responde_401() -> None:
    r = _cliente().get(RUTA)
    assert r.status_code == 401
    assert r.json() == {"detalle": MENSAJE_SIN_SESION}


def test_una_clave_de_api_mala_responde_401_con_el_mensaje_de_la_proteccion() -> None:
    r = _cliente(headers={CABECERA: "no.es-una-clave"}).get(RUTA)
    assert r.status_code == 401


@pytest.mark.parametrize("login", ["admin", "ana", "rita"])
def test_cualquier_rol_con_sesion_ve_la_pagina(login: str) -> None:
    # la página de Streamlit no pide acción: la ve toda cuenta (ui/app.py: accion=None)
    assert _con_cuenta(login).get(RUTA).status_code == 200


def test_la_clave_de_api_entra_igual() -> None:
    assert _con_clave().get(RUTA).status_code == 200


def test_la_ruta_solo_lee() -> None:
    cliente = _con_clave()
    assert cliente.post(RUTA).status_code == 405
    assert cliente.delete(RUTA).status_code == 405


# --- Contenido ------------------------------------------------------------------------------


def test_trae_la_version_las_revisiones_y_los_modulos_en_el_orden_de_la_pantalla() -> None:
    instalacion, caso = _preparar_bases()
    cuerpo = _con_clave().get(RUTA).json()
    assert set(cuerpo) == CAMPOS
    assert cuerpo["version"] == _version_de_pyproject()
    fases = {"a": "alpha", "b": "beta", "rc": "rc"}  # 1.0.0rc1 -> 1.0.0-rc.1 (spec S5 §9.2)
    assert cuerpo["semver"] == re.sub(
        r"(a|b|rc)(\d+)$", lambda m: f"-{fases[m[1]]}.{m[2]}", cuerpo["version"]
    )
    assert (cuerpo["revision_instalacion"], cuerpo["revision_caso"]) == (instalacion, caso)
    # recién preparadas, cada una está en la última revisión que conoce esta versión
    assert (cuerpo["head_instalacion"], cuerpo["head_caso"]) == (instalacion, caso)
    assert [m["nombre"] for m in cuerpo["modulos"]] == MODULOS
    assert all(set(m) == {"nombre", "instalado"} for m in cuerpo["modulos"])
    assert all(isinstance(m["instalado"], bool) for m in cuerpo["modulos"])


def test_un_modulo_ausente_se_dice_no_instalado(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util

    real = importlib.util.find_spec
    paquetes = {
        "sentence_transformers",
        "sklearn",
        "ifcopenshell",
        "ezdxf",
        "reportlab",
        "anthropic",
    }

    def buscar(nombre: str, *resto):
        if nombre == "xlrd":
            return object()  # a la vista, esté o no instalado en este entorno
        return None if nombre in paquetes else real(nombre, *resto)

    monkeypatch.setattr(importlib.util, "find_spec", buscar)
    cuerpo = _con_clave().get(RUTA).json()
    esperado = {nombre: nombre == "Datos del BCV" for nombre in MODULOS}
    assert {m["nombre"]: m["instalado"] for m in cuerpo["modulos"]} == esperado


def test_un_caso_que_no_existe_se_dice_sin_crearlo() -> None:
    cuerpo = _con_clave().get(RUTA).json()
    assert cuerpo["revision_caso"] == "sin base"
    assert not config.ruta_caso_por_defecto().exists()


def test_un_caso_ilegible_se_dice_sin_error_ni_ruta_en_el_cuerpo() -> None:
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(b"esto no es sqlite" * 100)
    r = _con_clave().get(RUTA)
    assert r.status_code == 200
    assert r.json()["revision_caso"] == "ilegible"


def test_el_caso_es_el_del_proceso_cuando_apu_base_lo_fija(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    otro = tmp_path / "otro.db"
    preparar_base(otro)
    monkeypatch.setenv("APU_BASE", f"sqlite:///{otro.as_posix()}")
    cuerpo = _con_clave().get(RUTA).json()
    assert cuerpo["revision_caso"] == _revision_en_disco(otro)


# --- Ruling de seguridad: la carpeta de datos -----------------------------------------------


def test_la_carpeta_de_datos_la_ven_el_administrador_y_la_clave_de_api() -> None:
    esperada = str(config.carpeta_datos())
    assert _con_clave().get(RUTA).json()["carpeta_datos"] == esperada
    assert _con_cuenta("admin").get(RUTA).json()["carpeta_datos"] == esperada


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_quien_arma_o_revisa_no_recibe_la_ruta_del_servidor(login: str) -> None:
    r = _con_cuenta(login).get(RUTA)
    assert r.json()["carpeta_datos"] is None
    assert str(config.carpeta_datos()) not in r.text


def test_no_viaja_ninguna_ficha_ni_clave_en_el_cuerpo() -> None:
    cliente = _con_cuenta("admin")
    ficha = cliente.cookies.get(COOKIE)
    csrf = hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()
    texto = cliente.get(RUTA).text
    assert ficha not in texto and csrf not in texto


# --- Arquitectura (RM-1) --------------------------------------------------------------------


def test_la_logica_de_acerca_no_importa_interfaz_api_guiones_ni_pruebas() -> None:
    archivo = config.RAIZ / "aplicacion" / "acerca.py"
    modulos: set[str] = set()
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            modulos.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module)
    prohibidos = {"streamlit", "ui", "api", "scripts", "tests"}
    assert {m for m in modulos if m.split(".")[0] in prohibidos} == set()
