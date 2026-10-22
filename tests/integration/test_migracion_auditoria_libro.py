"""`ins_0003_auditoria_libro`: el historial de auditorias de «Libro de la empresa» (UC-25, RF-142).

La tabla guarda el resumen y los hallazgos compactos de cada auditoria; nunca el libro ni el PDF
(RNF-28): por eso ninguna columna es binaria. Los totales son texto decimal, nunca `float`.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from fusion.historial_modelo import METADATA_HISTORIAL
from migraciones.comun import instantanea_esquema, metadata_unida
from migraciones.metadatos import METADATAS_INSTALACION
from operacion import config, respaldo
from operacion.base_datos import (
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    leer_estado,
    preparar_base,
    revision_head,
)

TABLA = "auditoria_libro"
#: (nombre, tipo SQL declarado, admite nulo): el DDL literal de la migracion, escrito a mano.
COLUMNAS = [
    ("id", "INTEGER", False),
    ("fecha_hora", "DATETIME", False),
    ("usuario", "VARCHAR(120)", False),
    ("tipo", "VARCHAR(5)", False),
    ("nombre_archivo", "VARCHAR(255)", False),
    ("sha256", "VARCHAR(64)", False),
    ("fecha_libro", "DATE", True),
    ("total_libro", "VARCHAR(40)", True),
    ("total_silice", "VARCHAR(40)", True),
    ("errores", "INTEGER", False),
    ("advertencias", "INTEGER", False),
    ("informativos", "INTEGER", False),
    ("atipicos", "INTEGER", False),
    ("recortado", "BOOLEAN", False),
    ("hallazgos", "TEXT", False),
]


def _url(ruta: Path) -> str:
    return f"sqlite:///{ruta.as_posix()}"


def _instantanea(ruta: Path) -> dict:
    motor = create_engine(_url(ruta))
    try:
        with motor.connect() as conexion:
            return instantanea_esquema(conexion)
    finally:
        motor.dispose()


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {f[0] for f in filas} - {"alembic_version"}


def test_migrar_crea_la_tabla_y_cero_deriva(tmp_path: Path) -> None:
    assert revision_head(Destino.INSTALACION) == "ins_0003_auditoria_libro"
    assert METADATA_HISTORIAL in METADATAS_INSTALACION
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.INSTALACION)
    assert TABLA in _tablas(migrada)

    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        for metadata in METADATAS_INSTALACION:
            metadata.create_all(motor)
    finally:
        motor.dispose()
    assert _instantanea(migrada) == _instantanea(creada)

    motor = create_engine(_url(migrada))
    try:
        with motor.connect() as conexion:
            contexto = MigrationContext.configure(conexion, opts={"compare_type": True})
            assert compare_metadata(contexto, metadata_unida(METADATAS_INSTALACION)) == []
    finally:
        motor.dispose()


def test_las_columnas_son_las_del_ddl_literal(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({TABLA})").fetchall()
    leidas = [(f[1], f[2], not f[3] and not f[5]) for f in filas]
    # `id` es la clave primaria: sin NOT NULL explicito, SQLite la declara nula en `table_info`
    assert [c[:2] for c in leidas] == [c[:2] for c in COLUMNAS]
    assert [c[2] for c in leidas if c[0] != "id"] == [c[2] for c in COLUMNAS if c[0] != "id"]
    assert not any("BLOB" in f[2].upper() for f in filas), "el libro no se guarda (RNF-28)"


def test_el_tipo_solo_admite_libro_o_pdf(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    insertar = (
        f"INSERT INTO {TABLA} (fecha_hora, usuario, tipo, nombre_archivo, sha256, errores, "
        "advertencias, informativos, atipicos, recortado, hallazgos) "
        "VALUES ('2026-10-18 10:00:00', 'ana', ?, 'a.xlsx', ?, 0, 0, 0, 0, 0, '[]')"
    )
    with closing(sqlite3.connect(ruta)) as conexion:
        for tipo in ("libro", "pdf"):
            conexion.execute(insertar, (tipo, "a" * 64))
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(insertar, ("excel", "a" * 64))
        conexion.commit()
        assert conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone() == (2,)


def test_la_base_de_la_1_0_0_se_respalda_y_migra(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION, "ins_0002_produccion")
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO prod_material (codigo, nombre, unidad_venta, existencia_minima, activo) "
            "VALUES ('ARENA', 'Arena', 'm3', '20', 1)"
        )
        conexion.commit()
    assert leer_estado(ruta).revision == "ins_0002_produccion"

    resultado = preparar_base(ruta, Destino.INSTALACION)

    assert resultado.revision_origen == "ins_0002_produccion"
    assert resultado.revision_destino == "ins_0003_auditoria_libro"
    assert resultado.juego is not None and resultado.juego.is_dir()
    assert respaldo.listar_juegos(config.carpeta_respaldos())
    assert leer_estado(ruta).revision == "ins_0003_auditoria_libro"
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT codigo FROM prod_material").fetchall() == [("ARENA",)]
        assert conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone() == (0,)


def test_deshacer_vuelve_a_ins_0002_y_vuelve_a_subir(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    deshacer_revisiones(ruta, Destino.INSTALACION, "-1")
    assert TABLA not in _tablas(ruta)
    assert "prod_material" in _tablas(ruta)
    assert leer_estado(ruta).revision == "ins_0002_produccion"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    assert TABLA in _tablas(ruta)
