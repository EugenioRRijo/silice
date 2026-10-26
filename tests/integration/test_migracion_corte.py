"""`caso_0017_mp_corte`: los precios declarados del corte de control (Tarea 25).

Las pruebas suben y bajan hasta esta revisión con nombre (no hasta la cabeza); la anterior se lee
de la propia revisión (`down_revision`), porque el orquestador la ajusta al integrar.

Oráculo: el DDL que fija el plan, escrito a mano: `mp_precio_corte` (`id`, `proyecto_id`,
`descripcion_insumo`, `unidad`, `precio`, `moneda`, `fecha`, `fuente String(300)`, `responsable`,
`fecha_hora`), ninguna columna admite nulo; solo inserción.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

TABLA = "mp_precio_corte"
REVISION = "caso_0017_mp_corte"
ARCHIVO = Path(__file__).parents[2] / "migraciones" / "caso" / "versions" / f"{REVISION}.py"
#: (nombre, tipo SQL declarado, admite nulo, posición en la clave primaria), en orden.
COLUMNAS = [
    ("id", "INTEGER", False, 1),  # SQLAlchemy declara NOT NULL toda clave primaria
    ("proyecto_id", "INTEGER", False, 0),
    ("descripcion_insumo", "VARCHAR(300)", False, 0),
    ("unidad", "VARCHAR(20)", False, 0),
    ("precio", "VARCHAR(40)", False, 0),
    ("moneda", "VARCHAR(10)", False, 0),
    ("fecha", "DATE", False, 0),
    ("fuente", "VARCHAR(300)", False, 0),
    ("responsable", "VARCHAR(200)", False, 0),
    ("fecha_hora", "DATETIME", False, 0),
]


def _anterior() -> str:
    especificacion = importlib.util.spec_from_file_location("revision_corte", ARCHIVO)
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


def _columnas(ruta: Path) -> list[tuple[str, str, bool, int]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    return [(f[1], f[2], not f[3], f[5]) for f in filas]


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(_url(ruta))
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)[TABLA]
    finally:
        motor.dispose()


def test_va_despues_de_la_procura() -> None:
    assert _anterior() == "caso_0016_mp_procura"


def test_subir_crea_la_tabla_con_las_columnas_del_plan(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert TABLA in _tablas(ruta)
    assert _columnas(ruta) == COLUMNAS


def test_la_tabla_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_corte import crear_esquema_corte

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        crear_esquema_corte(motor)
    finally:
        motor.dispose()
    assert _instantanea(migrada) == _instantanea(creada)


def test_bajar_a_la_anterior_quita_la_tabla_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    anterior = _anterior()
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    deshacer_revisiones(ruta, Destino.CASO, anterior)
    assert TABLA not in _tablas(ruta)
    assert "mp_compra" in _tablas(ruta)
    assert leer_estado(ruta).revision == anterior
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert TABLA in _tablas(ruta)


def test_una_base_que_ya_trae_la_tabla_se_adopta_sin_recrearla(tmp_path: Path) -> None:
    from aplicacion.tablas_corte import crear_esquema_corte

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, _anterior())
    motor = create_engine(_url(ruta))
    try:
        crear_esquema_corte(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            f"INSERT INTO {TABLA} (proyecto_id, descripcion_insumo, unidad, precio, moneda, fecha, "
            "fuente, responsable, fecha_hora) VALUES (1, 'Cemento gris', 'saco', '20.00', 'Bs', "
            "'2026-11-10', 'cotización ficticia', 'Ana <ana>', '2026-11-10 09:00:00')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT precio FROM {TABLA}").fetchall() == [("20.00",)]
