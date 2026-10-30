"""`ins_0005_mp_indice_aprobacion`: el índice de aprobaciones de todas las carpetas (MP-4, T18).

La tabla `mp_indice_aprobacion` refleja en la instalación los envíos a aprobación de cada carpeta
de trabajo (la fuente de verdad sigue siendo la carpeta), con `UNIQUE(caso, envio_id)`. Cuelga de
`ins_0004_mod_eleccion`; una base que ya la trae se adopta sin recrearla (`_faltan`).

Oráculos: el DDL esperado (nombre, tipo, nulo) está escrito a mano.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from aplicacion.tablas_indice_aprobacion import METADATA_INDICE_APROBACION
from migraciones.comun import instantanea_esquema
from operacion.base_datos import (
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    leer_estado,
    revision_head,
)

TABLA = "mp_indice_aprobacion"
REVISION = "ins_0005_mp_indice_aprobacion"
ANTERIOR = "ins_0004_mod_eleccion"
#: (nombre, tipo SQL declarado, admite nulo), en orden.
COLUMNAS = [
    ("id", "INTEGER", False),
    ("caso", "VARCHAR(255)", False),
    ("envio_id", "INTEGER", False),
    ("proyecto", "VARCHAR(120)", False),
    ("obra", "VARCHAR(200)", False),
    ("version", "VARCHAR(40)", False),
    ("total", "VARCHAR(40)", False),
    ("moneda", "VARCHAR(10)", False),
    ("estado", "VARCHAR(30)", False),
    ("enviado_por", "VARCHAR(200)", False),
    ("enviado_el", "DATETIME", False),
    ("dictamen_por", "VARCHAR(200)", True),
    ("dictamen_el", "DATETIME", True),
    ("nota", "VARCHAR(2000)", False),
    ("notas", "VARCHAR(2000)", False),
    ("armo", "BOOLEAN", False),
]
FILA = (
    "INSERT INTO mp_indice_aprobacion (caso, envio_id, proyecto, obra, version, total, moneda, "
    "estado, enviado_por, enviado_el, nota, notas, armo) VALUES ('obra.db', 1, '1', "
    "'Vivienda Demo 80 m2', 'VIV-001', '1500.50', 'Bs', 'en_aprobacion', 'Ana <ana>', "
    "'2026-10-20 10:30:00', '', '', 0)"
)


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


def test_la_revision_cuelga_de_la_eleccion_y_la_sigue_el_costo_de_produccion() -> None:
    assert revision_head(Destino.INSTALACION) == "ins_0007_prod_receta"


def test_subir_crea_la_tabla_con_las_columnas_del_plan(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION, REVISION)
    assert TABLA in _tablas(ruta)
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    assert [(f[1], f[2]) for f in filas] == [c[:2] for c in COLUMNAS]
    # la clave primaria no lleva NOT NULL explícito: SQLite la informa nula en `table_info`
    assert [not f[3] for f in filas if f[1] != "id"] == [c[2] for c in COLUMNAS if c[0] != "id"]
    assert [f[1] for f in filas if f[5]] == ["id"]


def test_un_envio_de_una_carpeta_va_una_sola_vez(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(FILA)
        conexion.execute(FILA.replace("'obra.db'", "'otra.db'"))  # otra carpeta: el mismo número
        conexion.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(FILA)


def test_la_tabla_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.INSTALACION)
    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        METADATA_INDICE_APROBACION.create_all(motor)
    finally:
        motor.dispose()
    assert _instantanea_de_la_tabla(migrada) == _instantanea_de_la_tabla(creada)


def test_bajar_a_la_anterior_quita_la_tabla_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    deshacer_revisiones(ruta, Destino.INSTALACION, ANTERIOR)
    assert TABLA not in _tablas(ruta)
    assert "mp_eleccion" in _tablas(ruta)
    assert leer_estado(ruta).revision == ANTERIOR
    aplicar_revisiones(ruta, Destino.INSTALACION)
    assert TABLA in _tablas(ruta)


def test_una_base_que_ya_trae_la_tabla_se_adopta_sin_recrearla(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION, ANTERIOR)
    motor = create_engine(_url(ruta))
    try:
        METADATA_INDICE_APROBACION.create_all(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(FILA)
        conexion.commit()

    aplicar_revisiones(ruta, Destino.INSTALACION)

    assert leer_estado(ruta).revision == "ins_0007_prod_receta"
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute(f"SELECT caso, version FROM {TABLA}").fetchall() == [
            ("obra.db", "VIV-001")
        ]
