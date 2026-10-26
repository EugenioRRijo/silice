"""`caso_0013_mp_mercado`: las tablas del estudio de mercado (MP-5, Tarea 13).

`mp_observacion` (los precios vistos en el mercado, para lo que se compra y lo que se cobra) y
`mp_precio_objetivo` (el precio de venta objetivo de una partida; vale el último). Tablas aditivas
de `aplicacion/tablas_mercado.py`; una base que ya las trae se adopta sin recrearlas (`_faltan`).
La revisión anterior se lee de la migración misma (`down_revision`): el orquestador la ajusta al
integrar las revisiones del plan en su orden, y estas pruebas la siguen sin cambiar.

Oráculos: el DDL esperado (nombre, tipo, nulo) está escrito a mano.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from aplicacion.tablas_mercado import crear_esquema_mercado
from migraciones.comun import instantanea_esquema
from operacion.base_datos import (
    CARPETA_MIGRACIONES,
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    leer_estado,
)

REVISION = "caso_0013_mp_mercado"
TABLAS = ("mp_observacion", "mp_precio_objetivo")
#: (nombre, tipo SQL declarado, admite nulo), en orden.
COLUMNAS = {
    "mp_observacion": [
        ("id", "INTEGER", False),
        ("lado", "VARCHAR(10)", False),
        ("codigo", "VARCHAR(40)", False),
        ("fuente_tipo", "VARCHAR(20)", False),
        ("fuente", "VARCHAR(200)", False),
        ("fecha", "DATE", False),
        ("moneda", "VARCHAR(10)", False),
        ("precio", "VARCHAR(40)", False),
        ("nota", "VARCHAR(500)", False),
        ("responsable", "VARCHAR(200)", False),
        ("fecha_hora", "DATETIME", False),
        ("anulada_por", "INTEGER", True),
    ],
    "mp_precio_objetivo": [
        ("id", "INTEGER", False),
        ("codigo_partida", "VARCHAR(40)", False),
        ("precio", "VARCHAR(40)", False),
        ("moneda", "VARCHAR(10)", False),
        ("observaciones", "VARCHAR(400)", False),
        ("responsable", "VARCHAR(200)", False),
        ("fecha_hora", "DATETIME", False),
    ],
}


def _anterior() -> str:
    archivo = CARPETA_MIGRACIONES / "caso" / "versions" / f"{REVISION}.py"
    especificacion = importlib.util.spec_from_file_location(REVISION, archivo)
    assert especificacion is not None and especificacion.loader is not None
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo.down_revision


ANTERIOR = _anterior()


def _url(ruta: Path) -> str:
    return f"sqlite:///{ruta.as_posix()}"


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {f[0] for f in filas} - {"alembic_version"}


def _instantanea_de_las_tablas(ruta: Path) -> dict:
    motor = create_engine(_url(ruta))
    try:
        with motor.connect() as conexion:
            todo = instantanea_esquema(conexion)
    finally:
        motor.dispose()
    return {tabla: todo[tabla] for tabla in TABLAS}


def test_la_revision_cuelga_de_una_revision_del_caso() -> None:
    assert ANTERIOR.startswith("caso_")


@pytest.mark.parametrize("tabla", TABLAS)
def test_subir_crea_las_tablas_con_las_columnas_del_plan(tmp_path: Path, tabla: str) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute(f"PRAGMA table_info({tabla})").fetchall()
    columnas = COLUMNAS[tabla]
    assert [(f[1], f[2]) for f in filas] == [c[:2] for c in columnas]
    # la clave primaria no lleva NOT NULL explícito: SQLite la informa nula en `table_info`
    assert [not f[3] for f in filas if f[1] != "id"] == [c[2] for c in columnas if c[0] != "id"]
    assert [f[1] for f in filas if f[5]] == ["id"]


def test_las_tablas_migradas_son_las_del_modelo(tmp_path: Path) -> None:
    migrada = tmp_path / "migrada.db"
    aplicar_revisiones(migrada, Destino.CASO, REVISION)
    creada = tmp_path / "creada.db"
    motor = create_engine(_url(creada))
    try:
        crear_esquema_mercado(motor)
    finally:
        motor.dispose()
    assert _instantanea_de_las_tablas(migrada) == _instantanea_de_las_tablas(creada)


def test_bajar_a_la_anterior_quita_las_tablas_y_se_puede_volver_a_subir(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    deshacer_revisiones(ruta, Destino.CASO, ANTERIOR)
    assert not set(TABLAS) & _tablas(ruta)
    assert "mp_carpeta" in _tablas(ruta)
    assert leer_estado(ruta).revision == ANTERIOR
    aplicar_revisiones(ruta, Destino.CASO, REVISION)
    assert set(TABLAS) <= _tablas(ruta)


def test_una_base_que_ya_trae_las_tablas_se_adopta_sin_recrearlas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    motor = create_engine(_url(ruta))
    try:
        crear_esquema_mercado(motor)
    finally:
        motor.dispose()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO mp_observacion (id, lado, codigo, fuente_tipo, fuente, fecha, moneda, "
            "precio, nota, responsable, fecha_hora) VALUES (1, 'compra', 'MAT-001', 'proveedor', "
            "'Ferretería Demo', '2026-10-25', 'Bs', '520.00', '', 'ana', '2026-10-25 09:30:00')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    assert leer_estado(ruta).revision == REVISION
    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT id, codigo, precio FROM mp_observacion").fetchall() == [
            (1, "MAT-001", "520.00")
        ]


def test_la_base_anterior_con_datos_conserva_sus_listas(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    aplicar_revisiones(ruta, Destino.CASO, ANTERIOR)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "INSERT INTO lista_precios (id, nombre, moneda, fecha_vigencia, origen) "
            "VALUES (1, 'Base', 'Bs', '2026-07-01', '')"
        )
        conexion.commit()

    aplicar_revisiones(ruta, Destino.CASO, REVISION)

    with closing(sqlite3.connect(ruta)) as conexion:
        assert conexion.execute("SELECT nombre, moneda FROM lista_precios").fetchall() == [
            ("Base", "Bs")
        ]
        assert conexion.execute("SELECT COUNT(*) FROM mp_observacion").fetchone() == (0,)
        assert conexion.execute("SELECT COUNT(*) FROM mp_precio_objetivo").fetchone() == (0,)
