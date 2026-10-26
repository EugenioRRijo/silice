"""`caso_0012_mp_medicion`: las notas de medición de los renglones de la Hoja (Tarea 9).

La tabla `mp_nota_medicion` guarda la nota de cada renglón agregado a mano, por obra, versión y
clave del renglón. Las pruebas suben y bajan hasta esta revisión con nombre (no hasta la cabeza);
la anterior se lee de la propia revisión (`down_revision`), porque el orquestador la ajusta al
integrar (el número no es el orden: va después de `caso_0014_mp_aprobacion`).

Oráculos: el DDL que fija el plan (`id`, `proyecto_id Integer`, `version String(40)`,
`clave String(200)`, `nota String(500)`), todo obligatorio, y una sola nota por renglón de una
versión; escritos a mano.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

TABLA = "mp_nota_medicion"
REVISION = "caso_0012_mp_medicion"
ARCHIVO = Path(__file__).parents[2] / "migraciones" / "caso" / "versions" / f"{REVISION}.py"
#: (nombre, tipo SQL declarado, admite nulo), en orden.
COLUMNAS = [
    ("id", "INTEGER", False),
    ("proyecto_id", "INTEGER", False),
    ("version", "VARCHAR(40)", False),
    ("clave", "VARCHAR(200)", False),
    ("nota", "VARCHAR(500)", False),
]


def _anterior() -> str:
    especificacion = importlib.util.spec_from_file_location("revision_medicion", ARCHIVO)
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


def _insertar(conexion: sqlite3.Connection, ident: int, clave: str) -> None:
    conexion.execute(
        f"INSERT INTO {TABLA} (id, proyecto_id, version, clave, nota) "
        "VALUES (?, 1, 'VIV-001', ?, '6 m × 35 m de muro')",
        (ident, clave),
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
    from aplicacion.tablas_medicion import crear_esquema_medicion

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        crear_esquema_medicion(motor)
    finally:
        motor.dispose()
    assert _instantanea_de_la_tabla(migrada) == _instantanea_de_la_tabla(creada)


def test_una_sola_nota_por_renglon_de_una_version(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    with closing(sqlite3.connect(ruta)) as conexion:
        _insertar(conexion, 1, "OBRA-04|a-mano:1")
        with pytest.raises(sqlite3.IntegrityError):
            _insertar(conexion, 2, "OBRA-04|a-mano:1")
        _insertar(conexion, 3, "OBRA-04|a-mano:2")
        conexion.commit()
        assert conexion.execute(f"SELECT id FROM {TABLA} ORDER BY id").fetchall() == [(1,), (3,)]


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
    from aplicacion.tablas_medicion import crear_esquema_medicion

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, _anterior())
    motor = create_engine(_url(ruta))
    try:
        crear_esquema_medicion(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        _insertar(conexion, 1, "OBRA-04|a-mano:1")
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT id, clave FROM {TABLA}").fetchall() == [
            (1, "OBRA-04|a-mano:1")
        ]
