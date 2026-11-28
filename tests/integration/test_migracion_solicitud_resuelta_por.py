"""`ins_0016_solicitud_resuelta_por`: `solicitud_cuenta.resuelta_por_id` (G4 #5, 2026-11-27).

Oráculos a mano: `resuelta_por_id` va al final de `solicitud_cuenta`, admite nulo y tiene clave
foránea a `usuario.id` (`fk_solicitud_cuenta_resuelta_por_id`). Las solicitudes de `ins_0015`
quedan con `resuelta_por_id` nulo y conservan sus filas y la unicidad de `login`. Bajar quita la
columna y su clave foránea sin tocar las solicitudes ni las cuentas. Una base que ya trae la
columna se adopta. FICTICIO.
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

REVISION = "ins_0016_solicitud_resuelta_por"
ANTERIOR = "ins_0015_notificacion_por_evento"
TABLA = "solicitud_cuenta"
COLUMNAS_0015 = [
    "id",
    "login",
    "nombre",
    "correo",
    "huella_clave",
    "creada",
    "estado",
    "papel",
    "huella_codigo",
    "vence",
    "resuelta_por",
]
CUENTA = (
    "INSERT INTO usuario (login, nombre, huella_clave, roles, activo, debe_cambiar_clave, "
    "restablecida_por_admin, creado, creado_por) VALUES ('admin', 'Admin', 'h', 'administrador', "
    "1, 0, 0, '2026-11-20 08:00:00', 'codigo')"
)
SOLICITUD = (
    f"INSERT INTO {TABLA} (login, nombre, correo, huella_clave, creada, estado, resuelta_por) "
    "VALUES ('lucia', 'Lucía', 'lucia@ejemplo.com', 'h', '2026-11-26 08:00:00', 'pendiente', '')"
)


def _columnas(conexion: sqlite3.Connection, tabla: str) -> list[str]:
    return [f[1] for f in conexion.execute(f"PRAGMA table_info({tabla})")]


def _foraneas(conexion: sqlite3.Connection, tabla: str) -> list[tuple[str, str, str]]:
    """(columna_local, tabla_destino, columna_destino)."""
    return [(f[3], f[2], f[4]) for f in conexion.execute(f"PRAGMA foreign_key_list({tabla})")]


def _base_en_0015_con_solicitud(tmp_path: Path) -> Path:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(CUENTA)
        conexion.execute(SOLICITUD)
        conexion.commit()
    return base


def test_es_la_cabeza_de_la_instalacion() -> None:
    assert revision_head(Destino.INSTALACION) == REVISION


def test_agrega_resuelta_por_id_con_fk_y_conserva_las_solicitudes(tmp_path: Path) -> None:
    base = _base_en_0015_con_solicitud(tmp_path)
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        assert _columnas(conexion, TABLA) == [*COLUMNAS_0015, "resuelta_por_id"]
        assert _foraneas(conexion, TABLA) == [("resuelta_por_id", "usuario", "id")]
        assert conexion.execute(f"SELECT login, resuelta_por_id FROM {TABLA}").fetchall() == [
            ("lucia", None)
        ]
        # FK válida pasa; FK a usuario inexistente falla; login sigue siendo único
        conexion.execute(f"UPDATE {TABLA} SET resuelta_por_id = 1 WHERE login = 'lucia'")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conexion.execute(
                f"INSERT INTO {TABLA} (login, nombre, correo, huella_clave, creada, estado, "
                "resuelta_por, resuelta_por_id) VALUES ('otra', 'Otra', 'o@ejemplo.com', 'h', "
                "'2026-11-26 09:00:00', 'aprobada', 'Admin <admin>', 99)"
            )
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conexion.execute(SOLICITUD)


def test_bajar_quita_resuelta_por_id_y_su_fk_sin_perder_filas(tmp_path: Path) -> None:
    base = _base_en_0015_con_solicitud(tmp_path)
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(f"UPDATE {TABLA} SET resuelta_por_id = 1 WHERE login = 'lucia'")
        conexion.commit()
    deshacer_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion, TABLA) == COLUMNAS_0015
        assert _foraneas(conexion, TABLA) == []
        assert conexion.execute(f"SELECT login FROM {TABLA}").fetchall() == [("lucia",)]
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as conexion:
        assert _columnas(conexion, TABLA) == [*COLUMNAS_0015, "resuelta_por_id"]
        assert _foraneas(conexion, TABLA) == [("resuelta_por_id", "usuario", "id")]


def test_una_base_que_ya_trae_la_columna_se_adopta(tmp_path: Path) -> None:
    base = _base_en_0015_con_solicitud(tmp_path)
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute(
            f"ALTER TABLE {TABLA} ADD COLUMN resuelta_por_id INTEGER REFERENCES usuario(id)"
        )
        conexion.execute(f"UPDATE {TABLA} SET resuelta_por_id = 1 WHERE login = 'lucia'")
        conexion.commit()
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as conexion:
        assert conexion.execute(f"SELECT login, resuelta_por_id FROM {TABLA}").fetchall() == [
            ("lucia", 1)
        ]
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (REVISION,)
        ]
