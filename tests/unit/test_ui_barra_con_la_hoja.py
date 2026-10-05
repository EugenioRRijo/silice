"""La barra superior conectada con la hoja real (integracion de SF3, SF4 y SF5).

Antes de integrar, la barra deshabilitaba Guardar version y Exportar Excel (la hoja no existia) y
ocultaba Importar plano. Aqui NO se parcha nada para decir que la hoja existe: se prueba con el
`ui.hoja` real, y el camino sin las funciones borrando los atributos. El guion corre la barra y la
pantalla de la hoja en la misma ejecucion, como las encadena la aplicacion al cambiar de pagina.
"""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from ui import barra
from ui.paginas.hoja import (
    CLAVE_EXCEL,
    CLAVE_PESTANA,
    CLAVE_PROYECTO,
    PESTANAS,
)

GUION = """
import streamlit as st
from ui.barra import pintar_barra
from ui.paginas.hoja import render

def ir_a(destino):
    st.session_state["destino"] = destino

pintar_barra("hoja", ir_a)
render()
"""
AVISO = "Guardar versión y Exportar Excel se habilitarán cuando la hoja del proyecto esté completa."


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("barra_hoja") / "of001.db")


@pytest.fixture
def base(_plantilla, tmp_path):
    copia = tmp_path / "of001.db"
    shutil.copy(_plantilla, copia)
    return copia


def _correr(monkeypatch, base: Path) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(GUION, default_timeout=120)
    at.session_state[CLAVE_PROYECTO] = NOMBRE_OF001
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _boton(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def _avisos(at: AppTest) -> list[str]:
    return [c.value for c in at.caption]


# --- con la hoja real --------------------------------------------------------------------------


def test_la_hoja_real_expone_las_dos_funciones_y_la_deteccion_da_disponible():
    hoja = importlib.import_module("ui.hoja")
    assert all(callable(getattr(hoja, nombre)) for nombre in barra.FUNCIONES_DE_SF3)
    assert barra.hay_guardado_y_exportacion() is True


@pytest.mark.parametrize("rotulo", [barra.ROTULO_GUARDAR, barra.ROTULO_EXPORTAR])
def test_con_la_hoja_real_los_botones_estan_habilitados_y_sin_aviso(monkeypatch, base, rotulo):
    at = _correr(monkeypatch, base)
    boton = _boton(at, rotulo)
    assert boton.disabled is False
    assert boton.help in (None, "")
    assert AVISO not in _avisos(at)
    assert "Todavía no está disponible" not in " ".join(
        [m.value for m in at.markdown] + _avisos(at) + [b.help or "" for b in at.button]
    )


@pytest.mark.parametrize("rotulo", [barra.ROTULO_GUARDAR, barra.ROTULO_EXPORTAR])
def test_sin_las_funciones_de_la_hoja_se_deshabilitan_y_queda_el_aviso(monkeypatch, base, rotulo):
    hoja = importlib.import_module("ui.hoja")
    monkeypatch.delattr(hoja, "guardar_version")
    monkeypatch.delattr(hoja, "exportar_excel")
    at = _correr(monkeypatch, base)
    boton = _boton(at, rotulo)
    assert boton.disabled is True
    assert AVISO in _avisos(at)


def test_con_solo_una_de_las_dos_funciones_tampoco_se_habilitan(monkeypatch, base):
    hoja = importlib.import_module("ui.hoja")
    monkeypatch.delattr(hoja, "exportar_excel")
    at = _correr(monkeypatch, base)
    assert _boton(at, barra.ROTULO_GUARDAR).disabled is True
    assert _boton(at, barra.ROTULO_EXPORTAR).disabled is True


# --- de la barra a la accion en la hoja --------------------------------------------------------


def test_exportar_excel_de_la_barra_prepara_el_libro_en_la_hoja(monkeypatch, base):
    at = _correr(monkeypatch, base)
    assert CLAVE_EXCEL not in at.session_state
    _boton(at, barra.ROTULO_EXPORTAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["destino"] == "hoja"
    nombre, contenido = at.session_state[CLAVE_EXCEL]
    assert nombre == "hoja_001.xlsx" and contenido[:2] == b"PK"
    assert len(at.get("download_button")) == 1


def test_guardar_version_de_la_barra_abre_el_panel_de_guardado_en_la_hoja(monkeypatch, base):
    at = _correr(monkeypatch, base)
    cerrado = next(e for e in at.expander if e.label.startswith("Guardar version"))
    assert cerrado.proto.expanded is False
    _boton(at, barra.ROTULO_GUARDAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["destino"] == "hoja"
    abierto = next(e for e in at.expander if e.label.startswith("Guardar version"))
    assert abierto.proto.expanded is True
    # sin cambios no hay nada que guardar: el boton de la hoja lo dice y no guarda nada
    assert next(b for b in at.button if b.label == "Guardar version" and b.help).disabled


def test_precios_de_la_barra_lleva_a_la_pestana_precios_de_la_hoja(monkeypatch, base):
    assert "Precios" in PESTANAS  # RS4-4: la pestana ya existe, asi que no va a Actualizar precios
    at = _correr(monkeypatch, base)
    _boton(at, barra.ROTULO_PRECIOS).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["destino"] == "hoja"
    assert at.session_state[CLAVE_PESTANA] == "Precios"
    assert any("Referencia" in d.value.columns for d in at.dataframe)


# --- Importar plano ----------------------------------------------------------------------------


def test_importar_plano_aparece_con_el_paquete_de_planos_real_y_lleva_al_flujo(monkeypatch, base):
    assert barra.hay_importacion_de_planos() is True
    at = _correr(monkeypatch, base)
    _boton(at, barra.ROTULO_IMPORTAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["destino"] == "hoja"
    assert at.session_state[CLAVE_PESTANA] == "Espacio y metrajes"
    flujo = next(e for e in at.expander if e.label == "Importar plano (DXF o IFC)")
    assert flujo.proto.expanded is True
