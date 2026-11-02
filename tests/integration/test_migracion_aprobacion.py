"""`caso_0014_mp_aprobacion`: el rastro de aprobaciones de la carpeta (MP-4, Tarea 17).

La tabla `mp_aprobacion_evento` (solo inserción) guarda cada envío, retiro y dictamen con el sello
del eslabón de su versión y su propia huella encadenada a la anterior de su obra. Las pruebas suben
y bajan hasta esta revisión con nombre (no hasta la cabeza), para que las revisiones siguientes del
plan no las rompan; la anterior se lee de la propia revisión (`down_revision`), porque el
orquestador la ajusta al integrar (`caso_0013_mp_mercado` cuando exista).

Oráculos: el DDL esperado (nombre, tipo, nulo) y las dos restricciones únicas, escritos a mano.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from aplicacion.tablas_aprobacion import crear_esquema_aprobacion
from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

TABLA = "mp_aprobacion_evento"
REVISION = "caso_0014_mp_aprobacion"
ARCHIVO = Path(__file__).parents[2] / "migraciones" / "caso" / "versions" / f"{REVISION}.py"
#: (nombre, tipo SQL declarado, admite nulo), en orden.
COLUMNAS = [
    ("id", "INTEGER", False),
    ("proyecto_id", "INTEGER", False),
    ("tipo", "VARCHAR(10)", False),
    ("version", "VARCHAR(40)", False),
    ("huella_version", "VARCHAR(64)", False),
    ("resultado", "VARCHAR(30)", True),
    ("notas", "VARCHAR(2000)", False),
    ("usuario", "VARCHAR(200)", False),
    ("fecha_hora", "DATETIME", False),
    ("armo", "BOOLEAN", False),
    ("cierre_de", "INTEGER", True),
    ("anterior", "VARCHAR(64)", False),
    ("huella", "VARCHAR(64)", False),
]


def _anterior() -> str:
    especificacion = importlib.util.spec_from_file_location("revision_aprobacion", ARCHIVO)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    assert modulo.revision == REVISION
    return modulo.down_revision


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


def _insertar(conexion: sqlite3.Connection, ident: int, anterior: str, cierre_de) -> None:
    conexion.execute(
        f"INSERT INTO {TABLA} (id, proyecto_id, tipo, version, huella_version, resultado, notas, "
        "usuario, fecha_hora, armo, cierre_de, anterior, huella) VALUES (?, 1, 'envio', 'VIV-001', "
        "?, NULL, '', 'Ana <ana>', '2026-10-19 09:00:00', 1, ?, ?, ?)",
        (ident, "b" * 64, cierre_de, anterior, str(ident) * 64),
    )


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
        crear_esquema_aprobacion(motor)
    finally:
        motor.dispose()
    assert _instantanea_de_la_tabla(migrada) == _instantanea_de_la_tabla(creada)


def test_la_base_migrada_rechaza_dos_cierres_y_dos_hijos_del_mismo_anterior(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    with closing(sqlite3.connect(ruta)) as conexion:
        _insertar(conexion, 1, "0" * 64, None)
        _insertar(conexion, 2, "1" * 64, 1)
        with pytest.raises(sqlite3.IntegrityError):
            _insertar(conexion, 3, "2" * 64, 1)  # el envío 1 ya tiene cierre
        with pytest.raises(sqlite3.IntegrityError):
            _insertar(conexion, 4, "1" * 64, None)  # dos eventos colgados del mismo anterior
        conexion.commit()
        assert conexion.execute(f"SELECT id FROM {TABLA} ORDER BY id").fetchall() == [(1,), (2,)]


def test_bajar_a_la_anterior_quita_la_tabla_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    anterior = _anterior()
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    deshacer_revisiones(ruta, Destino.CASO, anterior)
    assert TABLA not in _tablas(ruta)
    assert "mp_carpeta" in _tablas(ruta)
    assert leer_estado(ruta).revision == anterior
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert TABLA in _tablas(ruta)


def test_una_base_que_ya_trae_la_tabla_se_adopta_sin_recrearla(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, _anterior())
    motor = create_engine(_url(ruta))
    try:
        crear_esquema_aprobacion(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        _insertar(conexion, 1, "0" * 64, None)
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT id, version FROM {TABLA}").fetchall() == [(1, "VIV-001")]


def test_la_base_anterior_con_datos_conserva_sus_versiones(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, _anterior())
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO proyecto (id, nombre, descripcion, dominio) "
            "VALUES (1, 'Vivienda Demo', '', '')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT nombre FROM proyecto").fetchall() == [("Vivienda Demo",)]
        assert conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone() == (0,)
