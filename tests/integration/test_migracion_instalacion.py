"""La base de la instalación: su revisión `ins_0001_seguridad` y la deriva cero (RNF-20, RF-96)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from migraciones.metadatos import METADATAS_INSTALACION
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, revision_head
from seguridad.modelo import Base

TABLAS = {
    "usuario", "intento_acceso", "sesion", "evento_acceso", "codigo_instalacion", "empresa_propia",
    "clave_empresa", "empresa_registrada", "clave_api",
}


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {f[0] for f in filas} - {"alembic_version"}


def test_la_cabeza_del_destino_instalacion_es_la_revision_de_seguridad() -> None:
    assert revision_head(Destino.INSTALACION) == "ins_0001_seguridad"
    assert METADATAS_INSTALACION == (Base.metadata,)


def test_subir_crea_las_nueve_tablas_y_bajar_las_quita(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    assert _tablas(ruta) == TABLAS
    deshacer_revisiones(ruta, Destino.INSTALACION)
    assert _tablas(ruta) == set()
    aplicar_revisiones(ruta, Destino.INSTALACION)  # y vuelve a subir
    assert _tablas(ruta) == TABLAS


def test_deriva_cero_la_base_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.connect() as conexion:
            contexto = MigrationContext.configure(conexion, opts={"compare_type": True})
            assert compare_metadata(contexto, Base.metadata) == []
    finally:
        motor.dispose()


def test_las_tablas_de_la_instalacion_no_estan_en_los_metadatos_del_caso() -> None:
    from migraciones.metadatos import METADATAS_CASO

    nombres_caso = {t for m in METADATAS_CASO for t in m.tables}
    assert not (TABLAS & nombres_caso)  # DA-S5-7: cuentas y claves nunca viajan con un caso
