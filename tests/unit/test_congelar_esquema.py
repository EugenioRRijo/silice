"""El congelador de la revisión base: DDL literal de SQLite, en orden de creación (spec S5 §6.1)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from scripts import congelar_esquema as congelar


def _base(ruta: Path) -> Path:
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "CREATE TABLE padre (\n\tid INTEGER NOT NULL, \n\tnombre VARCHAR(40), \n"
            "\tPRIMARY KEY (id)\n)"
        )
        conexion.execute("CREATE INDEX ix_padre_nombre ON padre (nombre)")
        conexion.execute("CREATE TABLE hijo (padre_id INTEGER REFERENCES padre (id))")
        conexion.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        conexion.commit()
    return ruta


def test_leer_el_esquema_conserva_orden_ddl_e_indices_y_omite_alembic(tmp_path: Path) -> None:
    esquema = congelar.leer_esquema(_base(tmp_path / "m.db"))
    assert [tabla for tabla, _, _ in esquema] == ["padre", "hijo"]
    assert esquema[0][1].startswith("CREATE TABLE padre (\n\tid INTEGER NOT NULL")
    assert esquema[0][2] == ("CREATE INDEX ix_padre_nombre ON padre (nombre)",)
    assert esquema[1][2] == ()


def test_la_revision_renderizada_devuelve_el_mismo_ddl(tmp_path: Path) -> None:
    esquema = congelar.leer_esquema(_base(tmp_path / "m.db"))
    texto = congelar.renderizar(esquema, revision="prueba_0001", version="9.9.9", commit="abc1234")
    espacio: dict = {}
    exec(compile(texto, "prueba_0001.py", "exec"), espacio)
    assert espacio["revision"] == "prueba_0001" and espacio["down_revision"] is None
    assert [(t.nombre, t.ddl, t.indices) for t in espacio["TABLAS"]] == esquema


def test_no_pisa_una_revision_ya_congelada(tmp_path: Path, capsys) -> None:
    base = _base(tmp_path / "m.db")
    salida = tmp_path / "prueba_0001.py"
    salida.write_text("congelada\n", encoding="utf-8")
    argv = [
        "--base",
        str(base),
        "--revision",
        "prueba_0001",
        "--version",
        "9.9.9",
        "--commit",
        "abc1234",
        "--salida",
        str(salida),
    ]
    assert congelar.main(argv) == 1
    assert salida.read_text(encoding="utf-8") == "congelada\n"
    assert "congelada" in capsys.readouterr().err
