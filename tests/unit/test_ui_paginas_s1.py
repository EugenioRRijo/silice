"""AppTest de arranque y de las acciones de las dos pantallas de UC-17 (S1, Tarea 9).

La base de cada prueba es la de la 0.5.0 copiada a `tmp_path`: la pantalla la adopta con
`preparar_base`. AppTest no escribe en `st.data_editor` ni sube archivos, así que la subida
y el informe previo se prueban en `test_ui_indices.py` y `test_ui_precios_empresa.py`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fixtures import bases_prueba

ROTULO_REFERENCIA = "Cargar la referencia MaPreX en Bs"


def _abrir(monkeypatch, tmp_path: Path, pagina: str) -> AppTest:
    base = bases_prueba.copiar_base("0.5.0", "demo.db", tmp_path / "demo.db")
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(
        f"from ui.paginas.{pagina} import render\nrender()\n", default_timeout=90
    )
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_indices_arranca_y_leer_sin_archivo_dice_que_hacer(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path, "indices")
    assert not at.error
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Elija el archivo" in e.value for e in at.error)


def test_precios_empresa_arranca_y_carga_la_referencia_una_sola_vez(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path, "precios_empresa")
    assert not at.error
    boton = next(b for b in at.button if b.label == ROTULO_REFERENCIA)
    boton.click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("cargada con" in s.value for s in at.success)
    next(b for b in at.button if b.label == ROTULO_REFERENCIA).click().run()
    assert any("ya estaba cargada" in s.value for s in at.success)


def test_precios_empresa_sin_moneda_ni_archivo_no_crea_nada(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path, "precios_empresa")
    next(b for b in at.button if b.label == ROTULO_REFERENCIA).click().run()
    enviar = next(b for b in at.button if b.label == "Crear la lista de la empresa")
    enviar.click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Elija la moneda" in e.value for e in at.error)
