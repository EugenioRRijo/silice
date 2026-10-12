"""Genera las bases de prueba de una versión y su ficha (RV-3, PRU-H15; spec S5 §2 y §12).

Se corre con el código DE LA ETIQUETA, nunca con el de la rama: la etiqueta se extrae con
`git archive` en una carpeta aparte, este script se copia a su `scripts/` y se corre allí
(procedimiento en docs/manual_tecnico.md §10.5). La ficha (total literal, huella del informe y filas
por tabla de cada base) queda escrita con ese código: las pruebas de adopción comparan contra ella,
nunca contra un recálculo con el código nuevo.

Cuatro bases (la cuarta, desde la 0.6.0), cada una en su archivo (casos construidos, NORMAS.md §1):

- `demo.db`: línea base de la clínica, la demostración y `DEMO-001` (`scripts.seed_demo`);
- `of001.db`: la oficina OF-001 con su espacio `esp_*` y la versión `001`
  (`tests.fixtures.hoja_en_base.plantilla_of001`);
- `ti001.db`: TI-001 con su versión `001` y su plan (`plantilla_ti001`);
- `s1.db` (desde la 0.6.0): el caso S1, la clínica convertida a Bs, la lista de empresa de la
  memoria y el estudio de reajuste guardado (`tests.fixtures.caso_s1.plantilla_s1`).

Desde la 0.6.0 cada base nace por `operacion.base_datos.preparar_base` (en `head`); en la 0.5.0 ese
módulo no existe y la crea `create_all`, como la creaba la 0.5.0.

Uso, dentro del árbol de la etiqueta:
    uv run python scripts/generar_base_prueba.py --salida <repo>/tests/fixtures/bases/v0_5_0 \
        --version 0.5.0 --etiqueta v0.5.0 --commit <sha de la etiqueta>
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import sys
from collections.abc import Callable, Sequence
from contextlib import closing
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import select  # noqa: E402

from core import models  # noqa: E402
from core.budget import cargar_elaboracion  # noqa: E402
from core.catalog import Catalogo, abrir_sesion, crear_motor  # noqa: E402
from scripts import seed_demo  # noqa: E402
from tests.fixtures.caso_s1 import plantilla_s1  # noqa: E402
from tests.fixtures.hoja_en_base import plantilla_of001, plantilla_ti001  # noqa: E402

NOMBRE_FICHA = "ficha.json"
TABLA_VERSION = "alembic_version"


def _demo(ruta: Path) -> None:
    if seed_demo.main(["--db", str(ruta)]) != 0:
        raise RuntimeError(f"scripts.seed_demo no pudo sembrar {ruta}")


CONSTRUCTORES: dict[str, Callable[[Path], object]] = {
    "demo.db": _demo,
    "of001.db": plantilla_of001,
    "ti001.db": plantilla_ti001,
    "s1.db": plantilla_s1,
}


def _solo_lectura(base: Path) -> sqlite3.Connection:
    return sqlite3.connect(base.resolve().as_uri() + "?mode=ro", uri=True)


def filas_por_tabla(base: Path) -> dict[str, int]:
    """Filas de cada tabla de la base (incluida `alembic_version` si la tiene)."""
    with closing(_solo_lectura(base)) as conexion:
        tablas = [
            nombre
            for (nombre,) in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            tabla: conexion.execute(f'SELECT count(*) FROM "{tabla}"').fetchone()[0]
            for tabla in tablas
        }


def revision_alembic(base: Path) -> str | None:
    with closing(_solo_lectura(base)) as conexion:
        existe = conexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLA_VERSION,)
        ).fetchone()
        if existe is None:
            return None
        fila = conexion.execute(f"SELECT version_num FROM {TABLA_VERSION}").fetchone()
    return None if fila is None else str(fila[0])


def presupuestos(base: Path) -> list[dict[str, str]]:
    """Cada versión guardada, recargada con `cargar_elaboracion`: total literal y huella SHA-256 del
    informe en Markdown (el mismo texto que juzga RNF-04)."""
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            filas = sesion.execute(
                select(models.Proyecto.nombre, models.Presupuesto.codigo)
                .where(models.Presupuesto.proyecto_id == models.Proyecto.id)
                .order_by(models.Presupuesto.id)
            ).all()
            resultado = []
            for proyecto, codigo in filas:
                elaboracion = cargar_elaboracion(sesion, proyecto, codigo, Catalogo(sesion))
                informe = elaboracion.informe.a_markdown().encode("utf-8")
                resultado.append(
                    {
                        "proyecto": proyecto,
                        "codigo": codigo,
                        "total": str(elaboracion.presupuesto.total),
                        "huella_informe": hashlib.sha256(informe).hexdigest(),
                    }
                )
            return resultado
    finally:
        motor.dispose()


def ficha_de(base: Path) -> dict[str, Any]:
    """La ficha de una base, con el código que esté corriendo."""
    return {
        "revision_alembic": revision_alembic(base),
        "sha256_base": hashlib.sha256(base.read_bytes()).hexdigest(),
        "filas_por_tabla": filas_por_tabla(base),
        "presupuestos": presupuestos(base),
    }


def _preparar_si_existe(ruta: Path) -> None:
    """Desde la 0.6.0 la base nace en `head` por `preparar_base`; en la 0.5.0 no existe."""
    if importlib.util.find_spec("operacion") is not None:
        from operacion.base_datos import preparar_base

        preparar_base(ruta)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", type=Path, required=True)
    analizador.add_argument("--version", required=True, help="p. ej. 0.5.0")
    analizador.add_argument("--etiqueta", required=True, help="p. ej. v0.5.0")
    analizador.add_argument("--commit", required=True, help="sha del commit de la etiqueta")
    argumentos = analizador.parse_args(argv)
    salida: Path = argumentos.salida
    ocupados = [n for n in (*CONSTRUCTORES, NOMBRE_FICHA) if (salida / n).exists()]
    if ocupados:
        print(
            f"{salida} ya tiene {ocupados}: la base de prueba de una versión se genera una sola "
            "vez, en su compuerta (RV-3).",
            file=sys.stderr,
        )
        return 1
    salida.mkdir(parents=True, exist_ok=True)
    bases: dict[str, Any] = {}
    for nombre, construir in CONSTRUCTORES.items():
        ruta = salida / nombre
        _preparar_si_existe(ruta)
        construir(ruta)
        bases[nombre] = ficha_de(ruta)
    ficha = {
        "version": argumentos.version,
        "etiqueta": argumentos.etiqueta,
        "commit": argumentos.commit,
        "bases": bases,
    }
    (salida / NOMBRE_FICHA).write_text(
        json.dumps(ficha, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Bases de prueba y ficha de {argumentos.etiqueta} en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
