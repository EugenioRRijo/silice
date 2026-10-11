"""Interfaz `derivar(espacio, especialidad) -> list[ItemComputo]` (tarea 1.3, FR-1)."""

from __future__ import annotations

import pytest

from adapters.espacio import ESPECIALIDADES, Espacio, derivar


@pytest.mark.parametrize("especialidad", ["agua", "datos", "electricidad"])
def test_fr1_espacio_vacio_no_deriva_nada(especialidad):
    assert derivar(Espacio(), especialidad) == []


def test_las_especialidades_despachables():
    assert set(ESPECIALIDADES) == {"agua", "datos", "electricidad"}


def test_especialidad_desconocida_se_rechaza():
    with pytest.raises(ValueError, match="gas"):
        derivar(Espacio(), "gas")


def test_la_derivacion_devuelve_una_lista():
    assert isinstance(derivar(Espacio(), "agua"), list)
