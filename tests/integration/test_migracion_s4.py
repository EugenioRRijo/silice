"""La revision de Alembic del registro `ia_*` crea EXACTAMENTE lo que declara `asistente.registro`.

Independiente de la infraestructura de `operacion` (la deriva de RNF-20 del head completo la vigila
`tests/integration/test_migraciones.py`): aplica `upgrade()` y `downgrade()` de la revision con las
operaciones de Alembic sobre una base vacia y compara con `METADATA_IA.create_all`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from asistente.registro import METADATA_IA, TABLAS
from tests.fixtures.arquitectura import RAIZ

REVISION = next((RAIZ / "migraciones" / "caso" / "versions").glob("caso_*_s4_asistente.py"))


def _modulo(ruta: Path):
    especificacion = importlib.util.spec_from_file_location("revision_s4", ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def _forma(motor) -> dict[str, dict]:
    inspector = inspect(motor)
    return {
        tabla: {
            "columnas": [
                (c["name"], str(c["type"]), c["nullable"]) for c in inspector.get_columns(tabla)
            ],
            "pk": inspector.get_pk_constraint(tabla)["constrained_columns"],
            "fks": sorted(
                (tuple(f["constrained_columns"]), f["referred_table"])
                for f in inspector.get_foreign_keys(tabla)
            ),
        }
        for tabla in TABLAS
    }


@pytest.fixture
def motores():
    revisado, declarado = create_engine("sqlite://"), create_engine("sqlite://")
    yield revisado, declarado
    revisado.dispose()
    declarado.dispose()


def test_la_revision_crea_las_mismas_tablas_que_el_registro_y_baja_y_vuelve_a_subir(motores):
    revisado, declarado = motores
    METADATA_IA.create_all(declarado)
    modulo = _modulo(REVISION)
    with revisado.begin() as conexion:
        with Operations.context(MigrationContext.configure(conexion)):
            modulo.upgrade()
    assert _forma(revisado) == _forma(declarado)
    with revisado.begin() as conexion:
        with Operations.context(MigrationContext.configure(conexion)):
            modulo.downgrade()
            modulo.upgrade()
    assert _forma(revisado) == _forma(declarado)


def test_la_revision_sigue_la_regla_de_nombres_de_s5(motores):
    modulo = _modulo(REVISION)
    assert modulo.revision == REVISION.stem
    assert modulo.down_revision and modulo.down_revision != modulo.revision
