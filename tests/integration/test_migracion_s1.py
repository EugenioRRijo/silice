"""Bases anteriores (S1 §9.2): cada base de prueba de la 0.5.0 sube a head por `preparar_base`,
gana las tablas de S1-1 y conserva filas, total y huella del informe de su ficha
(seccion B, RV-3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres

TABLAS_S1_1 = {"serie_indice", "importacion_indice", "valor_indice", "moneda_proyecto",
               "precio_origen"}


@pytest.mark.parametrize("nombre", nombres("0.5.0"))
def test_la_base_0_5_0_gana_las_tablas_de_s1_1_sin_perder_filas(tmp_path: Path, nombre: str):
    ruta = copiar_base("0.5.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        assert TABLAS_S1_1 <= set(inspect(motor).get_table_names())
    finally:
        motor.dispose()
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("0.5.0")["bases"][nombre]) == []
