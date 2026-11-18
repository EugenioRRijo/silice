"""Las consultas de materiales que salieron de `api/rutas/produccion.py` (tarea 3.3 del plan de
desenredo): `materiales` por codigo y `material_por_codigo`, que recorta blancos como la ruta.
Base de produccion en memoria armada a mano; codigos ficticios."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from produccion.inventario import crear_material, material_por_codigo, materiales
from produccion.modelo import METADATA_PRODUCCION


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATA_PRODUCCION.create_all(motor)
    with Session(motor) as s:
        for codigo in ("PI-03", "AR-01", "GR-02"):
            crear_material(
                s,
                codigo=codigo,
                nombre=f"Material {codigo}",
                unidad_venta="m3",
                existencia_minima=Decimal("1"),
            )
        yield s
    motor.dispose()


def test_materiales_salen_por_codigo(sesion: Session) -> None:
    assert [m.codigo for m in materiales(sesion)] == ["AR-01", "GR-02", "PI-03"]


def test_material_por_codigo_recorta_blancos_y_es_exacto(sesion: Session) -> None:
    encontrado = material_por_codigo(sesion, "  AR-01 ")
    assert encontrado is not None and encontrado.codigo == "AR-01"
    assert material_por_codigo(sesion, "ar-01") is None
    assert material_por_codigo(sesion, "XX-99") is None
