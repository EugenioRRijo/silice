"""Une los JUnit de los tramos de la CI en uno solo y verifica que no falte ningun tramo.

Cada tramo escribe su `reporte-<os>-<n>.xml`; este script los junta en un unico `testsuites` que
`verificar_omitidas.py` y `meta_silice.py --junit` leen como si la suite hubiera corrido entera.
`--esperados N` falla (salida 2) si llegaron menos de N reportes, porque un tramo perdido nunca es
un OK. `--pesos` escribe ademas la duracion por archivo de prueba (para `dividir_suite.py`).

Uso: `python scripts/unir_junit.py --salida reporte.xml [--esperados N] [--pesos p.json] t1.xml ...`
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.dividir_suite import listar_archivos  # noqa: E402
from scripts.meta_alpha import _testcases  # noqa: E402

SUMADOS = ("tests", "failures", "errors", "skipped")


class TramosFaltantesError(ValueError):
    """Llegaron menos reportes de los esperados."""


def unir(textos: Sequence[str], esperados: int | None = None) -> str:
    """Un `testsuites` con todos los `testcase` de los reportes y los totales sumados."""
    if not textos:
        raise TramosFaltantesError("no hay ningun reporte que unir")
    if esperados is not None and len(textos) < esperados:
        raise TramosFaltantesError(f"llegaron {len(textos)} reportes de {esperados} esperados")
    suite = ET.Element("testsuite", name="pytest")
    totales = dict.fromkeys(SUMADOS, 0)
    tiempo = 0.0
    for texto in textos:
        raiz = ET.fromstring(texto)
        for hijo in [raiz] if raiz.tag == "testsuite" else raiz.findall("testsuite"):
            for clave in SUMADOS:
                totales[clave] += int(hijo.get(clave, 0))
            tiempo += float(hijo.get("time", 0))
        for caso in _testcases(raiz):
            suite.append(caso)
    for clave, valor in totales.items():
        suite.set(clave, str(valor))
    suite.set("time", f"{tiempo:.3f}")
    union = ET.Element("testsuites")
    union.append(suite)
    return ET.tostring(union, encoding="unicode")


def pesos_por_archivo(texto: str, archivos: Sequence[str]) -> dict[str, float]:
    """Segundos de cada archivo de prueba (suma de sus `testcase`), segun el `classname`."""
    modulos = {a.removesuffix(".py").replace("/", "."): a for a in archivos}
    pesos: dict[str, float] = defaultdict(float)
    for caso in _testcases(ET.fromstring(texto)):
        partes = (caso.get("classname") or "").split(".")
        for corte in range(len(partes), 0, -1):
            archivo = modulos.get(".".join(partes[:corte]))
            if archivo:
                pesos[archivo] += float(caso.get("time", 0))
                break
    return {a: round(s, 2) for a, s in sorted(pesos.items())}


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("reportes", nargs="+", type=Path)
    analizador.add_argument("--salida", type=Path, required=True)
    analizador.add_argument("--esperados", type=int, default=None)
    analizador.add_argument("--pesos", type=Path, default=None)
    args = analizador.parse_args(argv)
    try:
        textos = [r.read_text(encoding="utf-8") for r in args.reportes]
        unido = unir(textos, args.esperados)
    except (OSError, ET.ParseError, TramosFaltantesError) as error:
        print(f"unir junit: {error}")
        return 2
    args.salida.write_text(unido, encoding="utf-8")
    casos = sum(1 for _ in _testcases(ET.fromstring(unido)))
    print(f"unir junit: {len(textos)} reportes, {casos} pruebas en {args.salida}")
    if args.pesos:
        pesos = pesos_por_archivo(unido, listar_archivos())
        args.pesos.write_text(json.dumps(pesos, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
