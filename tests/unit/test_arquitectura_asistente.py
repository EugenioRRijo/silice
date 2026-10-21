"""Reglas de arquitectura de S4 en su propio archivo (S4 §5.2, maestro §3.1 RV-22; plan 0.9.0).

Capas: `aplicacion.hoja` queda DEBAJO de `asistente`. De `aplicacion`, `asistente` solo importa
`aplicacion.hoja` y `aplicacion.errores`; de `ui`, nada (retiro de Streamlit, F7: la hoja del
auditor paso de `ui.hoja` a `aplicacion.hoja`).
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
#: Lo unico de `aplicacion` que puede importar `asistente` el propio paquete (ver mas abajo).
DE_APLICACION_PERMITIDO = {"aplicacion", "aplicacion.hoja", "aplicacion.errores"}
#: En `aplicacion/` solo `entrega` (lo movio de `ui/entrega.py` la ola 4 de la sesion 2b), y solo
#: `asistente.registro`, para el anexo `ia.json`: ruling RP9-6 del plan 0.9.0.
IMPORTAN_ASISTENTE_APLICACION = {"aplicacion/entrega.py"}


def _raiz(nombre: str) -> str:
    return nombre.split(".")[0]


def test_la_guardia_ve_el_paquete_y_sus_modulos():
    assert RAIZ / "asistente" / "__init__.py" in ASISTENTE
    assert RAIZ / "asistente" / "herramientas.py" in ASISTENTE


@pytest.mark.parametrize("archivo", ASISTENTE, ids=ruta)
def test_asistente_no_importa_streamlit_ni_las_capas_de_arriba(archivo):
    nombres = importaciones(archivo)
    assert not {n for n in nombres if _raiz(n) in {"streamlit", "api", "scripts"}}, ruta(archivo)
    assert not {n for n in nombres if _raiz(n) == "ui"}, ruta(archivo)


@pytest.mark.parametrize("archivo", ASISTENTE, ids=ruta)
def test_de_aplicacion_asistente_solo_importa_la_hoja_y_los_errores(archivo):
    # `aplicacion.hoja` queda debajo de `asistente`; nada mas de `aplicacion` (ni entrega, ni caso)
    de_aplicacion = {n for n in importaciones(archivo) if _raiz(n) == "aplicacion"}
    assert all(
        n in DE_APLICACION_PERMITIDO or n.startswith("aplicacion.hoja.") for n in de_aplicacion
    ), (ruta(archivo), sorted(de_aplicacion))


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


def test_la_hoja_y_los_adaptadores_no_importan_asistente():
    for archivo in [*archivos("adapters"), *archivos("core"), *archivos("ml")]:
        assert "asistente" not in {_raiz(n) for n in importaciones(archivo)}, ruta(archivo)
    assert "asistente" not in {_raiz(n) for n in importaciones(RAIZ / "aplicacion" / "hoja.py")}


def test_aplicacion_entrega_solo_importa_el_registro_del_asistente():
    """La guardia ve el archivo (no recorre una lista vacia) y nadie mas de `aplicacion/` importa
    `asistente` (F5: se retiro el puente `ui/entrega.py`)."""
    vistos = {ruta(a): a for a in archivos("aplicacion")}
    assert "aplicacion/entrega.py" in vistos
    importadores = {
        nombre
        for nombre, archivo in vistos.items()
        if "asistente" in {_raiz(n) for n in importaciones(archivo)}
    }
    assert importadores == IMPORTAN_ASISTENTE_APLICACION, importadores
    de_asistente = {
        n for n in importaciones(vistos["aplicacion/entrega.py"]) if _raiz(n) == "asistente"
    }
    assert de_asistente <= {"asistente", "asistente.registro"}, de_asistente
