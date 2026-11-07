"""F5 vial, tarea 3: la migración `caso_0022_apu_desperdicio` (la traza del desperdicio).

Oráculos a mano: dos tablas aditivas, sin clave foránea a `core.models`, con las cifras como texto
de 40 (`DecimalExacto`); la migrada es la del modelo; bajar las quita sin tocar lo demás; una base
que ya las trae (creadas con `crear_esquema_desperdicio`) se adopta.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

REVISION = "caso_0022_apu_desperdicio"
ANTERIOR = "caso_0021_vial_transporte"
TABLAS = ("apu_desperdicio_guardado", "apu_desperdicio")
LINEA = [
    ("id", "INTEGER", False),
    ("guardado_id", "INTEGER", False),
    ("orden", "INTEGER", False),
    ("descripcion", "VARCHAR(300)", False),
    ("unidad", "VARCHAR(40)", False),
    ("cantidad_neta", "VARCHAR(40)", False),
    ("desperdicio_pct", "VARCHAR(40)", False),
    ("cantidad", "VARCHAR(40)", False),
]


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        return {f[0] for f in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columnas(ruta: Path, tabla: str) -> list[tuple[str, str, bool]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({tabla})").fetchall()
    return [(f[1], f[2], not f[3]) for f in filas]


def test_la_cabeza_del_caso_es_esta_revision() -> None:
    from operacion.base_datos import _guion

    assert _guion(Destino.CASO).get_heads() == [REVISION]


def test_subir_crea_las_dos_tablas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert not set(TABLAS) & _tablas(ruta)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta, "apu_desperdicio") == LINEA
    assert [c[0] for c in _columnas(ruta, "apu_desperdicio_guardado")] == [
        "id",
        "partida_codigo",
        "fecha_hora",
    ]


def test_la_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_desperdicio import crear_esquema_desperdicio

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(f"sqlite:///{creada.as_posix()}")
    try:
        crear_esquema_desperdicio(motor)
        with create_engine(f"sqlite:///{migrada.as_posix()}").connect() as a, motor.connect() as b:
            de_la_migracion, del_modelo = instantanea_esquema(a), instantanea_esquema(b)
    finally:
        motor.dispose()
    for tabla in TABLAS:
        assert de_la_migracion[tabla] == del_modelo[tabla]


def test_bajar_quita_solo_las_dos_tablas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    antes = _tablas(ruta) - set(TABLAS)
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert _tablas(ruta) == antes
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert set(TABLAS) <= _tablas(ruta)


def test_una_base_que_ya_trae_las_tablas_se_adopta(tmp_path: Path) -> None:
    from aplicacion.tablas_desperdicio import crear_esquema_desperdicio

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_desperdicio(motor)
    finally:
        motor.dispose()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta, "apu_desperdicio") == LINEA
