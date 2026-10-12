"""El marco por rol (RF-80, RF-37; S3 §5.1): lo que no depende de qué pantallas de S3 existen.

La navegación no es el control: se prueba la lista de pantallas de cada rol y, por separado, que
cada pantalla con acción la exige en la primera línea de su `render()` (AST). Las listas exactas
por rol, con Entregar, Revisar y Administración, están en `test_ui_roles.py`."""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seguridad.permisos import Rol
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import sesion as ui_sesion
from ui.app import PAGINAS, paginas_visibles
from ui.recorridos import RECORRIDOS, Paso, Recorrido

RUTA_APP = Path(__file__).resolve().parents[2] / "ui" / "app.py"


def _rutas(roles) -> list[str]:
    return [p.ruta_url for p in paginas_visibles(False, frozenset(roles))]


def test_el_rol_arma_ve_lo_de_trabajo_y_no_ve_la_administracion() -> None:
    rutas = set(_rutas({Rol.ARMA}))
    assert {"inicio", "catalogo", "componer", "elaborar", "hoja", "actualizacion", "historico",
            "escenarios", "similares", "simulador", "visor"} <= rutas
    assert "administracion" not in rutas


def test_el_rol_revisa_ve_la_lectura_y_nada_que_escriba() -> None:
    rutas = set(_rutas({Rol.REVISA}))
    assert {"inicio", "catalogo", "historico"} <= rutas
    assert not {"componer", "elaborar", "hoja", "actualizacion", "escenarios", "similares",
                "simulador", "visor"} & rutas


def test_el_administrador_no_ve_ninguna_pantalla_de_trabajo() -> None:
    rutas = set(_rutas({Rol.ADMINISTRADOR}))
    assert "inicio" in rutas
    assert not {"catalogo", "componer", "elaborar", "hoja", "actualizacion", "historico",
                "escenarios", "similares", "simulador", "visor"} & rutas


def test_varios_roles_suman_sus_pantallas_sin_repetir() -> None:
    todas = _rutas(set(Rol))
    assert todas == [p.ruta_url for p in PAGINAS] and len(set(todas)) == len(todas)


def test_sin_roles_solo_queda_lo_que_no_pide_accion() -> None:
    assert _rutas(set()) == ["inicio"]


def test_toda_pantalla_menos_el_inicio_declara_la_accion_que_la_protege() -> None:
    """Una pantalla nueva (también las de S1 y S2) sin `accion` la vería cualquier cuenta."""
    assert [p.ruta_url for p in PAGINAS if p.accion is None] == ["inicio"]


def test_un_recorrido_omite_los_pasos_de_pantallas_que_el_rol_no_ve() -> None:
    recorrido = next(r for r in RECORRIDOS if len(r.pasos) >= 3)
    visibles = {recorrido.pasos[0].pagina, recorrido.pasos[2].pagina}
    filtrado = recorrido.visible_en(visibles)
    assert [p.pagina for p in filtrado.pasos] == [recorrido.pasos[0].pagina,
                                                  recorrido.pasos[2].pagina]
    assert recorrido.visible_en(set()) is None
    assert all(isinstance(p, Paso) for p in filtrado.pasos) and isinstance(filtrado, Recorrido)


def _primera_instruccion(pagina) -> str:
    """El código de la primera instrucción de `render()` tras el docstring."""
    modulo = ast.parse(textwrap.dedent(inspect.getsource(inspect.getmodule(pagina.render))))
    render = next(n for n in modulo.body if isinstance(n, ast.FunctionDef) and n.name == "render")
    cuerpo = render.body
    if isinstance(cuerpo[0], ast.Expr) and isinstance(cuerpo[0].value, ast.Constant):
        cuerpo = cuerpo[1:]
    return ast.unparse(cuerpo[0])


@pytest.mark.parametrize("pagina", [p for p in PAGINAS if p.accion is not None],
                         ids=lambda p: p.ruta_url)
def test_cada_render_exige_su_accion_en_la_primera_linea(pagina) -> None:
    esperada = f"ui_sesion.exigir(Accion.{pagina.accion.name})"
    assert _primera_instruccion(pagina) in {esperada, f"sesion = {esperada}"}


# --- la aplicación completa -----------------------------------------------------------------


def _aplicacion(monkeypatch, tmp_path: Path, *roles: str, entrar: bool = True) -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, *roles)
    monkeypatch.setenv("SILICE_CASO", str(tmp_path / "caso.db"))
    at = AppTest.from_file(str(RUTA_APP), default_timeout=120)
    return (con_ficha(at, ficha) if entrar else at).run()


def _navegacion(monkeypatch):
    import streamlit as st

    llamadas: list = []
    original = st.navigation

    def espia(paginas, **kwargs):
        llamadas.append(list(paginas))
        return original(paginas, **kwargs)

    monkeypatch.setattr(st, "navigation", espia)
    return llamadas


def test_sin_sesion_la_aplicacion_pide_entrar_y_no_arma_el_menu(monkeypatch, tmp_path) -> None:
    llamadas = _navegacion(monkeypatch)
    at = _aplicacion(monkeypatch, tmp_path, "arma", entrar=False)
    assert at.title[0].value == "Sílice: acceso" and llamadas == []


def test_con_sesion_la_aplicacion_arma_el_menu_con_lo_que_el_rol_ve(monkeypatch, tmp_path) -> None:
    llamadas = _navegacion(monkeypatch)
    at = _aplicacion(monkeypatch, tmp_path, "revisa")
    assert not at.exception and llamadas and "Trabajo" in llamadas[0]
    assert "Investigacion" not in llamadas[0]
    assert any("Sesión: Luis (revisa)" in c.value for c in at.sidebar.caption)


def test_el_rol_revisa_no_ve_la_barra_de_herramientas(monkeypatch, tmp_path) -> None:
    at = _aplicacion(monkeypatch, tmp_path, "revisa")
    assert "Guardar version" not in [b.label for b in at.button]


def test_el_rol_arma_si_ve_la_barra_de_herramientas(monkeypatch, tmp_path) -> None:
    at = _aplicacion(monkeypatch, tmp_path, "arma")
    assert "Guardar version" in [b.label for b in at.button]


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()
