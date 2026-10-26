"""`caso_0016_mp_procura`: los plazos de entrega y las compras de la procura (Tarea 23).

Las pruebas suben y bajan hasta esta revisión con nombre (no hasta la cabeza); la anterior se lee
de la propia revisión (`down_revision`), porque el orquestador la ajusta al integrar.

Oráculos: el DDL que fija el plan, escrito a mano: `mp_plazo_entrega` (`proyecto_id`,
`descripcion_insumo`, `unidad`, `dias Integer`; clave primaria compuesta de las tres primeras) y
`mp_compra` (`id`, `proyecto_id`, `descripcion_insumo`, `unidad`, `evento`, `fecha`, `cantidad`,
`precio` y `moneda` que admiten nulo, `responsable`, `fecha_hora`).
"""

from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

PLAZO = "mp_plazo_entrega"
COMPRA = "mp_compra"
REVISION = "caso_0016_mp_procura"
ARCHIVO = Path(__file__).parents[2] / "migraciones" / "caso" / "versions" / f"{REVISION}.py"
#: (nombre, tipo SQL declarado, admite nulo, posición en la clave primaria), en orden.
COLUMNAS_PLAZO = [
    ("proyecto_id", "INTEGER", False, 1),
    ("descripcion_insumo", "VARCHAR(300)", False, 2),
    ("unidad", "VARCHAR(20)", False, 3),
    ("dias", "INTEGER", False, 0),
]
COLUMNAS_COMPRA = [
    ("id", "INTEGER", True, 1),  # SQLite informa nula la clave primaria entera en `table_info`
    ("proyecto_id", "INTEGER", False, 0),
    ("descripcion_insumo", "VARCHAR(300)", False, 0),
    ("unidad", "VARCHAR(20)", False, 0),
    ("evento", "VARCHAR(10)", False, 0),
    ("fecha", "DATE", False, 0),
    ("cantidad", "VARCHAR(40)", True, 0),
    ("precio", "VARCHAR(40)", True, 0),
    ("moneda", "VARCHAR(10)", True, 0),
    ("responsable", "VARCHAR(200)", False, 0),
    ("fecha_hora", "DATETIME", False, 0),
]


def _anterior() -> str:
    especificacion = importlib.util.spec_from_file_location("revision_procura", ARCHIVO)
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


def _columnas(ruta: Path, tabla: str) -> list[tuple[str, str, bool, int]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({tabla})").fetchall()
    return [(f[1], f[2], not f[3], f[5]) for f in filas]


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(_url(ruta))
    try:
        with motor.connect() as conexion:
            esquema = instantanea_esquema(conexion)
            return {tabla: esquema[tabla] for tabla in (PLAZO, COMPRA)}
    finally:
        motor.dispose()


def test_subir_crea_las_dos_tablas_con_las_columnas_del_plan(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert {PLAZO, COMPRA} <= _tablas(ruta)
    assert _columnas(ruta, PLAZO) == COLUMNAS_PLAZO
    assert _columnas(ruta, COMPRA) == COLUMNAS_COMPRA


def test_las_tablas_migradas_son_las_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_procura import crear_esquema_procura

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        crear_esquema_procura(motor)
    finally:
        motor.dispose()
    assert _instantanea(migrada) == _instantanea(creada)


def test_un_solo_plazo_por_insumo_de_una_obra(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    insertar = f"INSERT INTO {PLAZO} (proyecto_id, descripcion_insumo, unidad, dias) VALUES "
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(insertar + "(1, 'Cemento gris', 'saco', 3)")
        try:
            conexion.execute(insertar + "(1, 'Cemento gris', 'saco', 5)")
        except sqlite3.IntegrityError:
            repetido = True
        else:
            repetido = False
        conexion.execute(insertar + "(2, 'Cemento gris', 'saco', 5)")
        conexion.commit()
        assert repetido
        assert conexion.execute(f"SELECT proyecto_id, dias FROM {PLAZO}").fetchall() == [
            (1, 3),
            (2, 5),
        ]


def test_bajar_a_la_anterior_quita_las_tablas_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    anterior = _anterior()
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    deshacer_revisiones(ruta, Destino.CASO, anterior)
    assert not {PLAZO, COMPRA} & _tablas(ruta)
    assert "mp_observacion" in _tablas(ruta)
    assert leer_estado(ruta).revision == anterior
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert {PLAZO, COMPRA} <= _tablas(ruta)


def test_una_base_que_ya_trae_las_tablas_se_adopta_sin_recrearlas(tmp_path: Path) -> None:
    from aplicacion.tablas_procura import crear_esquema_procura

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, _anterior())
    motor = create_engine(_url(ruta))
    try:
        crear_esquema_procura(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            f"INSERT INTO {PLAZO} (proyecto_id, descripcion_insumo, unidad, dias) "
            "VALUES (1, 'Cemento gris', 'saco', 4)"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT dias FROM {PLAZO}").fetchall() == [(4,)]
