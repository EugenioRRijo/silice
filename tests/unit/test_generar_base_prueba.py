"""El generador de las bases de prueba de cada versión y de su ficha (RV-3, PRU-H15)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from scripts import generar_base_prueba as generador


def _base_minima(ruta: Path) -> Path:
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("CREATE TABLE a (id INTEGER PRIMARY KEY)")
        conexion.executemany("INSERT INTO a VALUES (?)", [(1,), (2,)])
        conexion.execute("CREATE TABLE b (x TEXT)")
        conexion.commit()
    return ruta


def test_filas_por_tabla_cuenta_todas_las_tablas(tmp_path: Path) -> None:
    assert generador.filas_por_tabla(_base_minima(tmp_path / "m.db")) == {"a": 2, "b": 0}


def test_la_revision_es_none_sin_alembic_y_la_fila_con_alembic(tmp_path: Path) -> None:
    base = _base_minima(tmp_path / "m.db")
    assert generador.revision_alembic(base) is None
    with closing(sqlite3.connect(base)) as conexion:
        conexion.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        conexion.execute("INSERT INTO alembic_version VALUES ('caso_0001_base_0_5_0')")
        conexion.commit()
    assert generador.revision_alembic(base) == "caso_0001_base_0_5_0"


def test_los_casos_de_la_base_de_prueba() -> None:
    assert list(generador.CONSTRUCTORES) == ["demo.db", "of001.db", "ti001.db", "s1.db"]


def test_se_niega_a_reescribir_una_base_de_prueba(tmp_path: Path, capsys) -> None:
    (tmp_path / "demo.db").write_bytes(b"")
    codigo = generador.main(
        ["--salida", str(tmp_path), "--version", "0.5.0", "--etiqueta", "v0.5.0", "--commit", "x"]
    )
    assert codigo == 1
    assert "se genera una sola vez" in capsys.readouterr().err


@pytest.mark.sin_usuario_por_omision
def test_el_generador_firma_las_versiones_que_llegan_sin_usuario(tmp_path: Path) -> None:
    """Desde la 1.0.0 (S3-2, RF-83) confirmar una versión exige `usuario` y las plantillas de
    `tests/` no lo declaran: en pytest lo pone `tests/conftest.py`; fuera de pytest, en el árbol de
    la etiqueta, nadie lo ponía y `s1.db` no se podía confirmar (`SelladoSinUsuario`)."""
    salida = tmp_path / "v"
    codigo = generador.main(
        ["--salida", str(salida), "--version", "1.0.0", "--etiqueta", "v1.0.0", "--commit", "x"]
    )
    assert codigo == 0
    with closing(sqlite3.connect(salida / "s1.db")) as conexion:
        usuarios = {fila[0] for fila in conexion.execute("SELECT usuario FROM eslabon_version")}
    assert generador.USUARIO_GENERADOR in usuarios
