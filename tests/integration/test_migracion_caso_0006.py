"""La revisión `caso_0006_s2_decision` (SL-E6): la rama `_faltan` y su `downgrade()`.

La bitácora de la 0.7.0 (S2-3, «Sin prueba propia») anota que ni la rama `_faltan` sobre una base
creada con `create_all` ni el `downgrade()` tenían prueba directa. Se aplican `upgrade()` y
`downgrade()` de la revisión con las operaciones de Alembic (como `test_migracion_s4.py`), sobre
tres bases en memoria:

* una creada con `create_all` del código actual (ya trae `decision_recuperacion`): la revisión la
  **adopta** sin recrearla y sin perder filas;
* una con todas las tablas salvo `decision_recuperacion`: la revisión la crea con la misma forma que
  declara `core.models.DecisionRecuperacion`, y su índice;
* `downgrade()` borra solo lo presente: dos veces seguidas no fallan, y vuelve a subir.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, event, inspect, text

from core.catalog.sesion import _activar_claves_foraneas
from core.models import Base
from tests.fixtures.arquitectura import RAIZ

REVISION = RAIZ / "migraciones" / "caso" / "versions" / "caso_0006_s2_decision.py"
TABLA = "decision_recuperacion"
INDICE = "ix_decision_recuperacion_proyecto"


def _modulo(ruta: Path):
    especificacion = importlib.util.spec_from_file_location("revision_caso_0006", ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def _aplicar(motor, *pasos: str) -> None:
    modulo = _modulo(REVISION)
    with motor.begin() as conexion:
        with Operations.context(MigrationContext.configure(conexion)):
            for paso in pasos:
                getattr(modulo, paso)()


def _forma(motor) -> dict:
    inspector = inspect(motor)
    return {
        "columnas": [
            (c["name"], str(c["type"]), c["nullable"]) for c in inspector.get_columns(TABLA)
        ],
        "pk": inspector.get_pk_constraint(TABLA)["constrained_columns"],
        "fks": sorted(
            (tuple(f["constrained_columns"]), f["referred_table"])
            for f in inspector.get_foreign_keys(TABLA)
        ),
        "indices": sorted(
            (i["name"], tuple(i["column_names"])) for i in inspector.get_indexes(TABLA)
        ),
    }


def _tablas(motor) -> set[str]:
    return set(inspect(motor).get_table_names())


@pytest.fixture
def motores():
    creados = []

    def nuevo():
        motor = create_engine("sqlite://")
        event.listen(motor, "connect", _activar_claves_foraneas)
        creados.append(motor)
        return motor

    yield nuevo
    for motor in creados:
        motor.dispose()


def test_la_revision_encadena_tras_caso_0005():
    modulo = _modulo(REVISION)
    assert modulo.revision == REVISION.stem == "caso_0006_s2_decision"
    assert modulo.down_revision == "caso_0005_s2_valuaciones"
    assert modulo.TABLAS == (TABLA,)


def test_sobre_una_base_creada_con_create_all_la_revision_adopta_la_tabla_sin_recrearla(motores):
    motor = motores()
    Base.metadata.create_all(motor)
    with motor.begin() as conexion:  # una fila centinela: si la tabla se recreara, se perdería
        conexion.execute(text("PRAGMA foreign_keys=OFF"))
        conexion.execute(
            text(
                "INSERT INTO decision_recuperacion (id, proyecto_id, linea_base_id, "
                "version_resultante_id, fecha_corte, opcion, detalle, costo_directo_adicional, "
                "costo_indirecto, penalizacion, termino, supuestos, fuente, responsable, "
                "fecha_hora) VALUES (7, 1, 1, 1, '2026-11-13', 'cuadrillas', '{}', '120', '0', "
                "'0', '2026-11-24', '[]', 'ficticia', 'Ing.', '2026-11-16 10:00:00')"
            )
        )
    antes = _forma(motor)
    _aplicar(motor, "upgrade")  # sin `_faltan`, esto sería «table already exists»
    assert _forma(motor) == antes
    with motor.connect() as conexion:
        assert conexion.execute(text(f"SELECT id FROM {TABLA}")).scalars().all() == [7]


def test_sobre_una_base_sin_la_tabla_la_crea_como_la_declara_el_modelo(motores):
    declarado, revisado = motores(), motores()
    Base.metadata.create_all(declarado)
    previas = [t for t in Base.metadata.sorted_tables if t.name != TABLA]
    Base.metadata.create_all(revisado, tables=previas)
    assert TABLA not in _tablas(revisado)
    _aplicar(revisado, "upgrade")
    assert TABLA in _tablas(revisado)
    assert _forma(revisado) == _forma(declarado)
    assert (INDICE, ("proyecto_id",)) in _forma(revisado)["indices"]
    # Las tablas anteriores no cambian.
    assert _tablas(revisado) == _tablas(declarado)


def test_downgrade_borra_solo_lo_presente_y_se_puede_repetir_y_volver_a_subir(motores):
    declarado, motor = motores(), motores()
    Base.metadata.create_all(declarado)
    Base.metadata.create_all(motor)
    resto = _tablas(motor) - {TABLA}
    _aplicar(motor, "downgrade")
    assert _tablas(motor) == resto
    _aplicar(motor, "downgrade")  # ya no está: no falla y no toca nada más
    assert _tablas(motor) == resto
    _aplicar(motor, "upgrade")
    assert _tablas(motor) == resto | {TABLA}
    assert _forma(motor) == _forma(declarado)
