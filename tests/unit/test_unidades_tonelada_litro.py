"""Alias de tonelada y litro en la unica tabla de unidades (expediente NUC-E1).

Oraculos escritos a mano. Masa (kg, t) y volumen (m3, l) siguen siendo unidades distintas entre si
y con las demas: la regla R3 necesita detectar esas diferencias.
"""

from __future__ import annotations

import pytest

from core.contracts.unidades import normalizar_unidad, unidades_equivalentes


@pytest.mark.parametrize(
    "grafia", ["ton", "tn", "tonelada", "toneladas", "t", "TON", " Toneladas "]
)
def test_tonelada(grafia):
    assert normalizar_unidad(grafia) == "t"


@pytest.mark.parametrize("grafia", ["l", "lt", "lts", "litro", "litros", "LT", " Litros "])
def test_litro(grafia):
    assert normalizar_unidad(grafia) == "l"


def test_masa_y_volumen_siguen_distintos():
    assert not unidades_equivalentes("t", "kg")
    assert not unidades_equivalentes("ton", "kgs")
    assert not unidades_equivalentes("l", "m3")
    assert not unidades_equivalentes("litro", "m³")
    assert not unidades_equivalentes("t", "l")
    assert not unidades_equivalentes("t", "m3")
    assert not unidades_equivalentes("l", "kg")


def test_ml_sigue_siendo_metro_lineal():
    assert normalizar_unidad("ml") == "m"
    assert not unidades_equivalentes("ml", "l")


def test_las_grafias_de_una_misma_unidad_casan():
    assert unidades_equivalentes("ton", "t")
    assert unidades_equivalentes("lt", "litros")
