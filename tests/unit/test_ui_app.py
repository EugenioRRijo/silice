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

import pytest
from streamlit.testing.v1 import AppTest

from tests.conftest import RUTA_BASE_REAL, huella
from ui.app import (
    CLAVE_BOTON_SIGUIENTE,
    PAGINA_INICIO,
    PAGINAS,
    ROTULO_SIGUIENTE,
    SECCION_ADMINISTRACION,
    SECCION_INVESTIGACION,
    SECCION_REVISION,
    SECCION_TRABAJO,
    VARIABLE_MODO_ENTREGA,
    modo_entrega_activo,
    pagina_por_ruta,
    paginas_visibles,
    ruta_actual,
    secciones_visibles,
)
from ui.caso import CLAVE_RECORRIDO, estado_caso, resumen_caso
from ui.paginas.inicio import ROTULO_RECORRIDO
from ui.recorridos import NOMBRE_DEMOSTRACION, RECORRIDOS, RUTA_INICIO

TITULOS_TRABAJO = (
    "Inicio",
    "Tablero del proyecto",
    "Catalogo de partidas e insumos",
    "Componer una partida",
    "Elaborar un presupuesto",
    "Hoja del proyecto",
    "Actualizar precios",
    "Historico de cambios de precio",
    "Precios de la empresa",
    "Indices del BCV",
    "Reajuste de precios",
    "Control de obra",
    "Acerca de Sílice",
    "Entregar paquete",
    "Existencias de la arenera",
)

TITULOS_REVISION = ("Revisar un paquete", "Libro de la empresa")

#: RF-42 (S3 §5.7): Administración es la cuarta sección, no una pantalla de Trabajo.
TITULOS_ADMINISTRACION = ("Administración",)

TITULOS_INVESTIGACION = (
    "Escenarios de sensibilidad",
    "Partidas similares",
    "Simulador de listas",
)

CASOS_DE_USO = {
    "actualizacion": "UC-02",
    "administracion": "UC-21",
    "componer": "UC-10 / UC-11",
    "control": "UC-19 / UC-20",
    "elaborar": "UC-01",
    "entregar": "UC-22",
    "escenarios": "UC-08",
    "existencias": "UC-28 / UC-29",
    "indices": "UC-17",
    "libros": "UC-25",
    "precios_empresa": "UC-17",
    "reajuste": "UC-18",
    "revisar": "UC-23",
    "similares": "UC-03",
}


def _titulos(paginas) -> tuple[str, ...]:
    return tuple(pagina.titulo for pagina in paginas)


# --- secciones y orden (RF-42, RF-43) ---------------------------------------------------------


def test_sin_modo_entrega_cuatro_secciones_en_el_orden_del_trabajo() -> None:
    """RF-42 enmendado por S3 §5.7: Trabajo, Revisión, Investigación y Administración."""
    secciones = secciones_visibles(False)
    assert tuple(secciones) == (
        SECCION_TRABAJO, SECCION_REVISION, SECCION_INVESTIGACION, SECCION_ADMINISTRACION)
    assert _titulos(secciones[SECCION_TRABAJO]) == TITULOS_TRABAJO
    assert _titulos(secciones[SECCION_REVISION]) == TITULOS_REVISION
    assert _titulos(secciones[SECCION_INVESTIGACION]) == TITULOS_INVESTIGACION
    assert _titulos(secciones[SECCION_ADMINISTRACION]) == TITULOS_ADMINISTRACION


def test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo() -> None:
    secciones = secciones_visibles(True)
    assert tuple(secciones) == (SECCION_TRABAJO, SECCION_REVISION, SECCION_ADMINISTRACION)
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


def test_las_pantallas_con_caso_de_uso_lo_declaran() -> None:
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
    assert len(set(rutas)) == len(rutas) == (
        len(TITULOS_TRABAJO)
        + len(TITULOS_REVISION)
        + len(TITULOS_INVESTIGACION)
        + len(TITULOS_ADMINISTRACION)
    )
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


# --- el marco alrededor de cada pantalla (RF-38, RF-39, RF-41, RF-42) --------------------------
#
# `AppTest` no puede navegar entre paginas definidas por callable (spec de UI, §6): cada pantalla se
# pinta por separado dentro de `marco()`, con el caso fijado en un temporal y un `ir_a` que solo
# registra el destino en la sesion.

SCRIPT_MARCO = """
import streamlit as st
from ui.app import marco, pagina_por_ruta
definicion = pagina_por_ruta({ruta!r})

def ir_a(destino):
    st.session_state["destino"] = destino

marco(definicion, definicion.render, ir_a)
"""


@pytest.fixture(scope="module")
def base_sembrada(tmp_path_factory) -> Path:
    from core.catalog import abrir_sesion, crear_esquema, crear_motor
    from operacion.base_datos import preparar_base
    from scripts.seed import sembrar

    base = tmp_path_factory.mktemp("marco") / "caso.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    # La base sembrada con `crear_esquema` se adopta una vez (RV-5): así todas las pantallas ven el
    # mismo estado y ninguna la migra a mitad de la parametrizacion. El juego va a una carpeta
    # temporal: esta fixture es de modulo y corre antes de la `SILICE_DATOS` de cada prueba.
    preparar_base(base, entorno={"SILICE_DATOS": str(base.parent / "datos")})
    return base


def _marco(monkeypatch, base: Path, ruta: str, estado: dict[str, object] | None = None) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT_MARCO.format(ruta=ruta), default_timeout=120)
    for clave, valor in (estado or {}).items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    return at


@pytest.mark.parametrize("ruta", [pagina.ruta_url for pagina in PAGINAS])
def test_cada_pantalla_muestra_el_caso_abierto_y_su_titulo(
    monkeypatch, base_sembrada, ruta
) -> None:
    at = _marco(monkeypatch, base_sembrada, ruta)
    leyendas = [leyenda.value for leyenda in at.sidebar.caption]
    assert str(base_sembrada) in leyendas
    assert resumen_caso(estado_caso(base_sembrada)) in leyendas
    definicion = pagina_por_ruta(ruta)
    assert [titulo.value for titulo in at.title] == [definicion.titulo]
    if definicion.caso_uso is not None:
        assert f"Caso de uso {definicion.caso_uso}" in [c.value for c in at.main.caption]


@pytest.mark.parametrize(
    "ruta", [pagina.ruta_url for pagina in PAGINAS if pagina.ruta_url != "inicio"]
)
def test_ninguna_pantalla_distinta_del_inicio_pide_la_ruta(
    monkeypatch, base_sembrada, ruta
) -> None:
    at = _marco(monkeypatch, base_sembrada, ruta)
    rotulos = [campo.label for campo in at.text_input]
    assert not any("SQLite" in rotulo for rotulo in rotulos), rotulos


def test_la_barra_lateral_indica_el_paso_del_recorrido(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "catalogo", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    leyendas = [leyenda.value for leyenda in at.sidebar.caption]
    assert "Paso 1 de 2: Ver el catalogo del caso" in leyendas


def test_el_boton_siguiente_lleva_al_paso_que_sigue(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "catalogo", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    boton = at.button(key=CLAVE_BOTON_SIGUIENTE)
    assert boton.label == ROTULO_SIGUIENTE.format("Elaborar, auditar y exportar")
    boton.click().run()
    assert at.session_state["destino"] == "componer"


def test_desde_el_inicio_el_siguiente_es_el_primer_paso(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "inicio", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    at.button(key=CLAVE_BOTON_SIGUIENTE).click().run()
    assert at.session_state["destino"] == "catalogo"


def test_en_el_ultimo_paso_no_hay_siguiente(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "componer", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    assert CLAVE_BOTON_SIGUIENTE not in {boton.key for boton in at.button}


def test_una_pantalla_fuera_del_recorrido_no_muestra_siguiente(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "historico", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    assert CLAVE_BOTON_SIGUIENTE not in {boton.key for boton in at.button}


# --- SF4 4.1: navegacion arriba (RF-60) y once pantallas (RF-37, RF-39, RF-42) -----------------


def test_el_extra_ui_exige_la_version_de_streamlit_con_navegacion_superior() -> None:
    """`position="top"` existe desde Streamlit 1.62 (la fija el extra `ui` de pyproject.toml)."""
    import tomllib

    datos = tomllib.loads((RUTA_APP.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    requisitos = [r.replace(" ", "") for r in datos["project"]["optional-dependencies"]["ui"]]
    assert "streamlit>=1.62" in requisitos


def test_el_streamlit_instalado_acepta_navigation_con_position_top() -> None:
    """Falla con una version de Streamlit sin la navegacion superior."""
    import inspect

    import streamlit as st

    parametros = inspect.signature(st.navigation).parameters
    assert "position" in parametros
    assert "top" in str(parametros["position"].annotation)


def test_la_aplicacion_declara_la_navegacion_arriba_con_los_dos_grupos(
    monkeypatch, tmp_path: Path
) -> None:
    import streamlit as st

    llamadas: list[tuple[object, dict[str, object]]] = []
    original = st.navigation

    def espia(paginas, **kwargs):
        llamadas.append((paginas, kwargs))
        return original(paginas, **kwargs)

    monkeypatch.setattr(st, "navigation", espia)
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    assert len(llamadas) == 1
    paginas, kwargs = llamadas[0]
    assert kwargs.get("position") == "top"
    assert list(paginas) == [
        SECCION_TRABAJO, SECCION_REVISION, SECCION_INVESTIGACION, SECCION_ADMINISTRACION]


def test_modo_entrega_declara_solo_el_grupo_trabajo_en_la_navegacion_superior(
    monkeypatch, tmp_path: Path
) -> None:
    import streamlit as st

    llamadas: list[tuple[object, dict[str, object]]] = []
    original = st.navigation

    def espia(paginas, **kwargs):
        llamadas.append((paginas, kwargs))
        return original(paginas, **kwargs)

    monkeypatch.setattr(st, "navigation", espia)
    monkeypatch.setenv(VARIABLE_MODO_ENTREGA, "1")
    _aplicacion(monkeypatch, tmp_path)
    paginas, kwargs = llamadas[0]
    assert kwargs.get("position") == "top"
    assert list(paginas) == [SECCION_TRABAJO, SECCION_REVISION, SECCION_ADMINISTRACION]


def test_son_veintiuna_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
    rutas = [p.ruta_url for p in PAGINAS]
    assert len(rutas) == 21
    assert rutas.index("hoja") == rutas.index("elaborar") + 1
    assert pagina_por_ruta("hoja").seccion == SECCION_TRABAJO


# --- SF4 4.2: la barra de herramientas va en el marco (RF-60) ----------------------------------

ROTULOS_DE_LA_BARRA = ("Precios", "Guardar version", "Exportar Excel", "Recorrido guiado")


def _rotulos_de_botones(at: AppTest) -> list[str]:
    return [boton.label for boton in at.button]


def test_la_aplicacion_pinta_la_barra_encima_de_la_pantalla(monkeypatch, tmp_path: Path) -> None:
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    rotulos = _rotulos_de_botones(at)
    for esperado in ROTULOS_DE_LA_BARRA:
        assert esperado in rotulos
    assert [p.proto.popover.label for p in at.get("popover")] == ["Proyecto", "Auditar"]


def test_el_modo_entrega_conserva_la_barra_completa(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(VARIABLE_MODO_ENTREGA, "1")
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    for esperado in ROTULOS_DE_LA_BARRA:
        assert esperado in _rotulos_de_botones(at)


def test_la_barra_se_pinta_antes_que_el_titulo_de_cada_pantalla(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "catalogo")
    assert "Recorrido guiado" in _rotulos_de_botones(at)
    assert [titulo.value for titulo in at.title] == ["Catalogo de partidas e insumos"]


def test_el_boton_de_la_barra_lleva_a_la_pantalla_con_ir_a(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "catalogo")
    next(b for b in at.button if b.label == "Precios").click().run()
    # integrada la hoja (SF3), Precios lleva a su pestana en la hoja (RS4-4), no a Actualizacion
    assert at.session_state["destino"] == "hoja"


def test_el_modo_entrega_mantiene_importar_plano_y_guardar_y_oculta_investigacion(
    monkeypatch, tmp_path: Path
) -> None:
    import streamlit as st

    from ui import barra

    llamadas: list[object] = []
    original = st.navigation

    def espia(paginas, **kwargs):
        llamadas.append(paginas)
        return original(paginas, **kwargs)

    monkeypatch.setattr(st, "navigation", espia)
    monkeypatch.setattr(barra, "hay_importacion_de_planos", lambda *a: True)
    monkeypatch.setenv(VARIABLE_MODO_ENTREGA, "1")
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    rotulos = _rotulos_de_botones(at)
    assert "Importar plano" in rotulos
    assert "Guardar version" in rotulos
    # ninguna seccion de Investigacion
    assert list(llamadas[0]) == [SECCION_TRABAJO, SECCION_REVISION, SECCION_ADMINISTRACION]
