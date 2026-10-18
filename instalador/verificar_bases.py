"""Compara las bases migradas por el programa instalado con la ficha de su versión (RF-96 a,
RF-97 e; spec S5 §11.2 paso 9).

    uv run python instalador/verificar_bases.py --casos <carpeta> \\
        --par 0.5.0:demo.db=v050_demo.db --par 1.0.0:demo.db=v100_demo.db

Cada `--par` es `VERSION:BASE=ARCHIVO`: el archivo de la carpeta de casos y la base de
`tests/fixtures/bases/` de la que salió. Debe estar en `head` y dar las filas por tabla, el total
literal y la huella del informe de su ficha.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion.base_datos import Destino, leer_estado, revision_head  # noqa: E402
from tests.fixtures import bases_prueba as bp  # noqa: E402


@dataclass(frozen=True, slots=True)
class Par:
    version: str
    base: str
    archivo: str


def leer_par(texto: str) -> Par:
    try:
        version, resto = texto.split(":", 1)
        base, archivo = resto.split("=", 1)
    except ValueError:
        raise ValueError(f"«{texto}» no tiene la forma VERSION:BASE=ARCHIVO") from None
    return Par(version, base, archivo)


def verificar(casos: Path, pares: Sequence[Par]) -> list[str]:
    problemas: list[str] = []
    for par in pares:
        ruta = casos / par.archivo
        if not ruta.is_file():
            problemas.append(f"{par.archivo}: no existe en {casos}")
            continue
        estado = leer_estado(ruta)
        head = revision_head(Destino.CASO)
        if estado.revision != head:
            problemas.append(f"{par.archivo}: está en {estado.revision}, no en head ({head})")
        with closing(sqlite3.connect(ruta)) as conexion:
            integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
        if integridad != "ok":
            problemas.append(f"{par.archivo}: integrity_check dice {integridad}")
        esperado = bp.ficha(par.version)["bases"][par.base]
        problemas.extend(f"{par.archivo}: {d}" for d in bp.diferencias_con_ficha(ruta, esperado))
    return problemas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--casos", type=Path, required=True)
    analizador.add_argument("--par", action="append", type=leer_par, required=True)
    argumentos = analizador.parse_args(argv)
    problemas = verificar(argumentos.casos, argumentos.par)
    print(json.dumps({"problemas": problemas}, ensure_ascii=False, indent=2))
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
