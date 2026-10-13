"""Sin el módulo de similitud, la pantalla dice cuál módulo falta (RF-97 g; spec S5 §4.2).

En el producto (instalador básico) no hay `uv`: el mensaje nombra el módulo y el instalador
completo; en desarrollo, el extra. La falla real del extra ausente se simula como en
`tests/unit/test_ui_similares.py` (parchando `_cargar_modelo` con `ModuleNotFoundError`), y la
base del caso vive en `tmp_path`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from operacion import config
from scripts.seed import sembrar

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


def _errores(monkeypatch, base: Path, producto: bool) -> list[str]:
    def _sin_extra(*_args, **_kwargs):
        raise ModuleNotFoundError("No module named 'sentence_transformers'")

    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _sin_extra)
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: producto)
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    next(t for t in at.text_input if t.label == ROTULO_DESCRIPCION).input(
        "excavacion de zanja"
    ).run()
    assert not at.exception, [e.value for e in at.exception]
    return [e.value for e in at.error]


def test_en_el_producto_nombra_el_modulo(monkeypatch, base_sembrada) -> None:
    (mensaje,) = _errores(monkeypatch, base_sembrada, producto=True)
    assert "módulo de similitud de partidas" in mensaje and "instalador completo" in mensaje
    assert "uv sync" not in mensaje  # en el producto no hay uv


def test_en_desarrollo_nombra_el_extra(monkeypatch, base_sembrada) -> None:
    (mensaje,) = _errores(monkeypatch, base_sembrada, producto=False)
    assert "uv sync --extra similitud" in mensaje
    assert "instalador completo" not in mensaje


def test_otra_falla_del_modelo_no_se_confunde_con_el_modulo_ausente(
    monkeypatch, base_sembrada
) -> None:
    """Solo la falla de importación habla del módulo; un modelo roto da su propio error."""

    def _roto(*_args, **_kwargs):
        raise RuntimeError("pesos corruptos simulados")

    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base_sembrada))
    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _roto)
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()
    next(t for t in at.text_input if t.label == ROTULO_DESCRIPCION).input("zanja").run()
    (mensaje,) = [e.value for e in at.error]
    assert "RuntimeError" in mensaje and "módulo de similitud" not in mensaje
