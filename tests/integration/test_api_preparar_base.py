"""La API abre el caso por `preparar_base` (RV-5; spec S5 §5.2): adopta una base de la 0.5.0 y,
ante una que no se puede preparar, responde 503 con el mensaje y sin tocarla."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.dependencias as dependencias
from operacion import respaldo
from operacion.base_datos import Destino, leer_estado, revision_head
from tests.fixtures import bases_prueba
from tests.fixtures.claves_api import cliente_de_prueba


@pytest.fixture
def cliente_sobre(monkeypatch):
    monkeypatch.setattr(dependencias, "_motor", None)

    def abrir(ruta: Path) -> TestClient:
        monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
        return cliente_de_prueba()

    yield abrir
    if dependencias._motor is not None:
        dependencias._motor.dispose()


def test_la_api_adopta_una_base_de_la_0_5_0_y_responde(tmp_path: Path, cliente_sobre) -> None:
    ruta = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")
    with cliente_sobre(ruta) as cliente:
        respuesta = cliente.get("/partidas")
    assert respuesta.status_code == 200 and respuesta.json()
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)


def test_una_base_mas_nueva_responde_503_y_no_se_toca(tmp_path: Path, cliente_sobre) -> None:
    ruta = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    antes = respaldo.huella(ruta)
    with cliente_sobre(ruta) as cliente:
        respuesta = cliente.get("/partidas")
    assert respuesta.status_code == 503
    assert "versión más nueva" in respuesta.json()["detalle"]
    assert respaldo.huella(ruta) == antes
