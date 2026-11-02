"""Sesión 4 de la ruta (arenera): la ERS y el modelo de datos definen lo que se construye.

La ERS escribe los códigos con el guion no separable U+2011 (`RF‑127`); la prueba lo normaliza para
no depender de cómo se teclee.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
GUION_NO_SEPARABLE = "‑"

CODIGOS_S4 = ("UC-28", "UC-29", *(f"RF-{n}" for n in range(127, 137)), "RNF-25")
TABLAS_S4 = ("prod_material", "prod_movimiento", "prod_pesaje_sospechoso")


def _texto(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8").replace(GUION_NO_SEPARABLE, "-")


@pytest.mark.parametrize("codigo", CODIGOS_S4)
def test_la_ers_define_los_requisitos_de_la_sesion_4(codigo):
    assert codigo in _texto("docs/ERS.md")


def test_la_ers_traza_los_casos_de_uso_de_la_arenera():
    ers = _texto("docs/ERS.md")
    assert "UC-28 → RF-127" in ers
    assert "UC-29 → RF-130" in ers


@pytest.mark.parametrize("tabla", TABLAS_S4)
def test_el_modelo_de_datos_nombra_las_tablas_de_la_arenera(tabla):
    assert tabla in _texto("docs/modelo_datos.md")
