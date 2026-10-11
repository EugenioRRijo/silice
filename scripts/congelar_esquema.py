"""Congela el esquema de una base de prueba como revisión base de Alembic (spec S5 §6.1).

Lee `sqlite_master` de una base de prueba (creada con el código de su etiqueta por
`scripts/generar_base_prueba.py`) y escribe la revisión con el DDL literal de cada tabla y de sus
índices, en el orden en que se crearon, como `TablaCongelada`. Se corre UNA vez por revisión base;
el archivo se revisa a mano y queda congelado: nunca se regenera desde los modelos.

Uso:
    uv run python scripts/congelar_esquema.py --base tests/fixtures/bases/v0_5_0/of001.db \
        --revision caso_0001_base_0_5_0 --version 0.5.0 --commit 8610053 \
        --salida migraciones/caso/versions/caso_0001_base_0_5_0.py
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

CABECERA = '''"""Revisión base del caso: esquema EXACTO de Sílice {version} (v{version}, {commit}).

Generada una vez con `scripts/congelar_esquema.py` desde la base de prueba de esa versión
(`tests/fixtures/bases/`), creada con el código de su etiqueta; revisada a mano y CONGELADA: no se
deriva de los modelos (spec S5 §6.1). Idempotente (DA-S5-4): crea las tablas que faltan y verifica
las existentes; una diferencia es `BaseNoAdoptable`.
"""

from alembic import op

from migraciones.comun import TablaCongelada, borrar_tablas, crear_o_verificar

revision = "{revision}"
down_revision = None
branch_labels = None
depends_on = None

'''

PIE = """

def upgrade() -> None:
    crear_o_verificar(op.get_bind(), TABLAS)


def downgrade() -> None:
    borrar_tablas(op.get_bind(), TABLAS)
"""


def leer_esquema(base: Path) -> list[tuple[str, str, tuple[str, ...]]]:
    """`(tabla, ddl, índices)` en orden de creación, sin `alembic_version` ni las internas."""
    uri = base.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conexion:
        filas = conexion.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql IS NOT NULL "
            "AND name NOT LIKE 'sqlite_%' AND tbl_name <> 'alembic_version' ORDER BY rowid"
        ).fetchall()
    indices: dict[str, list[str]] = {}
    for tipo, _nombre, tabla, sql in filas:
        if tipo == "index":
            indices.setdefault(tabla, []).append(sql)
    return [
        (nombre, sql, tuple(indices.get(nombre, ())))
        for tipo, nombre, _tabla, sql in filas
        if tipo == "table"
    ]


def _literal(texto: str) -> str:
    lineas = texto.splitlines(keepends=True) or [""]
    return "(\n" + "".join(f"            {linea!r}\n" for linea in lineas) + "        )"


def renderizar(
    esquema: Sequence[tuple[str, str, tuple[str, ...]]], *, revision: str, version: str, commit: str
) -> str:
    partes = [CABECERA.format(version=version, commit=commit, revision=revision), "TABLAS = (\n"]
    for nombre, ddl, indices in esquema:
        partes.append("    TablaCongelada(\n")
        partes.append(f"        nombre={nombre!r},\n")
        partes.append(f"        ddl={_literal(ddl)},\n")
        partes.append(
            "        indices=(\n"
            + "".join(f"            {i!r},\n" for i in indices)
            + "        ),\n"
        )
        partes.append("    ),\n")
    partes.append(")\n")
    partes.append(PIE)
    return "".join(partes)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--base", type=Path, required=True)
    analizador.add_argument("--revision", required=True)
    analizador.add_argument("--version", required=True)
    analizador.add_argument("--commit", required=True)
    analizador.add_argument("--salida", type=Path, required=True)
    argumentos = analizador.parse_args(argv)
    if argumentos.salida.exists():
        print(f"{argumentos.salida} ya existe: una revisión base está congelada.", file=sys.stderr)
        return 1
    texto = renderizar(
        leer_esquema(argumentos.base),
        revision=argumentos.revision,
        version=argumentos.version,
        commit=argumentos.commit,
    )
    argumentos.salida.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Revisión {argumentos.revision} escrita en {argumentos.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
