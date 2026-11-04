"""`caso_0020_hoja_importaciones`: el registro de importaciones de la obra (Tarea 10 de F4).

Oráculo, escrito a mano: una tabla aditiva `hoja_importaciones` (`id`, `version_id` entero,
`tipo String(20)`, `archivo String(255)`, `fecha_hora`, `usuario String(200)`, `resumen
String(300)`) con un índice por `version_id`. Ninguna tabla existente cambia; bajar quita solo
esa tabla y se puede volver a subir. Una base que ya la trae (creada al guardar la primera
importación en una base sin migrar) se adopta sin recrearla.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

REVISION = "caso_0020_hoja_importaciones"
ANTERIOR = "caso_0019_vial_tramos"
TABLA = "hoja_importaciones"
COLUMNAS = [
    ("id", "INTEGER", False),
    ("version_id", "INTEGER", False),
    ("tipo", "VARCHAR(20)", False),
    ("archivo", "VARCHAR(255)", False),
    ("fecha_hora", "DATETIME", False),
    ("usuario", "VARCHAR(200)", False),
    ("resumen", "VARCHAR(300)", False),
]


def _columnas(ruta: Path) -> list[tuple[str, str, bool]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    return [(f[1], f[2], not f[3]) for f in filas]


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        return {f[0] for f in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)
    finally:
        motor.dispose()


def test_la_cabeza_del_caso_es_esta_revision() -> None:
    from operacion.base_datos import _guion

    assert _guion(Destino.CASO).get_heads() == [REVISION]


def test_subir_crea_la_tabla(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert TABLA not in _tablas(ruta)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta) == COLUMNAS


def test_la_tabla_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_importaciones import crear_esquema_importaciones

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(f"sqlite:///{creada.as_posix()}")
    try:
        crear_esquema_importaciones(motor)
    finally:
        motor.dispose()
    assert _instantanea(migrada)[TABLA] == _instantanea(creada)[TABLA]


def test_bajar_quita_solo_la_tabla_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    antes = _tablas(ruta) - {TABLA}
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert leer_estado(ruta).revision == ANTERIOR
    assert _tablas(ruta) == antes
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert TABLA in _tablas(ruta)


def test_una_base_que_ya_trae_la_tabla_se_adopta(tmp_path: Path) -> None:
    from aplicacion.tablas_importaciones import crear_esquema_importaciones

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_importaciones(motor)  # la tabla ya creada al guardar la primera importación
    finally:
        motor.dispose()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta) == COLUMNAS
