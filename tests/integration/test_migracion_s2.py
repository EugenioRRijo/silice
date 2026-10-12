# tests/integration/test_migracion_s2.py
"""Bases anteriores (S2 §6.1, SL-E4): cada base de prueba de la 0.6.0 sube a `head` por
`preparar_base`, gana las tablas de control sin perder filas y recarga con el total y la huella del
informe de su ficha (sección B, RV-3). La prueba de deriva (RNF-20, `test_migraciones.py`) recorre
las revisiones `caso_0005_s2_valuaciones` y `caso_0006_s2_decision` sin cambios."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres

TABLAS_DE_S2_1 = {
    "linea_base_control",
    "calendario_obra",
    "parametros_control",
    "valuacion",
    "linea_valuacion",
    "anulacion_valuacion",
    "costo_real",
    "cita_valuacion",
}
TABLAS_DE_S2_3: set[str] = set()


def _tablas(ruta: Path) -> set[str]:
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        return set(inspect(motor).get_table_names())
    finally:
        motor.dispose()


@pytest.mark.parametrize("nombre", nombres("0.6.0"))
def test_base_anterior_abre_con_tablas_de_control(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("0.6.0", nombre, tmp_path / nombre)
    antes = _tablas(ruta)
    assert not antes & TABLAS_DE_S2_1  # una base de la 0.6.0 no las tiene
    preparar_base(ruta)
    assert (TABLAS_DE_S2_1 | TABLAS_DE_S2_3) <= _tablas(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("0.6.0")["bases"][nombre]) == []


@pytest.mark.parametrize("nombre", nombres("0.5.0"))
def test_base_de_la_0_5_0_sube_hasta_las_tablas_de_control(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("0.5.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    assert (TABLAS_DE_S2_1 | TABLAS_DE_S2_3) <= _tablas(ruta)
    assert diferencias_con_ficha(ruta, ficha("0.5.0")["bases"][nombre]) == []


def test_las_tablas_de_control_nacen_vacias(tmp_path: Path) -> None:
    ruta = copiar_base("0.6.0", "ti001.db", tmp_path / "ti001.db")
    preparar_base(ruta)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.connect() as conexion:
            for tabla in sorted(TABLAS_DE_S2_1 | TABLAS_DE_S2_3):
                filas = conexion.exec_driver_sql(f"SELECT COUNT(*) FROM {tabla}").scalar()
                assert filas == 0, tabla
    finally:
        motor.dispose()
