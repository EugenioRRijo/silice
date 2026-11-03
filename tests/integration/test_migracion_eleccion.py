"""`ins_0004_mod_eleccion`: la elección y las preferencias de cada cuenta en la instalación (MOD-0).

La tabla `mp_eleccion` guarda, por cuenta, la carpeta de trabajo (`caso`, nula = la carpeta de la
instalación), la obra (`proyecto`), el último módulo abierto y si el sidebar queda fijado. Cuelga de
`ins_0003_auditoria_libro`; una base que ya la trae se adopta sin recrearla (`_faltan`).

Oráculos: el DDL esperado (nombre, tipo, nulo) está escrito a mano.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from aplicacion.tablas_eleccion import METADATA_ELECCION
from migraciones.comun import instantanea_esquema
from operacion import config, respaldo
from operacion.base_datos import (
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    leer_estado,
    preparar_base,
    revision_head,
    revisiones_en_orden,
)

TABLA = "mp_eleccion"
REVISION = "ins_0004_mod_eleccion"
ANTERIOR = "ins_0003_auditoria_libro"
#: La que cuelga de esta (MP-4, T18) y es la cabeza de la instalación.
SIGUIENTE = "ins_0005_mp_indice_aprobacion"
CABEZA = "ins_0011_receta_ligante"
#: (nombre, tipo SQL declarado, admite nulo), en orden.
COLUMNAS = [
    ("usuario_id", "INTEGER", False),
    ("caso", "VARCHAR(255)", True),
    ("proyecto", "VARCHAR(120)", True),
    ("modulo", "VARCHAR(20)", True),
    ("sidebar_fijado", "BOOLEAN", False),
    ("fecha", "DATETIME", False),
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


def test_la_revision_cuelga_de_la_auditoria_del_libro_y_de_ella_el_indice_de_aprobacion() -> None:
    orden = revisiones_en_orden(Destino.INSTALACION)
    indice = orden.index(REVISION)
    assert orden[indice - 1 : indice + 2] == [ANTERIOR, REVISION, SIGUIENTE]
    assert revision_head(Destino.INSTALACION) == CABEZA


def test_subir_crea_la_tabla_con_las_columnas_del_plan(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION, REVISION)
    assert TABLA in _tablas(ruta)
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    assert [(f[1], f[2]) for f in filas] == [c[:2] for c in COLUMNAS]
    # la clave primaria no lleva NOT NULL explícito: SQLite la informa nula en `table_info`
    assert [not f[3] for f in filas if f[1] != "usuario_id"] == [
        c[2] for c in COLUMNAS if c[0] != "usuario_id"
    ]
    assert [f[1] for f in filas if f[5]] == ["usuario_id"]


def test_el_sidebar_nace_sin_fijar_y_la_carpeta_puede_ser_nula(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            f"INSERT INTO {TABLA} (usuario_id, fecha) VALUES (1, '2026-10-25 08:00:00')"
        )
        conexion.commit()
        assert conexion.execute(
            f"SELECT caso, proyecto, modulo, sidebar_fijado FROM {TABLA}"
        ).fetchall() == [(None, None, None, 0)]


def test_la_tabla_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.INSTALACION)
    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        METADATA_ELECCION.create_all(motor)
    finally:
        motor.dispose()
    assert _instantanea_de_la_tabla(migrada) == _instantanea_de_la_tabla(creada)


def test_bajar_a_la_anterior_quita_la_tabla_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    deshacer_revisiones(ruta, Destino.INSTALACION, ANTERIOR)
    assert TABLA not in _tablas(ruta)
    assert "auditoria_libro" in _tablas(ruta)
    assert leer_estado(ruta).revision == ANTERIOR
    aplicar_revisiones(ruta, Destino.INSTALACION)
    assert TABLA in _tablas(ruta)


def test_subir_dos_veces_no_falla(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    aplicar_revisiones(ruta, Destino.INSTALACION)
    assert leer_estado(ruta).revision == CABEZA
    assert TABLA in _tablas(ruta)


def test_una_base_que_ya_trae_la_tabla_se_adopta_sin_recrearla(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION, ANTERIOR)
    motor = create_engine(_url(ruta))
    try:
        METADATA_ELECCION.create_all(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            f"INSERT INTO {TABLA} (usuario_id, caso, sidebar_fijado, fecha) "
            "VALUES (3, 'obra.db', 1, '2026-10-25 08:00:00')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.INSTALACION)

    assert leer_estado(ruta).revision == CABEZA
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT usuario_id, caso FROM {TABLA}").fetchall() == [
            (3, "obra.db")
        ]


def test_la_base_anterior_con_datos_se_respalda_y_migra(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO prod_material (codigo, nombre, unidad_venta, existencia_minima, activo) "
            "VALUES ('ARENA', 'Arena', 'm3', '20', 1)"
        )
        conexion.commit()

    resultado = preparar_base(ruta, Destino.INSTALACION)

    assert resultado.revision_origen == ANTERIOR
    assert resultado.revision_destino == CABEZA
    assert resultado.juego is not None and resultado.juego.is_dir()
    assert respaldo.listar_juegos(config.carpeta_respaldos())
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT codigo FROM prod_material").fetchall() == [("ARENA",)]
        assert conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone() == (0,)
