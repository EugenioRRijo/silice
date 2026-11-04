"""`ins_0011_receta_ligante`: la marca `es_ligante` en los componentes de la receta (Tarea 16c).

Oraculos a mano: la columna nueva va al final de `prod_receta_componente`, las filas anteriores
quedan sin marca (0) y bajar la quita sin tocar el resto. FICTICIO.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from operacion.base_datos import (
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    revision_head,
)

REVISION = "ins_0011_receta_ligante"
ANTERIOR = "ins_0010_modulo"
TABLA = "prod_receta_componente"
ANTES = ["id", "receta_id", "orden", "codigo", "cantidad_por_t", "unidad", "tipo"]


def _columnas(conexion: sqlite3.Connection) -> list[str]:
    return [f[1] for f in conexion.execute(f"PRAGMA table_info({TABLA})")]


def _receta_con_componentes(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        "INSERT INTO prod_receta (producto, fuente, vigente_desde, usuario, registrado) "
        "VALUES ('MZ-1', 'ficticia', '2026-10-01', 'ana', '2026-10-01 08:00:00')"
    )
    conexion.execute(
        f"INSERT INTO {TABLA} (receta_id, orden, codigo, cantidad_por_t, unidad, tipo) VALUES "
        "(1, 0, 'ARE-1', '0.90', 't', 'comprado'), (1, 1, 'CA-30', '0.10', 't', 'comprado')"
    )


def test_es_la_cabeza_de_la_instalacion() -> None:
    assert revision_head(Destino.INSTALACION) == REVISION


def test_agrega_la_columna_al_final_y_lo_anterior_queda_sin_marca(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion) == ANTES
        _receta_con_componentes(conexion)
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion) == [*ANTES, "es_ligante"]
        filas = conexion.execute(f"SELECT codigo, es_ligante FROM {TABLA} ORDER BY id").fetchall()
        assert filas == [("ARE-1", 0), ("CA-30", 0)]


def test_bajar_quita_la_columna_y_conserva_las_filas(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        _receta_con_componentes(conexion)
        conexion.execute(f"UPDATE {TABLA} SET es_ligante = 1 WHERE codigo = 'CA-30'")
        conexion.commit()
    deshacer_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion) == ANTES
        assert conexion.execute(f"SELECT codigo FROM {TABLA} ORDER BY id").fetchall() == [
            ("ARE-1",),
            ("CA-30",),
        ]
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion)[-1] == "es_ligante"


def test_una_base_que_ya_trae_la_columna_se_adopta(tmp_path: Path) -> None:
    """Hecha con `create_all` (la columna ya esta), la migracion no la duplica."""
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(f"ALTER TABLE {TABLA} ADD COLUMN es_ligante BOOLEAN NOT NULL DEFAULT 0")
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion).count("es_ligante") == 1
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (REVISION,)
        ]
