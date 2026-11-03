"""`ins_0009_prod_publicacion`: una sola publicacion por calculo (plan vial, Tarea 4b). FICTICIOS.

Oraculos a mano: la tabla nueva nace vacia con sus columnas en este orden, `calculo_id` es unico
(un segundo registro del mismo calculo es `IntegrityError`), lo anterior sobrevive a subir y a
bajar, y una base que ya trae la tabla (creada con `create_all`) se adopta.
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

REVISION = "ins_0009_prod_publicacion"
ANTERIOR = "ins_0008_prod_calculo"
COLUMNAS = ["id", "calculo_id", "caso", "lista_id", "usuario", "registrado"]


def _tablas(conexion: sqlite3.Connection) -> set[str]:
    filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {f[0] for f in filas}


def _calculo(conexion: sqlite3.Connection) -> int:
    cursor = conexion.execute(
        "INSERT INTO prod_calculo (periodo, moneda, huella, instantanea, usuario, registrado) "
        "VALUES ('2026-11', 'USD', ?, '{}', 'ana', '2026-11-30 18:00:00')",
        ("a" * 64,),
    )
    return cursor.lastrowid


def _publicacion(conexion: sqlite3.Connection, calculo_id: int, lista_id: int = 1) -> None:
    conexion.execute(
        "INSERT INTO prod_publicacion (calculo_id, caso, lista_id, usuario, registrado) "
        "VALUES (?, 'carpeta-ficticia.db', ?, 'admin', '2026-12-01 07:30:00')",
        (calculo_id, lista_id),
    )


def test_le_sigue_la_de_los_modulos() -> None:
    """Plan vial, Tarea 19: la cabeza pasa a `ins_0010_modulo`, que baja a esta."""
    assert revision_head(Destino.INSTALACION) == "ins_0011_receta_ligante"


def test_crea_la_tabla_vacia_con_sus_columnas_y_calculo_id_unico(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert "prod_publicacion" in _tablas(conexion)
        hallado = [f[1] for f in conexion.execute("PRAGMA table_info(prod_publicacion)")]
        assert hallado == COLUMNAS
        assert conexion.execute("SELECT count(*) FROM prod_publicacion").fetchone() == (0,)
        calculo = _calculo(conexion)
        _publicacion(conexion, calculo)
        conexion.commit()
        with pytest.raises(sqlite3.IntegrityError):
            _publicacion(conexion, calculo, lista_id=2)
        conexion.rollback()
        assert conexion.execute("SELECT count(*) FROM prod_publicacion").fetchone() == (1,)


def test_subir_y_bajar_conserva_lo_anterior(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        _calculo(conexion)
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        _publicacion(conexion, 1)
        conexion.commit()
    deshacer_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert "prod_publicacion" not in _tablas(conexion)
        assert conexion.execute("SELECT periodo FROM prod_calculo").fetchall() == [("2026-11",)]
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert "prod_publicacion" in _tablas(conexion)
        assert conexion.execute("SELECT count(*) FROM prod_publicacion").fetchone() == (0,)


def test_una_base_que_ya_trae_la_tabla_se_adopta(tmp_path: Path) -> None:
    from sqlalchemy import create_engine

    from produccion.modelo import PublicacionRegistrada

    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    motor = create_engine(f"sqlite:///{base.as_posix()}")
    try:
        PublicacionRegistrada.__table__.create(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(base)) as conexion:
        _publicacion(conexion, _calculo(conexion))
        conexion.commit()

    aplicar_revisiones(base, Destino.INSTALACION)

    with closing(sqlite3.connect(base)) as conexion:
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            ("ins_0011_receta_ligante",)
        ]
        assert conexion.execute("SELECT calculo_id, lista_id FROM prod_publicacion").fetchall() == [
            (1, 1)
        ]
