"""`ins_0013_solicitud_cuenta`: la tabla de solicitudes y `usuario.correo` (C9a, 2026-11-26).

Oráculos a mano: las columnas de `solicitud_cuenta` son las de la tabla de la especificación
(`2026-11-26-registro-con-codigo` §3), en su orden; `correo` va al final de `usuario`; las cuentas
anteriores quedan con el correo vacío y conservan todo lo demás; el login de una solicitud es único.
Bajar quita la tabla y la columna sin tocar las cuentas. FICTICIO.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from operacion.base_datos import (
    Destino,
    aplicar_revisiones,
    deshacer_revisiones,
    revision_head,
)

REVISION = "ins_0013_solicitud_cuenta"
ANTERIOR = "ins_0012_conteo_anulado"
CABEZA = "ins_0016_solicitud_resuelta_por"  # la cabeza (G4 #5)
TABLA = "solicitud_cuenta"
COLUMNAS = [
    "id", "login", "nombre", "correo", "huella_clave", "creada", "estado", "papel",
    "huella_codigo", "vence", "resuelta_por", "resuelta_por_id",
]
ANTES_USUARIO = [
    "id", "login", "nombre", "huella_clave", "roles", "activo", "debe_cambiar_clave",
    "restablecida_por_admin", "creado", "creado_por",
]
CUENTA = (
    "INSERT INTO usuario (login, nombre, huella_clave, roles, activo, debe_cambiar_clave, "
    "restablecida_por_admin, creado, creado_por) VALUES ('ana', 'Ana', 'h', 'arma', 1, 0, 0, "
    "'2026-11-20 08:00:00', 'admin')"
)
SOLICITUD = (
    f"INSERT INTO {TABLA} (login, nombre, correo, huella_clave, creada, estado, resuelta_por) "
    "VALUES ('lucia', 'Lucía', 'lucia@ejemplo.com', 'h', '2026-11-26 08:00:00', 'pendiente', '')"
)


def _columnas(conexion: sqlite3.Connection, tabla: str) -> list[str]:
    return [f[1] for f in conexion.execute(f"PRAGMA table_info({tabla})")]


def _tablas(conexion: sqlite3.Connection) -> set[str]:
    return {n for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_es_la_cabeza_de_la_instalacion() -> None:
    assert revision_head(Destino.INSTALACION) == CABEZA


def test_crea_la_tabla_y_el_correo_de_las_cuentas_de_hoy_queda_vacio(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion, "usuario") == ANTES_USUARIO
        conexion.execute(CUENTA)
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion, "usuario") == [*ANTES_USUARIO, "correo"]
        assert conexion.execute("SELECT login, roles, correo FROM usuario").fetchall() == [
            ("ana", "arma", "")
        ]
        assert _columnas(conexion, TABLA) == COLUMNAS
        nulas = {f[1] for f in conexion.execute(f"PRAGMA table_info({TABLA})") if not f[3]}
        assert nulas == {"papel", "huella_codigo", "vence", "resuelta_por_id"}


def test_el_login_de_una_solicitud_es_unico(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(SOLICITUD)
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conexion.execute(SOLICITUD)


def test_bajar_quita_la_tabla_y_la_columna_y_conserva_las_cuentas(tmp_path: Path) -> None:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(CUENTA)
        conexion.execute(SOLICITUD)
        conexion.commit()
    deshacer_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert TABLA not in _tablas(conexion)
        assert _columnas(conexion, "usuario") == ANTES_USUARIO
        assert conexion.execute("SELECT login, roles FROM usuario").fetchall() == [("ana", "arma")]
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion, TABLA) == COLUMNAS


def test_una_base_que_ya_las_trae_se_adopta(tmp_path: Path) -> None:
    """Hecha con `create_all` (la tabla y la columna ya están): la migración no las duplica."""
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute("ALTER TABLE usuario ADD COLUMN correo VARCHAR(254) DEFAULT ''")
        conexion.execute(
            f"CREATE TABLE {TABLA} (id INTEGER PRIMARY KEY, login VARCHAR(60) NOT NULL UNIQUE, "
            "nombre VARCHAR(120) NOT NULL, correo VARCHAR(254) NOT NULL, huella_clave "
            "VARCHAR(200) NOT NULL, creada DATETIME NOT NULL, estado VARCHAR(12) NOT NULL, papel "
            "VARCHAR(20), huella_codigo VARCHAR(64), vence DATETIME, resuelta_por VARCHAR(120) "
            "NOT NULL)"
        )
        conexion.execute(SOLICITUD)
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion, "usuario").count("correo") == 1
        assert conexion.execute(f"SELECT login FROM {TABLA}").fetchall() == [("lucia",)]
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (CABEZA,)
        ]
