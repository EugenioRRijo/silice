"""INV-024: importar la interfaz no carga los extras `civil` ni `ml` (se cargan al usarlos)."""

import importlib.util

import pytest

from tests.fixtures.subproceso import importar_en_limpio, modulos_cargados

EXTRAS = ("ifcopenshell", "sentence_transformers")


@pytest.mark.parametrize("extra", EXTRAS)
def test_importar_la_aplicacion_no_carga_el_extra(extra, tmp_path):
    # QA-12: sin el extra instalado la prueba saldria verde en vacio; primero se exige que exista.
    assert importlib.util.find_spec(extra) is not None, f"{extra} no esta instalado"
    salida = importar_en_limpio(["ui.app"], cwd=tmp_path)
    assert salida.returncode == 0, salida.stderr
    assert extra not in modulos_cargados(salida)
