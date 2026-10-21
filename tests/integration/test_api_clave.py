"""La API exige clave en toda ruta menos `/salud` y se defiende de hosts y redes ajenas
(RF-98; spec S5 §8.3). Recorre las rutas reales de la aplicación: una ruta nueva sin clave rompe
la prueba.

Desviación registrada respecto del plan: FastAPI 0.141 ya no aplana `include_router` en
`app.routes` (deja objetos `_IncludedRouter`); el recorrido baja por su `original_router` y se
contrasta con las rutas del esquema OpenAPI, para que ninguna se escape por ninguno de los dos
caminos. La clave se crea con `tests.fixtures.claves_api` (firma real de S3, bitácora T9).
"""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.main import app
from api.proteccion import LIMITE_CUERPO
from operacion import config, registro
from operacion.base_datos import Destino, preparar_base
from tests.fixtures.claves_api import ANFITRION, CABECERA, crear_clave_de_prueba


def _rutas(router) -> Iterator[APIRoute]:
    for ruta in router.routes:
        if isinstance(ruta, APIRoute):
            yield ruta
        elif hasattr(ruta, "original_router"):  # FastAPI >= 0.140: routers incluidos
            yield from _rutas(ruta.original_router)


RUTAS = list(_rutas(app.router))
#: Sin clave a propósito: el ping y el acceso del navegador por cuenta (RT-9, sesión 2), que se
#: protege con la contraseña, el freno y el bloqueo de `seguridad.cuentas`.
SIN_CLAVE = frozenset({"/salud", "/v1/sesion"})
PROTEGIDAS = [
    (ruta, metodo)
    for ruta in RUTAS
    if ruta.path not in SIN_CLAVE
    for metodo in sorted(ruta.methods - {"HEAD", "OPTIONS"})
]


def _cliente(ip: str = "127.0.0.1", base: str = ANFITRION, **extra) -> TestClient:
    return TestClient(
        app, base_url=base, client=(ip, 50000), raise_server_exceptions=False, **extra
    )


def _ruta_concreta(ruta: APIRoute) -> str:
    return re.sub(r"\{[^}]+\}", "x", ruta.path)


def _get_sin_parametros() -> APIRoute:
    return next(r for r, m in PROTEGIDAS if m == "GET" and "{" not in r.path)


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    """Una `instalacion.db` ya migrada, una vez por módulo: cada prueba parte de una copia y no
    paga las migraciones de Alembic (la base sigue siendo real y está en `tmp_path`)."""
    plantilla = tmp_path_factory.mktemp("plantilla") / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path) -> None:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_migrada, destino)


@pytest.fixture
def clave_api() -> str:
    return crear_clave_de_prueba()


def test_hay_rutas_que_proteger_y_estan_las_de_s3() -> None:
    assert len(PROTEGIDAS) >= 10
    assert any(ruta.path == "/v1/auditorias" for ruta, _ in PROTEGIDAS)


def test_el_recorrido_ve_todas_las_rutas_del_esquema() -> None:
    """Ninguna ruta del OpenAPI queda fuera del recorrido (y la única sin clave es `/salud`)."""
    # El OpenAPI no lleva el convertidor: `{partida:path}` sale como `{partida}`.
    recorridas = {
        (re.sub(r"\{([^}:]+):[^}]+\}", r"{\1}", r.path), m.lower())
        for r in RUTAS
        for m in r.methods - {"HEAD", "OPTIONS"}
    }
    esquema = {
        (camino, metodo)
        for camino, operaciones in app.openapi()["paths"].items()
        for metodo in operaciones
    }
    assert esquema <= recorridas and ("/salud", "get") in recorridas


@pytest.mark.parametrize(
    ("ruta", "metodo"), PROTEGIDAS, ids=[f"{m} {r.path}" for r, m in PROTEGIDAS]
)
def test_cada_ruta_menos_salud_da_401_sin_clave(ruta: APIRoute, metodo: str) -> None:
    respuesta = _cliente().request(metodo, _ruta_concreta(ruta), json={})
    assert respuesta.status_code == 401, respuesta.text
    assert "detalle" in respuesta.json()


@pytest.mark.parametrize(
    "clave", ["", "AB12CD34.no-es-la-clave", "sin-punto", "a.b.c", "x" * 5000, "."]
)
def test_una_clave_falsa_tampoco_pasa(clave: str) -> None:
    respuesta = _cliente().get(_get_sin_parametros().path, headers={CABECERA: clave})
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": "Clave de API ausente, desconocida o revocada."}


def test_el_identificador_bueno_con_otro_secreto_no_pasa(clave_api: str) -> None:
    identificador = clave_api.split(".")[0]
    respuesta = _cliente().get(
        _get_sin_parametros().path, headers={CABECERA: f"{identificador}.otro-secreto"}
    )
    assert respuesta.status_code == 401


def test_con_clave_valida_la_ruta_responde_sin_401_ni_403(clave_api: str) -> None:
    cliente = _cliente(headers={CABECERA: clave_api})
    assert cliente.get(_get_sin_parametros().path).status_code not in (401, 403)


def test_salud_responde_sin_clave_y_sin_version() -> None:
    respuesta = _cliente().get("/salud")
    assert respuesta.status_code == 200 and respuesta.json() == {"estado": "ok"}


def test_ip_publica_simulada_recibe_403(clave_api: str) -> None:
    cliente = _cliente(ip="8.8.8.8", headers={CABECERA: clave_api})
    for ruta in ("/salud", "/v1/auditorias"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 403 and "detalle" in respuesta.json()


@pytest.mark.parametrize("ip", ["192.168.1.30", "10.0.0.5", "172.16.0.9", "::1"])
def test_una_ip_privada_simulada_pasa_el_filtro(ip: str) -> None:
    assert _cliente(ip=ip).get("/salud").status_code == 200


def test_un_host_ajeno_recibe_400() -> None:
    respuesta = _cliente(base="http://atacante.ejemplo").get("/salud")
    assert respuesta.status_code == 400


def test_localhost_es_un_anfitrion_permitido() -> None:
    assert _cliente(base="http://localhost:8000").get("/salud").status_code == 200


def test_un_cuerpo_de_20_mib_pasa_el_tope_y_uno_mas_recibe_413() -> None:
    """Frontera del tope (spec §8.3): 20 MiB exactos llegan a la ruta (401 sin clave); un byte
    más se corta con 413 antes de pedir la clave."""
    ruta = next(r for r, m in PROTEGIDAS if m == "POST")
    assert LIMITE_CUERPO == 20 * 1024 * 1024
    justo = _cliente().post(_ruta_concreta(ruta), content=b"x" * LIMITE_CUERPO)
    de_mas = _cliente().post(_ruta_concreta(ruta), content=b"x" * (LIMITE_CUERPO + 1))
    assert (justo.status_code, de_mas.status_code) == (401, 413)


def test_la_clave_nunca_queda_en_claro_en_la_base_ni_en_los_registros(clave_api: str) -> None:
    identificador, secreto = clave_api.split(".")
    registro.configurar(config.carpeta_registros())
    try:
        cliente = _cliente(headers={CABECERA: clave_api})
        assert cliente.get(_get_sin_parametros().path).status_code not in (401, 403)
        falsa = f"{identificador}.{secreto[::-1]}"
        assert (
            _cliente().get(_get_sin_parametros().path, headers={CABECERA: falsa}).status_code == 401
        )
        logging.getLogger(registro.NOMBRE_LOGGER).error("petición con %s: %s", CABECERA, falsa)
    finally:
        logger = logging.getLogger(registro.NOMBRE_LOGGER)
        for manejador in list(logger.handlers):
            logger.removeHandler(manejador)
            manejador.close()
    base = config.ruta_instalacion()
    for archivo in base.parent.glob(base.name + "*"):  # la base, su -wal y su -journal
        contenido = archivo.read_bytes()
        assert secreto.encode() not in contenido and secreto[::-1].encode() not in contenido
    with closing(sqlite3.connect(base)) as conexion:
        (huella,) = conexion.execute(
            "SELECT huella_secreto FROM clave_api WHERE identificador = ?", (identificador,)
        ).fetchone()
        detalles = " ".join(d for (d,) in conexion.execute("SELECT detalle FROM evento_acceso"))
    assert huella == hashlib.sha256(secreto.encode("utf-8")).hexdigest()
    assert secreto not in detalles and secreto[::-1] not in detalles
    texto = (config.carpeta_registros() / "silice.log").read_text(encoding="utf-8")
    assert secreto not in texto and secreto[::-1] not in texto


def test_un_intento_fallido_queda_en_el_registro_de_accesos() -> None:
    """Ola 0a (RM-3): el intento fallido es el de una clave presentada; sin cabecera ni cookie la
    ruta responde el 401 de la sesión y no hay clave que registrar."""
    crear_clave_de_prueba()  # la instalación existe
    respuesta = _cliente(ip="192.168.1.30").get(
        _get_sin_parametros().path, headers={CABECERA: "AB12CD34.no-es-la-clave"}
    )
    assert respuesta.status_code == 401
    with closing(sqlite3.connect(config.ruta_instalacion())) as conexion:
        filas = conexion.execute(
            "SELECT tipo, login_intentado, ip_cliente, detalle FROM evento_acceso "
            "WHERE tipo = 'fallo'"
        ).fetchall()
    assert filas == [("fallo", "(api)", "192.168.1.30", "clave de api")]


def test_la_documentacion_no_se_publica_en_el_producto() -> None:
    from fastapi import FastAPI

    from api.proteccion import opciones_documentacion

    producto = TestClient(FastAPI(**opciones_documentacion({"SILICE_PRODUCTO": "1"})))
    for ruta in ("/docs", "/redoc", "/openapi.json"):
        assert producto.get(ruta).status_code == 404, ruta
    desarrollo = TestClient(FastAPI(**opciones_documentacion({})))
    assert desarrollo.get("/docs").status_code == 200
