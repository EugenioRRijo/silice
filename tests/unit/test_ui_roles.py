"""Menú por rol con las pantallas de S3 (RF-80, RF-37, RF-42; S3 §5.1, §5.7): quién ve Entregar,
Revisar y Administración. Lo genérico (cada `render()` exige su acción, la sesión, la barra) está
en `test_ui_marco.py`; aquí, las listas exactas por rol y el recorrido del paquete.

El oráculo de cada lista es la matriz de S3 §5.1 aplicada A MANO a las pantallas del menú (cada
ruta con la acción que declara en `ui/app.py`), no `paginas_visibles` sobre sí misma. Las listas del
plan (tarea 20) son de antes de Tablero, Acerca, Libro de la empresa (1.5) y de que Precios de la
empresa e Índices pasaran al administrador (S3-1, bitácora GS3-1): se rehicieron con esas
pantallas, en el orden de `PAGINAS`."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seguridad.permisos import Rol
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import sesion as ui_sesion
from ui.app import paginas_visibles, secciones_visibles
from ui.recorridos import (
    NOMBRE_DEMOSTRACION,
    NOMBRE_PAQUETE,
    NOMBRE_PRECIOS,
    NOMBRE_PRESUPUESTO,
    recorrido_por_nombre,
)

RUTA_APP = Path(__file__).resolve().parents[2] / "ui" / "app.py"

#: A mano, desde la matriz de S3 §5.1 (LEER_PROYECTO: arma y revisa; EDITAR_HOJA, CONVERTIR,
#: CONTROL y ENTREGAR: arma; REVISAR: revisa; ADMINISTRAR_*: administrador; sin acción: todos).
RUTAS_ARMA = [
    "inicio",
    "tablero",
    "catalogo",
    "componer",
    "elaborar",
    "hoja",
    "actualizacion",
    "historico",
    "reajuste",
    "control",
    "acerca",
    "entregar",
    "existencias",
    "libros",
    "escenarios",
    "similares",
    "simulador",
    "visor",
]
RUTAS_REVISA = ["inicio", "tablero", "catalogo", "historico", "acerca", "revisar", "libros"]
RUTAS_ADMINISTRADOR = [
    "inicio",
    "precios_empresa",
    "indices",
    "acerca",
    "existencias",
    "administracion",
]


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


def _rutas(roles) -> list[str]:
    return [p.ruta_url for p in paginas_visibles(False, frozenset(roles))]


def test_el_rol_arma_ve_el_trabajo_y_la_investigacion_pero_no_revisar_ni_administrar() -> None:
    rutas = _rutas({Rol.ARMA})
    assert rutas == RUTAS_ARMA
    assert not {"revisar", "administracion", "precios_empresa", "indices"} & set(rutas)


def test_el_rol_revisa_solo_ve_el_inicio_la_lectura_y_la_revision() -> None:
    assert _rutas({Rol.REVISA}) == RUTAS_REVISA


def test_el_administrador_solo_ve_el_inicio_los_precios_de_la_empresa_y_la_administracion() -> None:
    assert _rutas({Rol.ADMINISTRADOR}) == RUTAS_ADMINISTRADOR


def test_arma_y_revisa_a_la_vez_ven_la_union_sin_administrar() -> None:
    rutas = _rutas({Rol.ARMA, Rol.REVISA})
    assert set(rutas) == set(RUTAS_ARMA) | set(RUTAS_REVISA)
    assert "administracion" not in rutas


def test_sin_roles_solo_se_ven_las_pantallas_sin_accion() -> None:
    assert _rutas(set()) == ["inicio", "acerca"]


def test_las_secciones_siguen_el_orden_de_s3_y_omiten_las_vacias() -> None:
    """RF-42 (S3 §5.7): Trabajo, Revisión, Investigación y Administración, según el rol."""
    assert tuple(secciones_visibles(False, frozenset({Rol.REVISA}))) == ("Trabajo", "Revision")
    assert tuple(secciones_visibles(False, frozenset({Rol.ADMINISTRADOR}))) == (
        "Trabajo",
        "Administracion",
    )
    assert tuple(secciones_visibles(False, frozenset({Rol.ARMA}))) == (
        "Trabajo",
        "Revision",
        "Investigacion",
    )
    assert tuple(secciones_visibles(True, frozenset({Rol.ARMA}))) == ("Trabajo", "Revision")


def test_ningun_recorrido_apunta_a_una_pantalla_que_el_rol_no_ve() -> None:
    """RF-37 con roles: quien arma ve completos los recorridos de trabajo y, del recorrido del
    paquete, solo el paso de entregar; quien revisa, solo el de revisar."""
    visibles = set(_rutas({Rol.ARMA}))
    for nombre in (NOMBRE_DEMOSTRACION, NOMBRE_PRESUPUESTO, NOMBRE_PRECIOS):
        recorrido = recorrido_por_nombre(nombre)
        assert recorrido.visible_en(visibles).pasos == recorrido.pasos, nombre
    paquete = recorrido_por_nombre(NOMBRE_PAQUETE)
    assert [p.pagina for p in paquete.visible_en(visibles).pasos] == ["entregar"]
    de_revision = set(_rutas({Rol.REVISA}))
    assert [p.pagina for p in paquete.visible_en(de_revision).pasos] == ["revisar"]
    demostracion = recorrido_por_nombre(NOMBRE_DEMOSTRACION).visible_en(de_revision)
    assert [p.pagina for p in demostracion.pasos] == ["catalogo"]
    del_administrador = set(_rutas({Rol.ADMINISTRADOR}))
    assert paquete.visible_en(del_administrador) is None


def _aplicacion(monkeypatch, tmp_path: Path, *roles: str) -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, *roles)
    monkeypatch.setenv("SILICE_CASO", str(tmp_path / "caso.db"))
    at = AppTest.from_file(str(RUTA_APP), default_timeout=120)
    return con_ficha(at, ficha).run()


def _espiar_navegacion(monkeypatch) -> list:
    import streamlit as st

    llamadas: list = []
    original = st.navigation

    def espia(paginas, **kwargs):
        llamadas.append(list(paginas))
        return original(paginas, **kwargs)

    monkeypatch.setattr(st, "navigation", espia)
    return llamadas


def test_la_aplicacion_arma_el_menu_con_las_secciones_del_rol(monkeypatch, tmp_path) -> None:
    llamadas = _espiar_navegacion(monkeypatch)
    at = _aplicacion(monkeypatch, tmp_path, "revisa")
    assert not at.exception, [e.value for e in at.exception]
    assert llamadas == [["Trabajo", "Revision"]]
    assert any("Sesión: Luis (revisa)" in c.value for c in at.sidebar.caption)


def test_el_administrador_ve_su_seccion_en_la_aplicacion(monkeypatch, tmp_path) -> None:
    llamadas = _espiar_navegacion(monkeypatch)
    at = _aplicacion(monkeypatch, tmp_path, "administrador")
    assert not at.exception, [e.value for e in at.exception]
    assert llamadas == [["Trabajo", "Administracion"]]
