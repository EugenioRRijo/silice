"""`ins_0002_produccion`: las tablas de la arenera en la base de la instalacion (RT-S4-1, RNF-20)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

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
from produccion.modelo import METADATA_PRODUCCION

TABLAS_NUEVAS = {"prod_material", "prod_movimiento", "prod_pesaje_sospechoso"}


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


def test_migrar_crea_las_tablas_y_cero_deriva(tmp_path: Path) -> None:
    assert revision_head(Destino.INSTALACION) == "ins_0002_produccion"
    assert METADATA_PRODUCCION in METADATAS_INSTALACION
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.INSTALACION)
    assert TABLAS_NUEVAS <= _tablas(migrada)

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


def test_la_base_de_la_1_0_0_se_respalda_y_migra(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION, "ins_0001_seguridad")
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO usuario (login, nombre, huella_clave, roles, activo, "
            "debe_cambiar_clave, restablecida_por_admin, creado, creado_por) "
            "VALUES ('ana', 'Ana', 'h', 'admin', 1, 0, 0, '2026-10-01 00:00:00', 'sistema')"
        )
        conexion.commit()
    assert leer_estado(ruta).revision == "ins_0001_seguridad"

    resultado = preparar_base(ruta, Destino.INSTALACION)

    assert resultado.revision_origen == "ins_0001_seguridad"
    assert resultado.revision_destino == "ins_0002_produccion"
    assert resultado.juego is not None and resultado.juego.is_dir()
    assert respaldo.listar_juegos(config.carpeta_respaldos())
    assert leer_estado(ruta).revision == "ins_0002_produccion"
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT login, nombre FROM usuario").fetchall() == [("ana", "Ana")]
        for tabla in TABLAS_NUEVAS:
            assert conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone() == (0,)


def test_deshacer_vuelve_a_ins_0001(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    deshacer_revisiones(ruta, Destino.INSTALACION, "-1")
    assert not (TABLAS_NUEVAS & _tablas(ruta))
    assert leer_estado(ruta).revision == "ins_0001_seguridad"
    aplicar_revisiones(ruta, Destino.INSTALACION)  # y vuelve a subir
    assert TABLAS_NUEVAS <= _tablas(ruta)
