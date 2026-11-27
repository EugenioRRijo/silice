"""`ins_0015_notificacion_por_evento`: la clave del evento y las preferencias (C11b, 2026-11-26).

Oráculos a mano: `clave_evento` va al final de `notificacion` y es única por persona (dos nulas no
chocan: las del front no llevan clave); `preferencia_notificacion` tiene `(usuario_id, categoria)`
como clave primaria y FK a `usuario.id`. Las notificaciones de `ins_0014` quedan con la clave nula
y todo lo demás igual. Bajar quita la tabla, el índice y la columna, y deja el `CHECK` de la
gravedad, la FK y el índice `(usuario_id, creada)` de `ins_0014`. Una base que ya lo trae se
adopta. FICTICIO.
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

REVISION = "ins_0015_notificacion_por_evento"
ANTERIOR = "ins_0014_notificacion"
CABEZA = "ins_0016_solicitud_resuelta_por"  # la cabeza (G4 #5)
COLUMNAS_0014 = [
    "id", "usuario_id", "gravedad", "titulo", "detalle", "enlace_texto", "enlace_ruta", "creada",
    "leida",
]
CUENTA = (
    "INSERT INTO usuario (login, nombre, huella_clave, roles, activo, debe_cambiar_clave, "
    "restablecida_por_admin, creado, creado_por) VALUES ('ana', 'Ana', 'h', 'arma', 1, 0, 0, "
    "'2026-11-20 08:00:00', 'admin')"
)
NOTIFICACION = (
    "INSERT INTO notificacion (usuario_id, gravedad, titulo, detalle, enlace_texto, enlace_ruta, "
    "creada, leida{extra}) VALUES (1, '{gravedad}', '{titulo}', '', '', '', "
    "'2026-11-26 10:00:00', 0{valor})"
)


def _notificacion(titulo: str, *, gravedad: str = "info", clave: str | None = None) -> str:
    if clave is None:
        return NOTIFICACION.format(extra="", gravedad=gravedad, titulo=titulo, valor="")
    return NOTIFICACION.format(
        extra=", clave_evento", gravedad=gravedad, titulo=titulo, valor=f", '{clave}'"
    )


def _columnas(conexion: sqlite3.Connection, tabla: str) -> list[str]:
    return [f[1] for f in conexion.execute(f"PRAGMA table_info({tabla})")]


def _tablas(conexion: sqlite3.Connection) -> set[str]:
    return {n for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _indices(conexion: sqlite3.Connection, tabla: str) -> dict[str, int]:
    """Nombre del índice -> 1 si es único."""
    return {f[1]: f[2] for f in conexion.execute(f"PRAGMA index_list({tabla})")}


def _base_en_0014_con_una_notificacion(tmp_path: Path) -> Path:
    base = tmp_path / "instalacion.db"
    aplicar_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as c:
        c.execute(CUENTA)
        c.execute(_notificacion("Del front"))
        c.commit()
    return base


def test_es_la_cabeza_de_la_instalacion() -> None:
    assert revision_head(Destino.INSTALACION) == CABEZA


def test_agrega_la_clave_al_final_y_las_de_antes_quedan_sin_clave(tmp_path: Path) -> None:
    base = _base_en_0014_con_una_notificacion(tmp_path)
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as c:
        assert _columnas(c, "notificacion") == [*COLUMNAS_0014, "clave_evento"]
        assert c.execute("SELECT titulo, clave_evento FROM notificacion").fetchall() == [
            ("Del front", None)
        ]
        assert _indices(c, "notificacion") == {
            "ux_notificacion_usuario_clave": 1,
            "ix_notificacion_usuario_creada": 0,
        }


def test_la_clave_es_unica_por_persona_y_las_nulas_no_chocan(tmp_path: Path) -> None:
    base = _base_en_0014_con_una_notificacion(tmp_path)
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as c:
        c.execute("PRAGMA foreign_keys = ON")
        c.execute(_notificacion("Otra del front"))
        c.execute(_notificacion("Evento", clave="lista:empresa:1"))
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            c.execute(_notificacion("Repetida", clave="lista:empresa:1"))
        c.execute(
            "INSERT INTO usuario (login, nombre, huella_clave, roles, activo, debe_cambiar_clave, "
            "restablecida_por_admin, creado, creado_por) VALUES ('tomas', 'Tomás', 'h', 'arma', "
            "1, 0, 0, '2026-11-20 08:00:00', 'admin')"
        )
        c.execute(
            "INSERT INTO notificacion (usuario_id, gravedad, titulo, detalle, enlace_texto, "
            "enlace_ruta, creada, leida, clave_evento) VALUES (2, 'info', 'De Tomás', '', '', '', "
            "'2026-11-26 10:00:00', 0, 'lista:empresa:1')"
        )
        c.commit()
        assert c.execute("SELECT COUNT(*) FROM notificacion").fetchone() == (4,)


def test_la_tabla_de_preferencias(tmp_path: Path) -> None:
    base = _base_en_0014_con_una_notificacion(tmp_path)
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as c:
        c.execute("PRAGMA foreign_keys = ON")
        assert _columnas(c, "preferencia_notificacion") == ["usuario_id", "categoria", "activa"]
        clave = [f[1] for f in c.execute("PRAGMA table_info(preferencia_notificacion)") if f[5]]
        assert clave == ["usuario_id", "categoria"]
        c.execute("INSERT INTO preferencia_notificacion VALUES (1, 'compras', 0)")
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            c.execute("INSERT INTO preferencia_notificacion VALUES (1, 'compras', 1)")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            c.execute("INSERT INTO preferencia_notificacion VALUES (99, 'compras', 0)")
        with pytest.raises(sqlite3.IntegrityError, match="NOT NULL"):
            c.execute("INSERT INTO preferencia_notificacion VALUES (1, 'dictamen', NULL)")


def test_bajar_deja_la_tabla_de_ins_0014_con_sus_restricciones(tmp_path: Path) -> None:
    base = _base_en_0014_con_una_notificacion(tmp_path)
    with closing(sqlite3.connect(base)) as c:
        ddl_0014 = c.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'notificacion'"
        ).fetchone()
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as c:
        c.execute(_notificacion("Evento", clave="lista:empresa:1"))
        c.commit()
    deshacer_revisiones(base, Destino.INSTALACION, ANTERIOR)
    with closing(sqlite3.connect(base)) as c:
        c.execute("PRAGMA foreign_keys = ON")
        assert "preferencia_notificacion" not in _tablas(c)
        assert _columnas(c, "notificacion") == COLUMNAS_0014
        assert _indices(c, "notificacion") == {"ix_notificacion_usuario_creada": 0}
        assert c.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'notificacion'"
        ).fetchone() == ddl_0014
        assert c.execute("SELECT titulo FROM notificacion ORDER BY id").fetchall() == [
            ("Del front",),
            ("Evento",),
        ]
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            c.execute(_notificacion("Mala", gravedad="critico"))
        assert c.execute("SELECT login FROM usuario").fetchall() == [("ana",)]


def test_una_base_que_ya_lo_trae_se_adopta(tmp_path: Path) -> None:
    base = _base_en_0014_con_una_notificacion(tmp_path)
    with closing(sqlite3.connect(base)) as c:
        c.execute("ALTER TABLE notificacion ADD COLUMN clave_evento VARCHAR(255)")
        c.execute(
            "CREATE UNIQUE INDEX ux_notificacion_usuario_clave "
            "ON notificacion (usuario_id, clave_evento)"
        )
        c.execute(
            "CREATE TABLE preferencia_notificacion (usuario_id INTEGER NOT NULL, categoria "
            "VARCHAR(40) NOT NULL, activa BOOLEAN NOT NULL, PRIMARY KEY (usuario_id, categoria), "
            "FOREIGN KEY(usuario_id) REFERENCES usuario (id))"
        )
        c.execute("INSERT INTO preferencia_notificacion VALUES (1, 'compras', 0)")
        c.commit()
    aplicar_revisiones(base, Destino.INSTALACION, REVISION)
    with closing(sqlite3.connect(base)) as c:
        assert c.execute("SELECT * FROM preferencia_notificacion").fetchall() == [
            (1, "compras", 0)
        ]
        assert c.execute("SELECT version_num FROM alembic_version").fetchall() == [(REVISION,)]
