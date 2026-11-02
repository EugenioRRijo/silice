"""`caso_0010_mp_carpeta`: la moneda de la carpeta de trabajo (MP-1, Tarea 1; D-MP1).

La tabla `mp_carpeta` (una sola fila, `id = 1`) guarda la moneda declarada, quién la declaró y
cuándo. Cuelga de `caso_0009_s3_paquete`; una base que ya la trae se adopta sin recrearla
(`_faltan`). Las pruebas suben y bajan hasta esta revisión con nombre (no hasta la cabeza), para
que las revisiones siguientes del plan (`caso_0011_mod_ficha_obra`…) no las rompan.

Oráculos: el DDL esperado (nombre, tipo, nulo) está escrito a mano.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from aplicacion.tablas_carpeta import crear_esquema_carpeta
from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

TABLA = "mp_carpeta"
REVISION = "caso_0010_mp_carpeta"
ANTERIOR = "caso_0009_s3_paquete"
#: (nombre, tipo SQL declarado, admite nulo), en orden.
COLUMNAS = [
    ("id", "INTEGER", False),
    ("moneda", "VARCHAR(10)", False),
    ("declarada_por", "VARCHAR(200)", False),
    ("declarada_el", "DATETIME", False),
]


def _url(ruta: Path) -> str:
    return f"sqlite:///{ruta.as_posix()}"


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {f[0] for f in filas} - {"alembic_version"}


def _instantanea_de_la_tabla(ruta: Path) -> dict:
    motor = create_engine(_url(ruta))
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)[TABLA]
    finally:
        motor.dispose()


def test_subir_crea_la_tabla_con_las_columnas_del_plan(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert TABLA in _tablas(ruta)
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    assert [(f[1], f[2]) for f in filas] == [c[:2] for c in COLUMNAS]
    # la clave primaria no lleva NOT NULL explícito: SQLite la informa nula en `table_info`
    assert [not f[3] for f in filas if f[1] != "id"] == [c[2] for c in COLUMNAS if c[0] != "id"]
    assert [f[1] for f in filas if f[5]] == ["id"]


def test_la_tabla_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        crear_esquema_carpeta(motor)
    finally:
        motor.dispose()
    assert _instantanea_de_la_tabla(migrada) == _instantanea_de_la_tabla(creada)


def test_bajar_a_la_anterior_quita_la_tabla_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert TABLA not in _tablas(ruta)
    assert "paq_recibido" in _tablas(ruta)
    assert leer_estado(ruta).revision == ANTERIOR
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert TABLA in _tablas(ruta)


def test_una_base_que_ya_trae_la_tabla_se_adopta_sin_recrearla(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    motor = create_engine(_url(ruta))
    try:
        crear_esquema_carpeta(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            f"INSERT INTO {TABLA} (id, moneda, declarada_por, declarada_el) "
            "VALUES (1, 'Bs', 'ana', '2026-10-25 09:30:00')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT id, moneda, declarada_por FROM {TABLA}").fetchall() == [
            (1, "Bs", "ana")
        ]


def test_la_base_anterior_con_datos_conserva_sus_listas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO lista_precios (id, nombre, moneda, fecha_vigencia, origen) "
            "VALUES (1, 'Base', 'Bs', '2026-07-01', '')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT nombre, moneda FROM lista_precios").fetchall() == [
            ("Base", "Bs")
        ]
        assert conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone() == (0,)
