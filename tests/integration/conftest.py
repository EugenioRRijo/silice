"""Fixtures de las pruebas de integración: una base SQLite en memoria ya sembrada.

Ninguna prueba escribe en `data/`: el motor vive en memoria y el script de siembra se ejerce
sobre `tmp_path` (CLAUDE.md §9 y restricciones del sprint).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from core.catalog import abrir_sesion, crear_esquema
from core.catalog.sesion import _activar_claves_foraneas
from scripts.seed import sembrar


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


@pytest.fixture
def cliente(sesion):
    """Cliente HTTP de la API sobre la sesión en memoria (INV‑042: una sola copia).

    Importa FastAPI dentro de la fixture: el extra `api` solo hace falta en las pruebas que la
    piden, no en todo el paquete de integración. La sustitución de la sesión se deshace en un
    `finally`: si el arranque del cliente falla, la siguiente prueba no hereda la base de esta.
    """
    from fastapi.testclient import TestClient

    from api.dependencias import sesion_api
    from api.main import app

    app.dependency_overrides[sesion_api] = lambda: sesion
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()


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
