"""Reglas de arquitectura de S4 en su propio archivo (S4 §5.2, maestro §3.1 RV-22; plan 0.9.0).

Capas: `ui.hoja` queda DEBAJO de `asistente`, y `asistente` DEBAJO de `ui.paginas`. De `ui`,
`asistente` solo importa `ui.hoja` (y `ui.texto_seguro` no: el texto ajeno lo muestra la pantalla);
de `ui`, solo `ui.paginas.hoja`, `ui.paginas.administracion` y `ui.entrega` importan `asistente`.
`anthropic` solo en `claude.py`; el cliente de Ollama solo en `ollama_local.py`; `keyring` solo en
`clave.py`; `streamlit` en ningun modulo del paquete.
"""

from __future__ import annotations

import pytest

from tests.fixtures.arquitectura import RAIZ, archivos, importaciones, ruta

ASISTENTE = archivos("asistente")
PAQUETES_DE_TERCEROS = {
    "anthropic": {"asistente/proveedores/claude.py"},
    "ollama": {"asistente/proveedores/ollama_local.py"},
    "keyring": {"asistente/clave.py"},
}
#: Los unicos modulos de `ui` que pueden importar `asistente` (maestro §3.1; `ui.entrega` solo
#: `asistente.registro`, para el anexo `ia.json`: ruling RP9-6 del plan 0.9.0).
IMPORTAN_ASISTENTE = {
    "ui/paginas/hoja.py",
    "ui/paginas/administracion.py",
    "ui/entrega.py",
}


def _raiz(nombre: str) -> str:
    return nombre.split(".")[0]


def test_la_guardia_ve_el_paquete_y_sus_modulos():
    assert RAIZ / "asistente" / "__init__.py" in ASISTENTE
    assert RAIZ / "asistente" / "herramientas.py" in ASISTENTE


@pytest.mark.parametrize("archivo", ASISTENTE, ids=ruta)
def test_asistente_no_importa_streamlit_ni_las_capas_de_arriba(archivo):
    nombres = importaciones(archivo)
    assert not {n for n in nombres if _raiz(n) in {"streamlit", "api", "scripts"}}, ruta(archivo)
    de_ui = {n for n in nombres if _raiz(n) == "ui"}
    # `ui.hoja` queda debajo de `asistente`; nada mas de `ui` (ni paginas, ni caso, ni barra)
    assert all(n == "ui" or n.startswith("ui.hoja") for n in de_ui), (ruta(archivo), sorted(de_ui))


@pytest.mark.parametrize("archivo", ASISTENTE, ids=ruta)
def test_asistente_solo_importa_seguridad_secretos_de_seguridad(archivo):
    de_seguridad = {n for n in importaciones(archivo) if _raiz(n) == "seguridad"}
    assert de_seguridad <= {"seguridad", "seguridad.secretos"}, (ruta(archivo), de_seguridad)


@pytest.mark.parametrize("archivo", ASISTENTE, ids=ruta)
def test_cada_tercero_de_ia_solo_vive_en_su_adaptador(archivo):
    nombres = {_raiz(n) for n in importaciones(archivo)}
    for tercero, permitidos in PAQUETES_DE_TERCEROS.items():
        if tercero in nombres:
            assert ruta(archivo) in permitidos, f"{ruta(archivo)} importa {tercero}"


def test_ui_hoja_y_los_adaptadores_no_importan_asistente():
    for archivo in [*archivos("adapters"), *archivos("core"), *archivos("ml")]:
        assert "asistente" not in {_raiz(n) for n in importaciones(archivo)}, ruta(archivo)
    assert "asistente" not in {_raiz(n) for n in importaciones(RAIZ / "ui" / "hoja.py")}


def test_de_ui_solo_las_paginas_de_la_lista_importan_asistente():
    importadores = {
        ruta(archivo)
        for archivo in archivos("ui")
        if "asistente" in {_raiz(n) for n in importaciones(archivo)}
    }
    assert importadores <= IMPORTAN_ASISTENTE, importadores - IMPORTAN_ASISTENTE


def test_ui_entrega_solo_importa_el_registro_del_asistente():
    """`ui/entrega.py` lo crea S3-3; hasta entonces el bucle no encuentra nada que vigilar."""
    for archivo in archivos("ui"):
        if ruta(archivo) == "ui/entrega.py":
            de_asistente = {n for n in importaciones(archivo) if _raiz(n) == "asistente"}
            assert de_asistente <= {"asistente", "asistente.registro"}, de_asistente
