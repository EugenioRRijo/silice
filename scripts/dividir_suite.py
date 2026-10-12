"""Reparte los archivos de prueba en tramos balanceados para la CI (un tramo por runner).

Lista `tests/**/test_*.py` y los reparte entre `total` tramos con el algoritmo voraz «mayor
primero»: cada archivo, del mas pesado al mas liviano, va al tramo con menos peso acumulado. El
reparto es determinista (mismo resultado en Linux y Windows) y completo: cada archivo cae en
exactamente un tramo, de modo que la union de los tramos es toda la suite, sin repetidos.

El peso de un archivo es su duracion medida en segundos si `scripts/pesos_suite.json` la trae
(se regenera con `scripts/unir_junit.py --pesos`); los archivos sin medida pesan la media de los
medidos y, sin archivo de pesos, todos pesan su tamano en bytes. Un archivo nuevo entra solo al
reparto: no hay que registrarlo en ninguna parte.

Uso: `python scripts/dividir_suite.py <indice> <total>` imprime los archivos del tramo `indice`
(de 1 a `total`), uno por linea, con `/` como separador.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_PESOS = Path(__file__).resolve().parent / "pesos_suite.json"


def listar_archivos(raiz: Path = RAIZ) -> list[str]:
    """Rutas relativas (con `/`) de los `test_*.py` bajo `tests/`, en orden alfabetico."""
    return sorted(p.relative_to(raiz).as_posix() for p in (raiz / "tests").rglob("test_*.py"))


def cargar_pesos(ruta: Path = RUTA_PESOS) -> dict[str, float]:
    if not ruta.is_file():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {str(k): float(v) for k, v in datos.items() if float(v) > 0}


def pesos_de(archivos: Sequence[str], medidos: Mapping[str, float], raiz: Path) -> dict[str, float]:
    """Peso de cada archivo: segundos medidos; sin medida, la media; sin ninguna, bytes."""
    conocidos = [medidos[a] for a in archivos if a in medidos]
    if not conocidos:
        return {a: float(max((raiz / a).stat().st_size, 1)) for a in archivos}
    media = sum(conocidos) / len(conocidos)
    return {a: medidos.get(a, media) for a in archivos}


def repartir(pesos: Mapping[str, float], total: int) -> list[list[str]]:
    """Voraz «mayor primero»: `total` listas ordenadas; cada archivo en exactamente una."""
    if total < 1:
        raise ValueError("el total de tramos debe ser al menos 1")
    tramos: list[list[str]] = [[] for _ in range(total)]
    sumas = [0.0] * total
    for archivo in sorted(pesos, key=lambda a: (-pesos[a], a)):
        destino = min(range(total), key=lambda i: (sumas[i], i))
        tramos[destino].append(archivo)
        sumas[destino] += pesos[archivo]
    return [sorted(t) for t in tramos]


def tramo(indice: int, total: int, raiz: Path = RAIZ, ruta_pesos: Path = RUTA_PESOS) -> list[str]:
    """Archivos del tramo `indice` (1 a `total`)."""
    if not 1 <= indice <= total:
        raise ValueError(f"el indice {indice} no esta entre 1 y {total}")
    archivos = listar_archivos(raiz)
    return repartir(pesos_de(archivos, cargar_pesos(ruta_pesos), raiz), total)[indice - 1]


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("indice", type=int, help="tramo, de 1 a total")
    analizador.add_argument("total", type=int, help="cantidad de tramos")
    analizador.add_argument("--pesos", type=Path, default=RUTA_PESOS, help="JSON ruta -> segundos")
    args = analizador.parse_args(argv)
    try:
        archivos = tramo(args.indice, args.total, ruta_pesos=args.pesos)
    except ValueError as error:
        print(f"dividir suite: {error}", file=sys.stderr)
        return 2
    sys.stdout.write("\n".join(archivos) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
