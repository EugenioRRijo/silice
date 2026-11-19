"""`ins_0012_conteo_anulado`: `anula_id` y `motivo` en `prod_movimiento` (tanda 2026-11-19).

La anulacion de un conteo fisico es un ajuste nuevo que apunta al anulado. Oraculos a mano: las dos
columnas van al final de `prod_movimiento`; los movimientos anteriores quedan sin anulacion
(`anula_id` nulo, `motivo` vacio) y conservan su tipo, su cantidad y su ticket unico; `anula_id` es
unico (un conteo se anula una sola vez). Bajar quita las columnas sin tocar las filas. FICTICIO.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from operacion.base_datos import (
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    revision_head,
)

REVISION = "ins_0012_conteo_anulado"
ANTERIOR = "ins_0011_receta_ligante"
TABLA = "prod_movimiento"
ANTES = [
    "id",
    "material_id",
    "fecha",
    "tipo",
    "cantidad",
    "ticket",
    "placa",
    "cliente",
    "nota",
    "origen",
    "usuario",
    "registrado",
]
FILAS = [("entrada", "150.5", "T-1"), ("ajuste", "-2.5", None)]


def _columnas(conexion: sqlite3.Connection) -> list[str]:
    return [f[1] for f in conexion.execute(f"PRAGMA table_info({TABLA})")]


def _con_movimientos(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        "INSERT INTO prod_material (codigo, nombre, unidad_venta, existencia_minima, activo) "
        "VALUES ('PIEDRA', 'Piedra', 't', '0', 1)"
    )
    for tipo, cantidad, ticket in FILAS:
        conexion.execute(
            f"INSERT INTO {TABLA} (material_id, fecha, tipo, cantidad, ticket, placa, cliente, "
            "nota, origen, usuario, registrado) VALUES (1, '2026-11-06', ?, ?, ?, '', '', '', "
            "'manual', 'ana', '2026-11-06 08:00:00')",
            (tipo, cantidad, ticket),
        )


def test_es_la_cabeza_de_la_instalacion() -> None:
    assert revision_head(Destino.INSTALACION) == REVISION


def test_agrega_las_columnas_al_final_y_lo_anterior_queda_sin_anular(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion) == ANTES
        _con_movimientos(conexion)
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion) == [*ANTES, "anula_id", "motivo"]
        filas = conexion.execute(
            f"SELECT tipo, cantidad, ticket, anula_id, motivo FROM {TABLA} ORDER BY id"
        ).fetchall()
        assert filas == [(*f, None, "") for f in FILAS]


def test_anula_id_apunta_a_un_movimiento_y_es_unico(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        _con_movimientos(conexion)
        claves = conexion.execute(f"PRAGMA foreign_key_list({TABLA})").fetchall()
        assert {(f[2], f[3], f[4]) for f in claves} == {
            ("prod_material", "material_id", "id"),
            (TABLA, "anula_id", "id"),
        }
        anular = (
            f"INSERT INTO {TABLA} (material_id, fecha, tipo, cantidad, placa, cliente, nota, "
            "origen, usuario, registrado, anula_id, motivo) VALUES (1, '2026-11-06', 'ajuste', "
            "'2.5', '', '', '', 'manual', 'ana', '2026-11-07 08:00:00', 2, 'mal contado')"
        )
        conexion.execute(anular)
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conexion.execute(anular)
        # los CHECK y el ticket unico siguen en pie tras recrear la tabla
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conexion.execute(
                f"INSERT INTO {TABLA} (material_id, fecha, tipo, cantidad, ticket, placa, "
                "cliente, nota, origen, usuario, registrado) VALUES (1, '2026-11-07', "
                "'despacho', '1', 'T-1', '', '', '', 'bascula', 'ana', '2026-11-07 08:00:00')"
            )
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conexion.execute(
                f"INSERT INTO {TABLA} (material_id, fecha, tipo, cantidad, placa, cliente, nota, "
                "origen, usuario, registrado) VALUES (1, '2026-11-07', 'robo', '1', '', '', '', "
                "'manual', 'ana', '2026-11-07 08:00:00')"
            )


def test_bajar_quita_las_columnas_y_conserva_las_filas(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        _con_movimientos(conexion)
        conexion.commit()
    deshacer_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion) == ANTES
        assert (
            conexion.execute(f"SELECT tipo, cantidad, ticket FROM {TABLA} ORDER BY id").fetchall()
            == FILAS
        )
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion)[-2:] == ["anula_id", "motivo"]


def test_una_base_que_ya_trae_las_columnas_se_adopta(tmp_path: Path) -> None:
    """Hecha con `create_all` (las columnas ya estan), la migracion no las duplica."""
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(f"ALTER TABLE {TABLA} ADD COLUMN anula_id INTEGER REFERENCES {TABLA} (id)")
        conexion.execute(f"ALTER TABLE {TABLA} ADD COLUMN motivo VARCHAR(300) DEFAULT '' NOT NULL")
        conexion.execute(f"CREATE UNIQUE INDEX ix_prod_movimiento_anula_id ON {TABLA} (anula_id)")
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion).count("anula_id") == 1
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (REVISION,)
        ]
