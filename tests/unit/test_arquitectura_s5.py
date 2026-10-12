"""Reglas de arquitectura de S5 (spec S5 §5.2; maestro §3.1 y §4.3; RV-5, RV-22).

Archivo propio de S5 (RV-2: cada spec escribe sus reglas en su archivo, con los ayudantes
compartidos de `tests/fixtures/arquitectura.py`).
"""

from __future__ import annotations

import pytest

from tests.fixtures.arquitectura import RAIZ, archivos, importaciones, llamadas, ruta

#: Lo único de `operacion` que `ui` y `api` pueden importar (spec S5 §5.2).
PUBLICOS_DE_OPERACION = (
    "operacion.config",
    "operacion.version",
    "operacion.respaldo",
    "operacion.base_datos",
    "operacion.instalacion",  # S3-1: la base de la instalación, la comparten la interfaz y la API
)


def _raiz(modulo: str) -> str:
    return modulo.split(".")[0]


def _infractores(paquetes: tuple[str, ...], prohibidos: set[str]) -> list[str]:
    return sorted(
        f"{ruta(archivo)}: {modulo}"
        for paquete in paquetes
        for archivo in archivos(paquete)
        for modulo in importaciones(archivo)
        if _raiz(modulo) in prohibidos
    )


@pytest.mark.parametrize("archivo", archivos("core"), ids=ruta)
def test_el_nucleo_no_importa_operacion_ni_migraciones(archivo) -> None:
    prohibidos = sorted(
        m for m in importaciones(archivo) if _raiz(m) in {"operacion", "migraciones"}
    )
    assert prohibidos == []


def test_operacion_no_importa_streamlit_ui_ni_api() -> None:
    assert archivos("operacion"), "la guardia no ve operacion/"
    assert _infractores(("operacion",), {"streamlit", "ui", "api"}) == []


def test_migraciones_no_importa_streamlit_ui_api_ni_operacion() -> None:
    assert archivos("migraciones"), "la guardia no ve migraciones/"
    assert _infractores(("migraciones",), {"streamlit", "ui", "api", "operacion"}) == []


def test_ui_y_api_no_importan_migraciones() -> None:
    assert _infractores(("ui", "api"), {"migraciones"}) == []


def test_ui_y_api_solo_importan_los_modulos_publicos_de_operacion() -> None:
    infractores = sorted(
        f"{ruta(archivo)}: {modulo}"
        for paquete in ("ui", "api")
        for archivo in archivos(paquete)
        for modulo in importaciones(archivo)
        if _raiz(modulo) == "operacion"
        and modulo != "operacion"
        and not any(modulo == p or modulo.startswith(p + ".") for p in PUBLICOS_DE_OPERACION)
    )
    assert infractores == []


#: Las doce páginas que abren el caso con un motor propio (spec S5 §1.2): todas lo preparan.
PAGINAS_QUE_ABREN_EL_CASO = (
    "actualizacion",
    "catalogo",
    "componer",
    "control",
    "elaborar",
    "escenarios",
    "historico",
    "hoja",
    "indices",
    "precios_empresa",
    "reajuste",
    "similares",
    "simulador",
)


def test_ni_la_interfaz_ni_la_api_crean_el_esquema() -> None:
    """RV-5: `crear_esquema` queda para las pruebas en memoria y los scripts de siembra."""
    infractores = sorted(
        f"{ruta(archivo)}:{linea}"
        for paquete in ("ui", "api")
        for archivo in archivos(paquete)
        for linea in llamadas(archivo, "crear_esquema")
    )
    assert infractores == []


def test_la_lista_de_paginas_que_abren_el_caso_esta_completa() -> None:
    con_motor = sorted(
        archivo.stem
        for archivo in (RAIZ / "ui" / "paginas").glob("*.py")
        if llamadas(archivo, "crear_motor")
    )
    assert con_motor == sorted(PAGINAS_QUE_ABREN_EL_CASO)


@pytest.mark.parametrize("pagina", PAGINAS_QUE_ABREN_EL_CASO)
def test_cada_pagina_que_abre_el_caso_lo_prepara(pagina: str) -> None:
    assert llamadas(RAIZ / "ui" / "paginas" / f"{pagina}.py", "preparar_base")
