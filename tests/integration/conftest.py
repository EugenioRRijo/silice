"""Fixtures de las pruebas de integración: una base SQLite en memoria ya sembrada.

Ninguna prueba escribe en `data/`: el motor vive en memoria y el script de siembra se ejerce
sobre `tmp_path` (NORMAS.md §9 y restricciones del sprint).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.catalog.sesion import _activar_claves_foraneas
from scripts.seed import sembrar
from tests.fixtures.base_con_pendiente import guardar_base_con_pendiente, url_sqlite


@pytest.fixture
def motor():
    """Motor SQLite en memoria con el esquema completo ya creado.

    `StaticPool` con `check_same_thread=False`, en vez de `core.catalog.crear_motor` (que usa el
    `SingletonThreadPool` por defecto del dialecto SQLite para `sqlite://`): las pruebas de la API
    (Sesión F.1) despachan las peticiones con `fastapi.testclient.TestClient`, que corre el ASGI
    en un hilo distinto al de la prueba. Con `SingletonThreadPool` ese hilo recibiría una base
    `:memory:` propia y vacía (`OperationalError: no such table`), porque ese pool nunca comparte
    una conexión entre hilos. `StaticPool` sí comparte una única conexión, que es lo que un
    `:memory:` de pruebas necesita para servir a más de un hilo. Mismo PRAGMA de claves foráneas
    que activa `crear_motor` (única fuente del listener, importado, no reescrito).
    """
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(engine, "connect", _activar_claves_foraneas)
    crear_esquema(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sesion(motor):
    """Sesión sobre el motor en memoria con la línea base ya sembrada y confirmada."""
    with abrir_sesion(motor) as sesion:
        sembrar(sesion)
        yield sesion


@contextmanager
def _cliente_http(fabrica_de_sesion: Callable[[], Any]) -> Iterator[Any]:
    """El único esqueleto del cliente HTTP de la API (INV‑042, M‑1 de la revisión de la pista C
    de C4): sustituye `api.dependencias.sesion_api` por `fabrica_de_sesion` y abre un
    `TestClient`.

    `fabrica_de_sesion` es lo que FastAPI llama en cada petición: una función que devuelve una
    sesión o un generador que la entrega. Importa FastAPI aquí dentro: el extra `api` solo hace
    falta en las pruebas que piden un cliente, no en todo el paquete de integración. El cliente
    llega desde 127.0.0.1 con una clave de API real de la instalación temporal (RF-98: toda ruta
    menos `/salud` la exige). La sustitución se deshace en un `finally`: si el arranque del
    cliente falla, la siguiente prueba no hereda la base de esta.
    """
    from api.dependencias import sesion_api
    from api.main import app
    from tests.fixtures.claves_api import cliente_de_prueba

    app.dependency_overrides[sesion_api] = fabrica_de_sesion
    try:
        with cliente_de_prueba() as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def cliente(sesion):
    """Cliente HTTP de la API sobre la sesión en memoria, compartida por todas las peticiones."""
    with _cliente_http(lambda: sesion) as cliente:
        yield cliente


@pytest.fixture
def cliente_con_pendiente(tmp_path):
    """Cliente HTTP sobre un archivo de `tmp_path` con el 001 guardado con su pendiente T-99.

    El base lo guarda el núcleo directo con `pendientes=` (`tests/fixtures/base_con_pendiente.py`)
    y el motor se cierra antes de la petición: la ruta lee lo persistido, con una sesión por
    petición como `api.dependencias.sesion_api`. Nada escribe en `data/`.
    """
    ruta = tmp_path / "escenarios.db"
    guardar_base_con_pendiente(ruta)
    motor = crear_motor(url_sqlite(ruta))

    def _sesion_por_peticion():
        with abrir_sesion(motor) as sesion:
            yield sesion

    try:
        with _cliente_http(_sesion_por_peticion) as cliente:
            yield cliente
    finally:
        motor.dispose()


@pytest.fixture
def items_payload():
    """Los ítems del presupuesto auditado como cuerpo JSON de `POST /presupuestos`, con los montos
    como texto. Una lista nueva por prueba: quien la altera no contamina a las demás."""
    from tests.fixtures.computo_auditado import items_auditados

    return [
        {
            "codigo_partida": item.codigo_partida,
            "descripcion": item.descripcion,
            "unidad": item.unidad,
            "cantidad": str(item.cantidad),
            "origen_id": item.origen_id,
            "origen_tipo": item.origen_tipo.value,
            "dominio": item.dominio.value,
            "regla": item.regla,
            "parametros": {clave: str(valor) for clave, valor in item.parametros.items()},
            "especificaciones": dict(item.especificaciones),
        }
        for item in items_auditados()
    ]


@pytest.fixture
def obra_sin_linea_base(motor):
    """OB-S2 (S2 §7.1) en una base vacía: la versión OB-001 con su plan, sin línea base de control.

    Datos ficticios (NORMAS.md §1). No confirma: la sesión se cierra con el motor."""
    from tests.fixtures import control_ob_s2 as ob

    with abrir_sesion(motor) as sesion:
        ob.sembrar(sesion)
        sesion.commit()  # un caso guardado: un `rollback` de la pantalla no lo deshace
        yield sesion


@pytest.fixture
def obra(obra_sin_linea_base):
    """OB-S2 con su línea base de control declarada (perspectiva costo, desde el 2026-11-02)."""
    from tests.fixtures import control_ob_s2 as ob

    ob.declarar_linea_base(obra_sin_linea_base)
    obra_sin_linea_base.commit()
    return obra_sin_linea_base
