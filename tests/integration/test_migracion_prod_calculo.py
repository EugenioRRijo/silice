"""`ins_0008_prod_calculo`: los calculos del costo por tonelada (Tarea 4 del plan vial). FICTICIOS.

Oraculos a mano: la tabla nueva y su orden de columnas se escriben aqui; lo anterior sobrevive a
subirla y a bajarla, y una base que ya trae la tabla (creada con `create_all`) se adopta.
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

REVISION = "ins_0008_prod_calculo"
ANTERIOR = "ins_0007_prod_receta"
COLUMNAS = ["id", "periodo", "moneda", "huella", "instantanea", "usuario", "registrado"]
HUELLA = "a" * 64


def _tablas(conexion: sqlite3.Connection) -> set[str]:
    filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {f[0] for f in filas}


def _calculo(conexion: sqlite3.Connection, moneda: str = "USD", huella: str = HUELLA) -> None:
    conexion.execute(
        "INSERT INTO prod_calculo (periodo, moneda, huella, instantanea, usuario, registrado) "
        "VALUES ('2026-11', ?, ?, '{}', 'ana', '2026-11-30 18:00:00')",
        (moneda, huella),
    )


def test_es_la_cabeza_de_la_instalacion() -> None:
    assert revision_head(Destino.INSTALACION) == REVISION


def test_crea_la_tabla_con_sus_columnas_y_sus_reglas(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert "prod_calculo" in _tablas(conexion)
        hallado = [f[1] for f in conexion.execute("PRAGMA table_info(prod_calculo)")]
        assert hallado == COLUMNAS
        _calculo(conexion)
        _calculo(conexion)  # recalcular con la misma huella es otro registro
        conexion.commit()
        with pytest.raises(sqlite3.IntegrityError):
            _calculo(conexion, moneda="EUR")
        with pytest.raises(sqlite3.IntegrityError):
            _calculo(conexion, huella="corta")
        assert conexion.execute("SELECT count(*) FROM prod_calculo").fetchone() == (2,)


def test_subir_y_bajar_conserva_lo_anterior(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(
            "INSERT INTO prod_receta (producto, fuente, vigente_desde, usuario, registrado) "
            "VALUES ('MZ-1', 'ficticia', '2026-10-01', 'ana', '2026-10-01 08:00:00')"
        )
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        _calculo(conexion)
        conexion.commit()
    deshacer_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert "prod_calculo" not in _tablas(conexion)
        assert conexion.execute("SELECT producto FROM prod_receta").fetchall() == [("MZ-1",)]
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert "prod_calculo" in _tablas(conexion)


def test_una_base_que_ya_trae_la_tabla_se_adopta(tmp_path: Path) -> None:
    from sqlalchemy import create_engine

    from produccion.modelo import Calculo

    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    motor = create_engine(f"sqlite:///{base.as_posix()}")
    try:
        Calculo.__table__.create(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(base)) as conexion:
        _calculo(conexion)
        conexion.commit()

    aplicar_revisiones(base, Destino.INSTALACION)

    with closing(sqlite3.connect(base)) as conexion:
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (REVISION,)
        ]
        assert conexion.execute("SELECT periodo, huella FROM prod_calculo").fetchall() == [
            ("2026-11", HUELLA)
        ]
