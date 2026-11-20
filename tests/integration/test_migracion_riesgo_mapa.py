"""Mejora de la DS-81: la migración `caso_0023_riesgo_mapa` (el mapa de series que recuerda Riesgo).

Oráculos a mano: dos tablas aditivas, sin clave foránea a `core.models`; la migrada es la del
modelo; bajar las quita sin tocar lo demás y se puede volver a subir; una base que ya las trae
(creadas con `crear_esquema_riesgo`) se adopta; lo guardado antes de la migración sigue ahí.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

REVISION = "caso_0023_riesgo_mapa"
ANTERIOR = "caso_0022_apu_desperdicio"
TABLAS = ("riesgo_mapa_guardado", "riesgo_mapa_serie")
GUARDADO = [
    ("id", "INTEGER", False),
    ("version_id", "INTEGER", False),
    ("usuario", "VARCHAR(200)", False),
    ("fecha_hora", "DATETIME", False),
]
SERIE = [
    ("id", "INTEGER", False),
    ("guardado_id", "INTEGER", False),
    ("insumo", "VARCHAR(500)", False),
    ("serie", "VARCHAR(40)", False),
]


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        return {f[0] for f in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columnas(ruta: Path, tabla: str) -> list[tuple[str, str, bool]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({tabla})").fetchall()
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


def test_subir_crea_las_dos_tablas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert not set(TABLAS) & _tablas(ruta)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta, "riesgo_mapa_guardado") == GUARDADO
    assert _columnas(ruta, "riesgo_mapa_serie") == SERIE


def test_la_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_riesgo import crear_esquema_riesgo

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(f"sqlite:///{creada.as_posix()}")
    try:
        crear_esquema_riesgo(motor)
    finally:
        motor.dispose()
    de_la_migracion, del_modelo = _instantanea(migrada), _instantanea(creada)
    for tabla in TABLAS:
        assert de_la_migracion[tabla] == del_modelo[tabla]


def test_bajar_quita_solo_las_dos_tablas_y_lo_de_antes_queda(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO apu_desperdicio_guardado (partida_codigo, fecha_hora) "
            "VALUES ('P-1', '2026-11-20 09:00:00')"
        )
        conexion.commit()
    antes = _tablas(ruta) - set(TABLAS)
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert _tablas(ruta) == antes
    assert leer_estado(ruta).revision == ANTERIOR
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT partida_codigo FROM apu_desperdicio_guardado").fetchall() == [
            ("P-1",)
        ]
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert set(TABLAS) <= _tablas(ruta)


def test_una_base_que_ya_trae_las_tablas_se_adopta(tmp_path: Path) -> None:
    from aplicacion.tablas_riesgo import crear_esquema_riesgo

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_riesgo(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO riesgo_mapa_guardado (version_id, usuario, fecha_hora) "
            "VALUES (1, 'Ana <ana>', '2026-11-20 09:00:00')"
        )
        conexion.commit()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT usuario FROM riesgo_mapa_guardado").fetchall() == [
            ("Ana <ana>",)
        ]
