"""INV-081 en la pagina de partidas similares (UC-03): una falla declarada del modelo es un mensaje.

La pagina usa el criterio unico de `ml.normalization.proponedor` (por `ui.composicion.
sugerir_partidas_similares`): ante una de `FALLAS_DE_LA_PROPUESTA` muestra `st.error` (o el aviso
del extra ausente), nunca una traza. El modelo se simula parchando
`ml.normalization.normalizador._cargar_modelo`, sin descargar nada. La base vive en `tmp_path`,
desviada por el objeto modulo `sys.modules["ui.caso"]`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from scripts.seed import sembrar
from tests.conftest import RUTA_BASE_REAL, huella

SCRIPT = "from ui.paginas.similares import render\nrender()\n"
ROTULO_DESCRIPCION = "Descripcion de la partida"


@pytest.fixture
def base_sembrada(tmp_path: Path) -> Path:
    base = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return base


def _consultar(monkeypatch, base: Path, falla: Exception) -> AppTest:
    """La pagina con `falla` al cargar el modelo, tras teclear una descripcion."""

    def _cargar_modelo(*_args, **_kwargs):
        raise falla

    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _cargar_modelo)
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    next(t for t in at.text_input if t.label == ROTULO_DESCRIPCION).input(
        "excavacion de zanja"
    ).run()
    return at


def test_pesos_corruptos_dan_un_mensaje_y_no_una_traza(monkeypatch, base_sembrada):
    antes = huella(RUTA_BASE_REAL)
    at = _consultar(monkeypatch, base_sembrada, RuntimeError("pesos corruptos simulados"))

    assert not at.exception, [e.value for e in at.exception]
    errores = [e.value for e in at.error]
    assert any(
        "El modelo de similitud no esta disponible" in e and "RuntimeError" in e for e in errores
    ), errores
    assert huella(RUTA_BASE_REAL) == antes


def test_sin_el_extra_la_pagina_lo_dice(monkeypatch, base_sembrada):
    """La falla real del extra ausente es `ModuleNotFoundError`; `ml` la declara `ImportError`."""
    pagina = importlib.import_module("ui.paginas.similares")
    at = _consultar(
        monkeypatch,
        base_sembrada,
        ModuleNotFoundError("No module named 'sentence_transformers'"),
    )

    assert not at.exception, [e.value for e in at.exception]
    assert [e.value for e in at.error] == [pagina._MENSAJE_SIN_EXTRA_ML]
