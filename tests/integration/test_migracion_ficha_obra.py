"""`caso_0011_mod_ficha_obra`: la ficha de la obra (cliente y ubicación; MOD-3a).

La tabla `ficha_obra` guarda por obra (`proyecto_id`, sin clave foránea a `core.models`) su
cliente y su ubicación. Cuelga de `caso_0010_mp_carpeta`; una base que ya la trae se adopta sin
recrearla (`_faltan`). Las pruebas suben y bajan hasta esta revisión con nombre.

Oráculos: el DDL esperado (nombre, tipo, nulo, valor por omisión) está escrito a mano.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from aplicacion.tablas_obra import crear_esquema_obra
from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

TABLA = "ficha_obra"
REVISION = "caso_0011_mod_ficha_obra"
ANTERIOR = "caso_0010_mp_carpeta"
#: (nombre, tipo SQL declarado), en orden.
COLUMNAS = [("proyecto_id", "INTEGER"), ("cliente", "VARCHAR(200)"), ("ubicacion", "VARCHAR(200)")]


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
    assert [(f[1], f[2]) for f in filas] == COLUMNAS
    assert [f[1] for f in filas if f[5]] == ["proyecto_id"]
    por_nombre = {f[1]: f for f in filas}
    for columna in ("cliente", "ubicacion"):
        assert por_nombre[columna][3] == 1  # NOT NULL
        assert por_nombre[columna][4] == "''"  # por omisión, el texto vacío


def test_sin_cliente_ni_ubicacion_la_fila_queda_vacia(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(f"INSERT INTO {TABLA} (proyecto_id) VALUES (5)")
        assert conexion.execute(f"SELECT cliente, ubicacion FROM {TABLA}").fetchall() == [("", "")]


def test_la_tabla_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        crear_esquema_obra(motor)
    finally:
        motor.dispose()
    assert _instantanea_de_la_tabla(migrada) == _instantanea_de_la_tabla(creada)


def test_bajar_a_la_anterior_quita_la_tabla_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert TABLA not in _tablas(ruta)
    assert "mp_carpeta" in _tablas(ruta)
    assert leer_estado(ruta).revision == ANTERIOR
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert TABLA in _tablas(ruta)


def test_dos_subidas_seguidas_no_fallan(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION


def test_una_base_que_ya_trae_la_tabla_se_adopta_sin_recrearla(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    motor = create_engine(_url(ruta))
    try:
        crear_esquema_obra(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            f"INSERT INTO {TABLA} (proyecto_id, cliente, ubicacion) "
            "VALUES (3, 'Contratista Demo, C.A.', 'Maracay')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT * FROM {TABLA}").fetchall() == [
            (3, "Contratista Demo, C.A.", "Maracay")
        ]


def test_la_base_anterior_con_datos_conserva_sus_filas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO mp_carpeta (id, moneda, declarada_por, declarada_el) "
            "VALUES (1, 'Bs', 'ana', '2026-10-25 09:30:00')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT moneda FROM mp_carpeta").fetchall() == [("Bs",)]
        assert conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone() == (0,)
