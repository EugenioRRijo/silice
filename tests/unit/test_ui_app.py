"""Pruebas del enrutador y marco comun de `ui/app.py` (sprint de UI; antes, Sesion P5.1).

Reescritas a proposito en el sprint de UI (spec, §6): el menu paso de nueve pantallas en orden
alfabetico a diez en dos secciones con nombres de oficio, y el Inicio es la pagina por defecto.
Cambian porque cambio el comportamiento **especificado**, no porque fallaran. Sobrevive intacta la
afirmacion de que todas las rutas URL son unicas: nacio de un fallo real (`a478cfc`).

Secciones, orden, filtro del modo entrega e integridad de enlaces son funciones puras sobre
`DefinicionPagina`, que no es de Streamlit. El marco se prueba con `AppTest` desviando la base a un
temporal por el objeto modulo `sys.modules["ui.caso"]`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.conftest import RUTA_BASE_REAL, huella
from ui.app import (
    PAGINA_INICIO,
    PAGINAS,
    SECCION_INVESTIGACION,
    SECCION_TRABAJO,
    VARIABLE_MODO_ENTREGA,
    modo_entrega_activo,
    pagina_por_ruta,
    paginas_visibles,
    ruta_actual,
    secciones_visibles,
)
from ui.paginas.inicio import ROTULO_RECORRIDO
from ui.recorridos import RECORRIDOS, RUTA_INICIO

TITULOS_TRABAJO = (
    "Inicio",
    "Catalogo de partidas e insumos",
    "Componer una partida",
    "Elaborar un presupuesto",
    "Actualizar precios",
    "Historico de cambios de precio",
)

TITULOS_INVESTIGACION = (
    "Escenarios de sensibilidad",
    "Partidas similares",
    "Simulador de listas",
    "Visor 3D del modelo",
)

CASOS_DE_USO = {
    "actualizacion": "UC-02",
    "componer": "UC-10 / UC-11",
    "elaborar": "UC-01",
    "escenarios": "UC-08",
    "similares": "UC-03",
}


def _titulos(paginas) -> tuple[str, ...]:
    return tuple(pagina.titulo for pagina in paginas)


# --- secciones y orden (RF-42, RF-43) ---------------------------------------------------------


def test_sin_modo_entrega_dos_secciones_en_el_orden_del_trabajo() -> None:
    secciones = secciones_visibles(False)
    assert tuple(secciones) == (SECCION_TRABAJO, SECCION_INVESTIGACION)
    assert _titulos(secciones[SECCION_TRABAJO]) == TITULOS_TRABAJO
    assert _titulos(secciones[SECCION_INVESTIGACION]) == TITULOS_INVESTIGACION


def test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo() -> None:
    secciones = secciones_visibles(True)
    assert tuple(secciones) == (SECCION_TRABAJO,)
    assert secciones[SECCION_TRABAJO] == secciones_visibles(False)[SECCION_TRABAJO]


def test_paginas_visibles_es_la_concatenacion_de_las_secciones() -> None:
    for modo in (False, True):
        concatenadas = tuple(p for grupo in secciones_visibles(modo).values() for p in grupo)
        assert paginas_visibles(modo) == concatenadas


def test_modo_entrega_solo_se_activa_con_el_valor_exacto_1() -> None:
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "1"}) is True
    assert modo_entrega_activo({}) is False
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "0"}) is False
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "si"}) is False


def test_ningun_titulo_lleva_codigo_de_caso_de_uso() -> None:
    assert [p.titulo for p in PAGINAS if "UC-" in p.titulo or "UC‑" in p.titulo] == []


def test_las_cinco_pantallas_con_caso_de_uso_lo_declaran() -> None:
    declarados = {p.ruta_url: p.caso_uso for p in PAGINAS if p.caso_uso is not None}
    assert declarados == CASOS_DE_USO


# --- Inicio por defecto (RF-36) ---------------------------------------------------------------


def test_el_inicio_es_la_primera_pagina_y_la_unica_por_defecto() -> None:
    assert PAGINAS[0] is PAGINA_INICIO
    assert PAGINA_INICIO.ruta_url == RUTA_INICIO
    assert sum(1 for p in PAGINAS if p is PAGINA_INICIO) == 1


def test_la_ruta_vacia_de_la_pagina_por_defecto_es_el_inicio() -> None:
    # Streamlit 1.62 devuelve url_path == "" para la pagina marcada default=True
    # (streamlit/navigation/page.py:414).
    assert ruta_actual("") == RUTA_INICIO
    assert ruta_actual("componer") == "componer"


def test_cada_pagina_tiene_una_ruta_url_propia() -> None:
    rutas = [pagina.ruta_url for pagina in paginas_visibles(False)]
    assert len(set(rutas)) == len(rutas) == len(TITULOS_TRABAJO) + len(TITULOS_INVESTIGACION)
    assert "componer" in rutas


def test_pagina_por_ruta() -> None:
    assert pagina_por_ruta("componer").titulo == "Componer una partida"


# --- integridad de enlaces de los recorridos (RF-37, RF-43) -----------------------------------


def test_todo_paso_apunta_a_una_pagina_registrada() -> None:
    registradas = {p.ruta_url for p in paginas_visibles(False)}
    for recorrido in RECORRIDOS:
        for paso in recorrido.pasos:
            assert paso.pagina in registradas, (recorrido.nombre, paso.pagina)


def test_ningun_paso_sale_de_la_seccion_trabajo() -> None:
    en_modo_entrega = {p.ruta_url for p in paginas_visibles(True)}
    for recorrido in RECORRIDOS:
        for paso in recorrido.pasos:
            assert paso.pagina in en_modo_entrega, (recorrido.nombre, paso.pagina)


# --- la aplicacion completa arranca en el Inicio ----------------------------------------------

RUTA_APP = Path(__file__).resolve().parents[2] / "ui" / "app.py"


def _aplicacion(monkeypatch, tmp_path: Path) -> AppTest:
    caso = importlib.import_module("ui.caso")
    temporal = tmp_path / "app.db"
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(temporal))
    antes = huella(RUTA_BASE_REAL)
    at = AppTest.from_file(str(RUTA_APP), default_timeout=60)
    at.run()
    # INV-022: la desviacion surtio efecto (el marco muestra el temporal) y la base real no cambio.
    assert str(temporal) in [leyenda.value for leyenda in at.sidebar.caption]
    assert huella(RUTA_BASE_REAL) == antes
    return at


def test_la_aplicacion_arranca_en_el_inicio(monkeypatch, tmp_path: Path) -> None:
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    assert at.title[0].value == "Inicio"
    assert any(radio.label == ROTULO_RECORRIDO for radio in at.radio)


def test_la_aplicacion_arranca_en_modo_entrega(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(VARIABLE_MODO_ENTREGA, "1")
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    assert at.title[0].value == "Inicio"
