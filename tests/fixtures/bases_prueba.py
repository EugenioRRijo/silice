"""Bases de prueba de cada versión con su ficha (RV-3, PRU-H15; spec S5 §2 y §12).

`tests/fixtures/bases/v<X_Y_Z>/` guarda las bases que generó `scripts/generar_base_prueba.py` con el
código de la etiqueta `vX.Y.Z`, y su `ficha.json`. Las pruebas COPIAN la base (nunca la abren en su
sitio) y comparan con `diferencias_con_ficha`, que recalcula con el código de hoy lo mismo que el
generador escribió con el de la etiqueta.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from scripts.generar_base_prueba import NOMBRE_FICHA, TABLA_VERSION, ficha_de

CARPETA = Path(__file__).resolve().parent / "bases"


def carpeta_version(version: str) -> Path:
    return CARPETA / ("v" + version.replace(".", "_"))


def ficha(version: str) -> dict[str, Any]:
    return json.loads((carpeta_version(version) / NOMBRE_FICHA).read_text(encoding="utf-8"))


def nombres(version: str) -> list[str]:
    return sorted(ficha(version)["bases"])


def copiar_base(version: str, nombre: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(carpeta_version(version) / nombre, destino)
    return destino


def diferencias_con_ficha(ruta: Path, esperado: dict[str, Any]) -> list[str]:
    """Lo que no cuadra entre la base (recargada con el código de hoy) y su ficha: filas de cada
    tabla de la ficha (salvo `alembic_version`), total literal y huella del informe."""
    actual = ficha_de(ruta)
    diferencias = [
        f"{tabla}: {actual['filas_por_tabla'].get(tabla)} filas; la ficha dice {filas}"
        for tabla, filas in sorted(esperado["filas_por_tabla"].items())
        if tabla != TABLA_VERSION and actual["filas_por_tabla"].get(tabla) != filas
    ]
    if actual["presupuestos"] != esperado["presupuestos"]:
        diferencias.append(f"presupuestos: {actual['presupuestos']} != {esperado['presupuestos']}")
    return diferencias


def crear_base_futura(ruta: Path, revision: str = "caso_9999_futura") -> Path:
    """Una base con una revisión que este código no conoce: la de un Sílice más nuevo (§6.4, 3d)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        conexion.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
        conexion.execute("CREATE TABLE partida (id INTEGER PRIMARY KEY)")
        conexion.commit()
    return ruta
