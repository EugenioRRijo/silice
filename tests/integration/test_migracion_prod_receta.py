"""`ins_0007_prod_receta`: recetas de la planta y el movimiento `consumo` (Tarea 3 del plan vial).

Oraculos a mano: las dos tablas nuevas y su orden de columnas se escriben aqui; el movimiento
`consumo` solo cabe despues de la migracion y los movimientos anteriores sobreviven a subirla.
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

REVISION = "ins_0007_prod_receta"
ANTERIOR = "ins_0006_prod_costo"
COLUMNAS = {
    "prod_receta": ["id", "producto", "fuente", "vigente_desde", "usuario", "registrado"],
    "prod_receta_componente": [
        "id",
        "receta_id",
        "orden",
        "codigo",
        "cantidad_por_t",
        "unidad",
        "tipo",
        "es_ligante",  # Tarea 16c, ins_0011: la ultima, tras subir a la cabeza
    ],
}


def _tablas(conexion: sqlite3.Connection) -> set[str]:
    filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {f[0] for f in filas}


def _sql_de(conexion: sqlite3.Connection, tabla: str) -> str:
    fila = conexion.execute("SELECT sql FROM sqlite_master WHERE name = ?", (tabla,)).fetchone()
    return fila[0]


def _movimiento(conexion: sqlite3.Connection, tipo: str, cantidad: str = "5") -> None:
    conexion.execute(
        "INSERT INTO prod_movimiento (material_id, fecha, tipo, cantidad, placa, cliente, nota, "
        "origen, usuario, registrado) VALUES (1, '2026-10-01', ?, ?, '', '', '', 'manual', 'ana', "
        "'2026-10-01 08:00:00')",
        (tipo, cantidad),
    )


def _con_material(conexion: sqlite3.Connection) -> None:
    conexion.execute(
        "INSERT INTO prod_material (codigo, nombre, unidad_venta, existencia_minima, activo) "
        "VALUES ('AGR-12', 'Agregado', 't', '0', 1)"
    )


def test_le_sigue_la_de_los_calculos() -> None:
    """Plan vial, Tareas 4 y 4b: encima de esta van `ins_0008_prod_calculo` y
    `ins_0010_modulo` y `ins_0010_modulo`, la cabeza."""
    assert revision_head(Destino.INSTALACION) == "ins_0011_receta_ligante"


def test_crea_las_dos_tablas_con_sus_columnas(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert set(COLUMNAS) <= _tablas(conexion)
        for tabla, columnas in COLUMNAS.items():
            hallado = [f[1] for f in conexion.execute(f"PRAGMA table_info({tabla})")]
            assert hallado == columnas, tabla


def test_el_consumo_solo_cabe_despues_de_subir_y_lo_anterior_sobrevive(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        _con_material(conexion)
        _movimiento(conexion, "entrada", "100")
        _movimiento(conexion, "despacho", "30")
        conexion.commit()
        with pytest.raises(sqlite3.IntegrityError):
            _movimiento(conexion, "consumo")  # antes de subir no cabe
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        _movimiento(conexion, "consumo", "94")
        conexion.commit()
        filas = conexion.execute(
            "SELECT tipo, cantidad FROM prod_movimiento ORDER BY id"
        ).fetchall()
        assert filas == [("entrada", "100"), ("despacho", "30"), ("consumo", "94")]
        with pytest.raises(sqlite3.IntegrityError):
            _movimiento(conexion, "regalo")  # el resto de tipos sigue prohibido


def test_bajar_quita_las_tablas_y_los_consumos_y_conserva_lo_demas(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as conexion:
        _con_material(conexion)
        _movimiento(conexion, "entrada", "100")
        _movimiento(conexion, "consumo", "94")
        conexion.commit()
    deshacer_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert not set(COLUMNAS) & _tablas(conexion)
        assert conexion.execute("SELECT tipo, cantidad FROM prod_movimiento").fetchall() == [
            ("entrada", "100")
        ]
        with pytest.raises(sqlite3.IntegrityError):
            _movimiento(conexion, "consumo")
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert set(COLUMNAS) <= _tablas(conexion)


def test_una_base_que_ya_trae_las_tablas_y_el_check_se_adopta(tmp_path: Path) -> None:
    """Hecha con `create_all` (tablas nuevas y `CHECK` con consumo), la migracion no recrea nada."""
    from sqlalchemy import create_engine

    from produccion.modelo import Movimiento, RecetaComponente, RecetaRegistrada

    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        _con_material(conexion)
        _movimiento(conexion, "entrada", "100")
        conexion.commit()
        conexion.execute("DROP TABLE prod_movimiento")
        conexion.commit()
    motor = create_engine(f"sqlite:///{base.as_posix()}")
    try:
        for tabla in (Movimiento, RecetaRegistrada, RecetaComponente):
            tabla.__table__.create(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(base)) as conexion:
        _movimiento(conexion, "consumo", "7")
        conexion.commit()
        sql_antes = _sql_de(conexion, "prod_movimiento")

    aplicar_revisiones(base, Destino.INSTALACION, REVISION)

    with closing(sqlite3.connect(base)) as conexion:
        assert _sql_de(conexion, "prod_movimiento") == sql_antes  # adoptada, no recreada
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (REVISION,)
        ]
        assert conexion.execute("SELECT tipo, cantidad FROM prod_movimiento").fetchall() == [
            ("consumo", "7")
        ]
