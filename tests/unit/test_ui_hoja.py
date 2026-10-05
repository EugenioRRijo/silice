"""Pantalla «Hoja del proyecto», pestaña Espacio y metrajes (tarea 1.8).

`AppTest` no puede editar un `st.data_editor`: aqui se prueba el arranque (sin excepcion, con el
borrador vacio y con el baño de OF-001 sembrado en el borrador) y lo que pinta. La edicion de
celdas la cubren las pruebas de `ui.hoja` (`tests/unit/test_hoja.py`). La base se desvia a un
temporal por el objeto modulo `sys.modules["ui.caso"]`; la salvaguarda de `tests/conftest.py`
vigila `data/apu.db`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fixtures.espacio_bano import espacio_bano
from ui.paginas.hoja import CLAVE_BORRADOR, PESTANAS

SCRIPT = "from ui.paginas.hoja import render\nrender()\n"


def _arrancar(monkeypatch, base: Path, borrador=None) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    if borrador is not None:
        at.session_state[CLAVE_BORRADOR] = borrador
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_la_pantalla_arranca_con_el_borrador_vacio(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path / "no_existe.db")
    # los cinco editores: origenes, ambientes, fuentes, puntos y vertices de recorridos
    assert len(at.dataframe) == 5
    assert at.info  # sin espacio no hay cantidades derivadas: la pantalla lo dice


def test_la_pantalla_no_crea_la_base_si_no_existe(monkeypatch, tmp_path):
    base = tmp_path / "no_existe.db"
    _arrancar(monkeypatch, base)
    assert not base.exists()


def test_el_bano_sembrado_muestra_cantidades_derivadas_y_el_informe(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path / "no_existe.db", borrador=espacio_bano())
    texto = " ".join(m.value for m in at.markdown)
    assert "AF-TUB-PVC-3/4" in texto or any("AF-TUB-PVC-3/4" in str(d.value) for d in at.dataframe)
    assert "Informe de auditoria" in " ".join(s.value for s in at.subheader)
    assert "R8" in texto  # el informe declara las reglas del espacio


def test_el_estado_va_fuera_de_los_editores(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path / "no_existe.db", borrador=espacio_bano())
    estados = [d for d in at.dataframe if "Estado" in list(d.value.columns)]
    assert len(estados) == 3  # ambientes, fuentes y puntos


def test_la_primera_pestana_es_espacio_y_metrajes():
    assert PESTANAS[0] == "Espacio y metrajes"


def test_la_oficina_sembrada_muestra_las_tres_especialidades(monkeypatch, tmp_path):
    from tests.fixtures.espacio_of001 import espacio_of001

    at = _arrancar(monkeypatch, tmp_path / "no_existe.db", borrador=espacio_of001())
    cantidades = [d.value for d in at.dataframe if "Partida" in list(d.value.columns)]
    assert len(cantidades) == 1
    partidas = set(cantidades[0]["Partida"])
    assert {"AF-TUB-PVC-3/4", "DR-TUB-PVC-2", "DT-UTP-CAT-6", "EL-COND-12-AWG"} <= partidas
    estados = [d for d in at.dataframe if "Estado" in list(d.value.columns)]
    assert len(estados) == 3


# --- SF4: acciones que pide la barra superior --------------------------------------------------


def test_la_accion_precios_de_la_barra_elige_la_pestana_precios_si_existe(monkeypatch, tmp_path):
    from ui.caso import ACCION_PRECIOS, CLAVE_ACCION
    from ui.paginas import hoja as pantalla

    monkeypatch.setattr(pantalla, "PESTANAS", ("Espacio y metrajes", "Precios"))
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "no_existe.db"))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_ACCION] = ACCION_PRECIOS
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[pantalla.CLAVE_PESTANA] == "Precios"
    assert CLAVE_ACCION not in at.session_state  # la accion se consume


def test_la_accion_precios_sin_pestana_precios_no_cambia_la_pestana(monkeypatch, tmp_path):
    from ui.caso import ACCION_PRECIOS, CLAVE_ACCION
    from ui.paginas import hoja as pantalla

    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "no_existe.db"))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_ACCION] = ACCION_PRECIOS
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[pantalla.CLAVE_PESTANA] == pantalla.PESTANAS[0]
    assert CLAVE_ACCION not in at.session_state
