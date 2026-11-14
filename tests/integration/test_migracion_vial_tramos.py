"""`caso_0019_vial_tramos`: los tramos viales guardados por versión (Tarea 8 del plan vial).

Oráculo, escrito a mano: dos tablas aditivas. `vial_tramos_guardado` (una fila por guardado de una
versión: `id`, `version_id`, `usuario String(200)`, `fecha_hora`, `fuente String(300)`) y
`vial_tramo` (una por tramo del guardado: `id`, `guardado_id`, `orden`, `tramo_id String(80)`,
cuatro cifras en texto de 40 y `capas`, `demarcacion` en texto). Ninguna tabla existente cambia;
bajar quita las dos y sube otra vez sin pérdida del resto.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from migraciones.comun import instantanea_esquema
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, leer_estado

REVISION = "caso_0019_vial_tramos"
ANTERIOR = "caso_0018_mp_corte_tasa"
TABLAS = ("vial_tramos_guardado", "vial_tramo")
#: La última revisión que cambia estas tablas (F5 vial, tarea 2: la columna `transporte`): el
#: modelo de `aplicacion/tablas_vial.py` es el de esa revisión, no el de `caso_0019`.
REVISION_DEL_MODELO = "caso_0021_vial_transporte"
TRANSPORTE = ("transporte", "VARCHAR(10)", True)
GUARDADO = [
    ("id", "INTEGER", False),
    ("version_id", "INTEGER", False),
    ("usuario", "VARCHAR(200)", False),
    ("fecha_hora", "DATETIME", False),
    ("fuente", "VARCHAR(300)", False),
]
TRAMO = [
    ("id", "INTEGER", False),
    ("guardado_id", "INTEGER", False),
    ("orden", "INTEGER", False),
    ("tramo_id", "VARCHAR(80)", False),
    ("progresiva_ini_km", "VARCHAR(40)", False),
    ("progresiva_fin_km", "VARCHAR(40)", False),
    ("ancho_m", "VARCHAR(40)", False),
    ("distancia_planta_km", "VARCHAR(40)", True),
    ("capas", "TEXT", False),
    ("demarcacion", "TEXT", False),
]


def _columnas(ruta: Path, tabla: str) -> list[tuple[str, str, bool]]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({tabla})").fetchall()
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


def test_cuelga_de_la_ultima_del_caso() -> None:
    from migraciones.caso.versions import caso_0019_vial_tramos as revision

    assert revision.revision == REVISION
    assert revision.down_revision == ANTERIOR


def test_subir_crea_las_dos_tablas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert not set(TABLAS) & _tablas(ruta)
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    assert _columnas(ruta, "vial_tramos_guardado") == GUARDADO
    assert _columnas(ruta, "vial_tramo") == TRAMO


def test_las_tablas_migradas_son_las_del_modelo(tmp_path: Path) -> None:
    from aplicacion.tablas_vial import crear_esquema_vial

    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION_DEL_MODELO)
    creada = tmp_path / "creada.db"
    motor = create_engine(f"sqlite:///{creada.as_posix()}")
    try:
        crear_esquema_vial(motor)
    finally:
        motor.dispose()
    de_la_migracion = _instantanea(migrada)
    de_el_modelo = _instantanea(creada)
    for tabla in TABLAS:
        assert de_la_migracion[tabla] == de_el_modelo[tabla]


def test_bajar_quita_solo_las_dos_tablas_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    antes = _tablas(ruta) - set(TABLAS)
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert leer_estado(ruta).revision == ANTERIOR
    assert _tablas(ruta) == antes
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert set(TABLAS) <= _tablas(ruta)


def test_una_base_que_ya_trae_las_tablas_se_adopta(tmp_path: Path) -> None:
    from aplicacion.tablas_vial import crear_esquema_vial

    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema_vial(motor)  # las tablas ya creadas al guardar el primer tramo
    finally:
        motor.dispose()
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    # el modelo de hoy ya trae la columna de `caso_0021`: la adopción la conserva
    assert _columnas(ruta, "vial_tramo") == [*TRAMO, TRANSPORTE]
