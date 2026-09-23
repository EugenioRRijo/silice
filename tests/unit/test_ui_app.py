"""Pruebas del modo entrega de `ui/app.py` (Sesion P5.1, prototipo AREN.IA).

El filtro de pantallas es una funcion pura sobre `DefinicionPagina`, que no es de Streamlit: se
prueba sin construir ningun `st.Page` ni arrancar la aplicacion.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.app import VARIABLE_MODO_ENTREGA, modo_entrega_activo, paginas_visibles

TITULOS_NUEVE = (
    "Actualizacion de precios (UC-02)",
    "Catalogo",
    "Componer partida (UC-10 / UC-11)",
    "Elaborar presupuesto (UC-01)",
    "Escenarios (UC-08)",
    "Historico de precios",
    "Partidas similares (UC-03)",
    "Simulador de listas",
    "Visor 3D",
)

TITULOS_ARENIA = (
    "Actualizacion de precios (UC-02)",
    "Catalogo",
    "Componer partida (UC-10 / UC-11)",
    "Elaborar presupuesto (UC-01)",
    "Historico de precios",
)

TITULOS_INVESTIGACION = (
    "Escenarios (UC-08)",
    "Partidas similares (UC-03)",
    "Simulador de listas",
    "Visor 3D",
)


def test_sin_modo_entrega_se_ven_las_nueve_en_el_orden_de_hoy() -> None:
    titulos = tuple(pagina.titulo for pagina in paginas_visibles(False))
    assert titulos == TITULOS_NUEVE


def test_modo_entrega_muestra_exactamente_las_cinco_de_arenia_en_orden() -> None:
    titulos = tuple(pagina.titulo for pagina in paginas_visibles(True))
    assert titulos == TITULOS_ARENIA


def test_modo_entrega_oculta_las_cuatro_de_investigacion() -> None:
    titulos = {pagina.titulo for pagina in paginas_visibles(True)}
    assert titulos.isdisjoint(TITULOS_INVESTIGACION)
    assert all(not pagina.investigacion for pagina in paginas_visibles(True))


def test_modo_entrega_solo_se_activa_con_el_valor_exacto_1() -> None:
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "1"}) is True
    assert modo_entrega_activo({}) is False
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "0"}) is False
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "si"}) is False


# --- La aplicacion completa arranca -----------------------------------------------------------
#
# Las pruebas de arriba no construyen ningun `st.Page`, y por eso no vieron que las nueve paginas
# registradas con una funcion llamada `render` chocan en `st.navigation`: Streamlit infiere de ese
# nombre la ruta URL de cada pagina y exige que sean unicas. `AppTest.from_file` ejecuta
# `ui/app.py` de verdad, como `streamlit run`. La pagina por defecto (actualizacion de precios)
# abre su base al pintarse: se desvia a un temporal parcheando el modulo de `sys.modules`, el
# mismo que importa el guion (`tests/unit/test_ui_componer.py` explica por que no la ruta en
# cadena).

RUTA_APP = Path(__file__).resolve().parents[2] / "ui" / "app.py"


def _aplicacion(monkeypatch, tmp_path: Path) -> AppTest:
    pagina = importlib.import_module("ui.paginas.actualizacion")
    monkeypatch.setattr(pagina, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "app.db"))
    at = AppTest.from_file(str(RUTA_APP), default_timeout=60)
    at.run()
    return at


def test_cada_pagina_tiene_una_ruta_url_propia() -> None:
    rutas = [pagina.ruta_url for pagina in paginas_visibles(False)]
    assert len(set(rutas)) == len(rutas) == len(TITULOS_NUEVE)
    assert "componer" in rutas


def test_la_aplicacion_arranca_sin_excepcion(monkeypatch, tmp_path: Path) -> None:
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]


def test_la_aplicacion_arranca_en_modo_entrega(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(VARIABLE_MODO_ENTREGA, "1")
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
