"""La barra de herramientas del marco (SF4, RF-60 y RF-63, spec §10): una prueba `AppTest` por
herramienta. `pintar_barra(ruta, ir_a)` se corre dentro de un guion con un `ir_a` que solo anota el
destino en la sesion (el mismo arnes que `test_ui_app.py` usa para el marco). Las herramientas que
dependen de SF3 (Guardar version, Exportar Excel) y de SF5 (Importar plano) se prueban en sus dos
estados parchando el objeto modulo que las detecta.
"""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from scripts.seed import NOMBRE_PROYECTO
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.base_con_pendiente import guardar_base_con_pendiente
from ui import barra
from ui.caso import (
    ACCION_EXPORTAR_EXCEL,
    ACCION_GUARDAR_VERSION,
    ACCION_IMPORTAR_PLANO,
    ACCION_PRECIOS,
    CLAVE_ACCION,
    CLAVE_PROYECTO,
    CLAVE_RECORRIDO,
)
from ui.recorridos import NOMBRE_DEMOSTRACION, RECORRIDOS

SCRIPT = """
import streamlit as st
from ui.barra import pintar_barra

def ir_a(destino):
    st.session_state["destino"] = destino

pintar_barra({ruta!r}, ir_a)
"""

ACCIONES_SF3 = [
    (barra.ROTULO_GUARDAR, ACCION_GUARDAR_VERSION),
    (barra.ROTULO_EXPORTAR, ACCION_EXPORTAR_EXCEL),
]


@pytest.fixture(scope="module")
def caso_con_version(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("barra") / "caso.db"
    resultado = guardar_base_con_pendiente(ruta)
    return ruta, resultado


@pytest.fixture
def caso(tmp_path, caso_con_version):
    """Copia del caso para las pruebas que escriben (crear proyectos)."""
    ruta = tmp_path / "caso.db"
    shutil.copy(caso_con_version[0], ruta)
    return ruta


def _barra(monkeypatch, base: Path, ruta: str = "catalogo", estado=None) -> AppTest:
    caso_ui = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso_ui, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT.format(ruta=ruta), default_timeout=120)
    for clave, valor in (estado or {}).items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _boton(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def _rotulos(at: AppTest) -> list[str]:
    """Los botones de la barra; los de dentro del popover Proyecto (crear, abrir) no cuentan."""
    return [b.label for b in at.button if b.label not in (barra.ROTULO_CREAR, barra.ROTULO_ABRIR)]


def _textos(at: AppTest) -> str:
    return " ".join(
        [m.value for m in at.markdown]
        + [c.value for c in at.caption]
        + [e.value for e in at.error]
        + [s.value for s in at.success]
        + [i.value for i in at.info]
    )


def _abierto(at: AppTest):
    return at.session_state[CLAVE_PROYECTO] if CLAVE_PROYECTO in at.session_state else None


def _sin_funciones_de_sf3(monkeypatch) -> None:
    hoja = importlib.import_module("ui.hoja")
    for nombre in barra.FUNCIONES_DE_SF3:
        monkeypatch.delattr(hoja, nombre, raising=False)


def _con_funciones_de_sf3(monkeypatch) -> None:
    hoja = importlib.import_module("ui.hoja")
    for nombre in barra.FUNCIONES_DE_SF3:
        monkeypatch.setattr(hoja, nombre, lambda *a, **k: None, raising=False)


# --- deteccion de lo que todavia no existe -----------------------------------------------------


def test_importar_plano_se_detecta_por_el_paquete_de_planos_en_disco():
    """Oraculo independiente: la carpeta `adapters/espacio/planos` existe o no en el disco."""
    raiz = Path(__file__).resolve().parents[2]
    en_disco = (raiz / "adapters" / "espacio" / "planos" / "__init__.py").is_file()
    assert barra.hay_importacion_de_planos() is en_disco


def test_hay_importacion_de_planos_con_un_buscador_que_encuentra_o_no():
    assert barra.hay_importacion_de_planos(lambda nombre: object()) is True
    assert barra.hay_importacion_de_planos(lambda nombre: None) is False

    def sin_paquete(nombre):
        raise ModuleNotFoundError(nombre)

    assert barra.hay_importacion_de_planos(sin_paquete) is False


def test_guardar_y_exportar_dependen_de_las_dos_funciones_de_ui_hoja(monkeypatch):
    hoja = importlib.import_module("ui.hoja")
    _sin_funciones_de_sf3(monkeypatch)
    assert barra.hay_guardado_y_exportacion() is False
    monkeypatch.setattr(hoja, barra.FUNCIONES_DE_SF3[0], lambda: None, raising=False)
    assert barra.hay_guardado_y_exportacion() is False  # con una sola no basta
    monkeypatch.setattr(hoja, barra.FUNCIONES_DE_SF3[1], lambda: None, raising=False)
    assert barra.hay_guardado_y_exportacion() is True


# --- la barra y sus herramientas ---------------------------------------------------------------


def test_la_barra_oculta_importar_plano_mientras_sf5_no_llega(monkeypatch, caso_con_version):
    monkeypatch.setattr(barra, "hay_importacion_de_planos", lambda *a: False)
    at = _barra(monkeypatch, caso_con_version[0])
    assert _rotulos(at) == [
        barra.ROTULO_PRECIOS,
        barra.ROTULO_GUARDAR,
        barra.ROTULO_EXPORTAR,
        barra.ROTULO_RECORRIDO,
    ]
    assert [p.proto.popover.label for p in at.get("popover")] == [barra.ROTULO_PROYECTO, barra.ROTULO_AUDITAR]


def test_importar_plano_aparece_si_existe_el_paquete_y_lleva_a_la_hoja(
    monkeypatch, caso_con_version
):
    monkeypatch.setattr(barra, "hay_importacion_de_planos", lambda *a: True)
    at = _barra(monkeypatch, caso_con_version[0])
    assert barra.ROTULO_IMPORTAR in _rotulos(at)
    _boton(at, barra.ROTULO_IMPORTAR).click().run()
    assert at.session_state["destino"] == "hoja"
    assert at.session_state[CLAVE_ACCION] == ACCION_IMPORTAR_PLANO


@pytest.mark.parametrize(("rotulo", "accion"), ACCIONES_SF3)
def test_guardar_y_exportar_estan_deshabilitados_hasta_que_llegue_sf3(
    monkeypatch, caso_con_version, rotulo, accion
):
    _sin_funciones_de_sf3(monkeypatch)
    at = _barra(monkeypatch, caso_con_version[0])
    boton = _boton(at, rotulo)
    assert boton.disabled is True
    assert boton.help == "disponible cuando se complete SF3"
    assert "destino" not in at.session_state


@pytest.mark.parametrize(("rotulo", "accion"), ACCIONES_SF3)
def test_guardar_y_exportar_se_habilitan_y_se_delegan_en_la_hoja(
    monkeypatch, caso_con_version, rotulo, accion
):
    _con_funciones_de_sf3(monkeypatch)
    at = _barra(monkeypatch, caso_con_version[0])
    boton = _boton(at, rotulo)
    assert boton.disabled is False
    boton.click().run()
    assert at.session_state["destino"] == "hoja"
    assert at.session_state[CLAVE_ACCION] == accion


def test_precios_sin_pestana_precios_lleva_a_actualizar_precios(monkeypatch, caso_con_version):
    paginas_hoja = importlib.import_module("ui.paginas.hoja")
    monkeypatch.setattr(paginas_hoja, "PESTANAS", ("Espacio y metrajes",))
    at = _barra(monkeypatch, caso_con_version[0])
    _boton(at, barra.ROTULO_PRECIOS).click().run()
    assert at.session_state["destino"] == "actualizacion"
    assert CLAVE_ACCION not in at.session_state


def test_precios_con_pestana_precios_lleva_a_la_hoja(monkeypatch, caso_con_version):
    paginas_hoja = importlib.import_module("ui.paginas.hoja")
    monkeypatch.setattr(paginas_hoja, "PESTANAS", ("Espacio y metrajes", "Precios"))
    at = _barra(monkeypatch, caso_con_version[0])
    _boton(at, barra.ROTULO_PRECIOS).click().run()
    assert at.session_state["destino"] == "hoja"
    assert at.session_state[CLAVE_ACCION] == ACCION_PRECIOS


# --- Recorrido guiado (UC-12) ------------------------------------------------------------------


def test_recorrido_guiado_sin_recorrido_activo_lleva_al_inicio(monkeypatch, caso_con_version):
    at = _barra(monkeypatch, caso_con_version[0], "catalogo")
    _boton(at, barra.ROTULO_RECORRIDO).click().run()
    assert at.session_state["destino"] == "inicio"


def test_recorrido_guiado_retoma_el_paso_que_sigue(monkeypatch, caso_con_version):
    estado = {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION}
    at = _barra(monkeypatch, caso_con_version[0], "catalogo", estado)
    _boton(at, barra.ROTULO_RETOMAR.format(NOMBRE_DEMOSTRACION)).click().run()
    assert at.session_state["destino"] == "componer"


def test_recorrido_guiado_desde_fuera_del_recorrido_vuelve_a_su_primer_paso(
    monkeypatch, caso_con_version
):
    estado = {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION}
    at = _barra(monkeypatch, caso_con_version[0], "historico", estado)
    _boton(at, barra.ROTULO_RETOMAR.format(NOMBRE_DEMOSTRACION)).click().run()
    primero = next(r for r in RECORRIDOS if r.nombre == NOMBRE_DEMOSTRACION).pasos[0].pagina
    assert at.session_state["destino"] == primero


def test_recorrido_guiado_desde_su_ultimo_paso_vuelve_al_inicio(monkeypatch, caso_con_version):
    estado = {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION}
    at = _barra(monkeypatch, caso_con_version[0], "componer", estado)
    _boton(at, barra.ROTULO_RETOMAR.format(NOMBRE_DEMOSTRACION)).click().run()
    assert at.session_state["destino"] == "inicio"


# --- Proyecto (RF-63) --------------------------------------------------------------------------


def _crear(at: AppTest, nombre: str) -> AppTest:
    at.text_input(key=barra.CLAVE_NOMBRE_NUEVO).set_value(nombre)
    return _boton(at, barra.ROTULO_CREAR).click().run()


def test_proyecto_muestra_el_caso_y_que_no_hay_proyecto_abierto(monkeypatch, caso):
    at = _barra(monkeypatch, caso)
    texto = _textos(at)
    assert str(caso) in texto
    assert "Ningun proyecto abierto" in texto


def test_proyecto_nuevo_con_nombre_vacio_se_rechaza_con_mensaje(monkeypatch, caso):
    at = _crear(_barra(monkeypatch, caso), "   ")
    assert "no puede quedar vacio" in _textos(at)
    assert _abierto(at) is None


def test_proyecto_nuevo_con_nombre_repetido_se_rechaza_con_mensaje(monkeypatch, caso):
    at = _crear(_barra(monkeypatch, caso), NOMBRE_PROYECTO.lower())
    assert "Ya existe un proyecto" in _textos(at)
    assert _abierto(at) is None


def test_proyecto_nuevo_valido_se_crea_se_abre_y_limpia_el_campo(monkeypatch, caso):
    at = _crear(_barra(monkeypatch, caso), "Torre B")
    assert at.session_state[CLAVE_PROYECTO] == "Torre B"
    texto = _textos(at)
    assert "Torre B" in texto
    assert "sin version guardada" in texto
    assert at.text_input(key=barra.CLAVE_NOMBRE_NUEVO).value == ""
    assert "Torre B" in at.selectbox(key=barra.CLAVE_ABRIR).options


def test_proyecto_nuevo_no_se_crea_dos_veces(monkeypatch, caso):
    at = _crear(_barra(monkeypatch, caso), "Torre B")
    at = _crear(at, "Torre B")
    assert "Ya existe un proyecto" in _textos(at)


def test_abrir_un_proyecto_muestra_su_version_vigente(monkeypatch, caso):
    at = _barra(monkeypatch, caso)
    at.selectbox(key=barra.CLAVE_ABRIR).select(NOMBRE_PROYECTO)
    _boton(at, barra.ROTULO_ABRIR).click().run()
    assert at.session_state[CLAVE_PROYECTO] == NOMBRE_PROYECTO
    texto = _textos(at)
    assert NOMBRE_PROYECTO in texto
    assert f"version vigente: {linea_base.CODIGO_PRESUPUESTO}" in texto


def test_un_proyecto_abierto_que_ya_no_esta_en_el_caso_se_trata_como_ninguno(monkeypatch, caso):
    at = _barra(monkeypatch, caso, estado={CLAVE_PROYECTO: "Fantasma"})
    assert "Ningun proyecto abierto" in _textos(at)


def test_sin_caso_crear_proyecto_dice_que_el_caso_no_existe(monkeypatch, tmp_path):
    at = _barra(monkeypatch, tmp_path / "no_existe.db")
    at = _crear(at, "Torre B")
    assert "no existe" in _textos(at)
    assert not (tmp_path / "no_existe.db").exists()


# --- Auditar -----------------------------------------------------------------------------------


def test_auditar_resume_el_informe_de_la_version_vigente(monkeypatch, caso_con_version):
    ruta, resultado = caso_con_version
    at = _barra(monkeypatch, ruta, estado={CLAVE_PROYECTO: NOMBRE_PROYECTO})
    texto = _textos(at)
    assert f"{len(resultado.informe.hallazgos)} hallazgo" in texto
    assert linea_base.CODIGO_PRESUPUESTO in texto


def test_auditar_sin_proyecto_abierto_lo_pide(monkeypatch, caso_con_version):
    at = _barra(monkeypatch, caso_con_version[0])
    assert "Abra un proyecto" in _textos(at)
