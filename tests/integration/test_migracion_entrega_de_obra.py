"""Lote G5: la migración `caso_0025_entrega_de_obra` (`entrega_de_obra`).

Oráculos a mano: tabla aditiva en la base del caso, sin clave foránea a `core.models`; la migrada es
la del modelo (`aplicacion.tablas_entrega`); bajar la quita sin tocar lo demás y se puede volver a
subir; una base que ya la trae (creada con `crear_esquema_entrega`) se adopta conservando sus filas.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

REVISION = "caso_0025_entrega_de_obra"
ANTERIOR = "caso_0024_desperdicio_responsable"
TABLA = "entrega_de_obra"
COLUMNAS = [
    ("proyecto_codigo", "VARCHAR(40)", False),
    ("fecha_entrega", "DATE", True),
    ("actualizada", "DATETIME", False),
    ("actualizada_por", "VARCHAR(200)", False),
]


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        return {f[0] for f in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columnas(ruta: Path) -> list[tuple[str, str, bool]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    return [(f[1], f[2], not f[3]) for f in filas]


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)
    finally:
        motor.dispose()


def test_la_cabeza_del_caso_es_esta_revision() -> None:
    from operacion.base_datos import _guion

    guion = _guion(Destino.CASO)
    assert guion.get_heads() == [REVISION]
    assert guion.get_revision(REVISION).down_revision == ANTERIOR


def test_subir_crea_la_tabla_entrega_de_obra(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert TABLA not in _tablas(ruta)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta) == COLUMNAS


def test_la_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_entrega import crear_esquema_entrega

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(f"sqlite:///{creada.as_posix()}")
    try:
        crear_esquema_entrega(motor)
    finally:
        motor.dispose()
    assert _instantanea(migrada)[TABLA] == _instantanea(creada)[TABLA]


def test_bajar_quita_solo_la_tabla_y_lo_de_antes_queda(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO apu_desperdicio_guardado (partida_codigo, fecha_hora, responsable) "
            "VALUES ('P-1', '2026-11-20 09:00:00', 'Ana <ana>')"
        )
        conexion.execute(
            "INSERT INTO entrega_de_obra (proyecto_codigo, fecha_entrega, actualizada, "
            "actualizada_por) VALUES ('1', '2026-12-15', '2026-11-27 09:00:00', 'Ana <ana>')"
        )
        conexion.commit()
    antes = _tablas(ruta) - {TABLA}
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert _tablas(ruta) == antes
    assert leer_estado(ruta).revision == ANTERIOR
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(
            "SELECT partida_codigo, responsable FROM apu_desperdicio_guardado"
        ).fetchall()
    assert filas == [("P-1", "Ana <ana>")]
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert TABLA in _tablas(ruta)


def test_una_base_que_ya_trae_la_tabla_se_adopta(tmp_path: Path) -> None:
    from aplicacion.tablas_entrega import crear_esquema_entrega

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_entrega(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO entrega_de_obra (proyecto_codigo, fecha_entrega, actualizada, "
            "actualizada_por) VALUES ('1', '2026-12-15', '2026-11-27 09:00:00', 'Ana <ana>')"
        )
        conexion.commit()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(
            "SELECT proyecto_codigo, fecha_entrega, actualizada_por FROM entrega_de_obra"
        ).fetchall() == [("1", "2026-12-15", "Ana <ana>")]
