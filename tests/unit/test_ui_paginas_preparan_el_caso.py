"""Las páginas abren el caso por `preparar_base` (RV-5): una base de la 0.5.0 se adopta una sola vez
con su juego; una de una versión más nueva se rechaza con mensaje y sin tocarla."""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from operacion import config, respaldo
from operacion.base_datos import Destino, leer_estado, revision_head
from tests.fixtures import bases_prueba

SCRIPT = "from ui.paginas.catalogo import render\nrender()\n"


def _catalogo(monkeypatch, base: Path) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_el_catalogo_adopta_una_base_de_la_0_5_0_una_sola_vez(monkeypatch, tmp_path: Path) -> None:
    base = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")
    at = _catalogo(monkeypatch, base)
    assert not at.error
    assert leer_estado(base).revision == revision_head(Destino.CASO)
    assert len(respaldo.listar_juegos(config.carpeta_respaldos())) == 1
    at.run()
    assert len(respaldo.listar_juegos(config.carpeta_respaldos())) == 1


def test_una_base_mas_nueva_se_rechaza_con_mensaje_y_sin_tocarla(
    monkeypatch, tmp_path: Path
) -> None:
    base = bases_prueba.crear_base_futura(tmp_path / "futura.db")
    antes = respaldo.huella(base)
    at = _catalogo(monkeypatch, base)
    assert any("versión más nueva" in error.value for error in at.error)
    assert respaldo.huella(base) == antes
