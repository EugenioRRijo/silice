"""Reglas de arquitectura de S1 en su propio archivo (RV‑2), con los ayudantes compartidos de
`tests/fixtures/arquitectura.py` (sección B, Tarea 1)."""

import pytest

from tests.fixtures.arquitectura import RAIZ, importaciones

SIN_PINTAR = (
    "aplicacion/indices.py",
    "aplicacion/precios_empresa.py",
    "aplicacion/reajuste.py",
)


@pytest.mark.parametrize("modulo", [m for m in SIN_PINTAR if (RAIZ / m).exists()])
def test_la_capa_de_s1_no_pinta(modulo):
    prohibidos = {
        m
        for m in importaciones(RAIZ / modulo)
        if m.split(".")[0] in {"streamlit", "pandas"} or m == "ui.caso"
    }
    assert prohibidos == set()


def test_ninguna_pagina_de_s1_importa_scripts_al_cargar():
    for pagina in ("indices", "precios_empresa", "reajuste"):
        ruta = RAIZ / "ui" / "paginas" / f"{pagina}.py"
        if ruta.exists():
            texto = ruta.read_text(encoding="utf-8")
            assert "\nfrom scripts" not in texto and "\nimport scripts" not in texto  # RV‑25
