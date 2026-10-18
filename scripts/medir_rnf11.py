"""Mide RNF-11: el tiempo de la hoja del proyecto con 500 puntos, en `ui.hoja`, sin Streamlit.

La metrica de la spec del sprint final (§4.3) pide, para un proyecto de 500 puntos, una mediana
de **2 s o menos** desde que se aplica una edicion hasta que se tiene el presupuesto, el informe de
auditoria y el punto de equilibrio, **sin persistir**. Este script produce esa evidencia:

1. genera los 500 puntos con el generador determinista (`scripts/generar_hoja_prueba.py`, semilla
   0) y arma con ellos el borrador de la hoja (`ui.hoja.Borrador`) con su plan secuencial;
2. cada corrida aplica una edicion (escribe a mano la cantidad de un punto, DA-SF-5) y llama a
   `ui.hoja.elaborar_borrador`: valora, ajusta el plan, audita con R1 a R10 y calcula el punto de
   equilibrio y el Estado por fila. No toca ninguna base de datos;
3. se hace **una corrida de calentamiento** (no cuenta) y se miden **cinco**; la cifra es la
   **mediana**.

Uso:
    uv run python scripts/medir_rnf11.py                 # 500 puntos, 5 corridas, umbral 2 s
    uv run python scripts/medir_rnf11.py --puntos 100    # otro tamano
    uv run python scripts/medir_rnf11.py --estricto      # sale con 1 si supera el umbral

**Solo registra.** Sin `--estricto` sale siempre con 0, aunque supere los 2 s: el veredicto de
RNF-11 se toma en el equipo de desarrollo (como RNF-03) y la CI solo anota la cifra en Linux y
Windows, porque una maquina compartida o cargada no debe romper la corrida. La cifra queda en
`scripts/_salida_rnf11.json` (ignorado por git), de donde la lee la meta S9 de
`scripts/meta_sf.py`, y se anota en `docs/plan_pruebas.md` §10.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.generar_hoja_prueba import (  # noqa: E402
    PARAMETROS_PRUEBA,
    composiciones_de_prueba,
    generar_items,
)
from ui import hoja  # noqa: E402

PUNTOS = 500
CORRIDAS = 5
UMBRAL_SEGUNDOS = 2.0
SEMILLA = 0
RUTA_SALIDA = RAIZ / "scripts" / "_salida_rnf11.json"
FECHA_DE_LA_CARGA = date(2026, 10, 5)


@dataclass(frozen=True, slots=True)
class Medicion:
    """Las corridas medidas (sin la de calentamiento), en segundos."""

    corridas: tuple[float, ...]

    @property
    def mediana(self) -> float:
        return mediana(self.corridas)


def mediana(valores: Sequence[float]) -> float:
    """La mediana: el valor del medio, o el promedio de los dos del medio si son pares."""
    orden = sorted(valores)
    medio = len(orden) // 2
    return orden[medio] if len(orden) % 2 else (orden[medio - 1] + orden[medio]) / 2


def medir(
    trabajo: Callable[[int], object],
    corridas: int = CORRIDAS,
    reloj: Callable[[], float] = time.perf_counter,
) -> Medicion:
    """Cronometra `trabajo(i)`: una corrida de calentamiento (`i = 0`, se descarta) y `corridas`
    medidas (`i = 1..corridas`). Cada corrida recibe su numero para aplicar una edicion distinta."""
    tiempos = []
    for i in range(corridas + 1):
        inicio = reloj()
        trabajo(i)
        tiempos.append(reloj() - inicio)
    return Medicion(tuple(tiempos[1:]))


def preparar(puntos: int = PUNTOS) -> tuple[Callable[[int], hoja.ResultadoHoja], hoja.Borrador]:
    """El borrador de `puntos` puntos y el trabajo que se mide: aplicar la edicion `i` y elaborar.

    Mide SIN R17 (tarea 1.7): el borrador no tiene espacio (solo `items_base`), asi que R17 no daria
    ningun hallazgo, y la cifra de RNF-11 sigue comparable con las ya registradas.

    La edicion `i` escribe a mano la cantidad del punto `i` (modulo el total). Devuelve tambien el
    borrador de partida."""
    items = generar_items(puntos, SEMILLA)
    base = hoja.Borrador(
        fecha=FECHA_DE_LA_CARGA,
        items_base=tuple(items),
        composiciones=composiciones_de_prueba(),
        parametros=PARAMETROS_PRUEBA,
    )
    borrador = hoja.con_plan_secuencial(base)
    claves = hoja.claves_de_items(hoja.items_sin_escribir(borrador))

    def trabajo(i: int) -> hoja.ResultadoHoja:
        editado = replace(borrador, cantidades={claves[i % len(claves)]: Decimal(1000 + i)})
        return hoja.elaborar_borrador(editado, codigo="MEDIDA")

    return trabajo, borrador


def _coma(valor: float) -> str:
    return f"{valor:.3f}".replace(".", ",")


def _equipo() -> str:
    return f"{platform.platform()}; {platform.processor() or 'procesador sin nombre'}; " + (
        f"{os.cpu_count()} nucleos; Python {platform.python_version()}"
    )


def main(argv: Sequence[str] | None = None, reloj: Callable[[], float] = time.perf_counter) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--puntos", type=int, default=PUNTOS)
    analizador.add_argument("--corridas", type=int, default=CORRIDAS)
    analizador.add_argument("--umbral", type=float, default=UMBRAL_SEGUNDOS)
    analizador.add_argument("--salida", type=Path, default=RUTA_SALIDA)
    analizador.add_argument(
        "--estricto", action="store_true", help="sale con 1 si la mediana supera el umbral"
    )
    args = analizador.parse_args(argv)

    trabajo, _ = preparar(args.puntos)
    medicion = medir(trabajo, args.corridas, reloj)
    cumple = medicion.mediana <= args.umbral
    registro = {
        "requisito": "RNF-11",
        "puntos": args.puntos,
        "corridas_s": [round(c, 6) for c in medicion.corridas],
        "mediana_s": round(medicion.mediana, 6),
        "mediana_texto": f"{medicion.mediana:.3f}",
        "umbral_s": args.umbral,
        "cumple": cumple,
        "equipo": _equipo(),
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    args.salida.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")

    corridas = ", ".join(_coma(c) for c in medicion.corridas)
    print(
        f"RNF-11, hoja de {args.puntos} puntos: corridas medidas [{corridas}] s tras una de "
        f"calentamiento; mediana {_coma(medicion.mediana)} s (umbral {_coma(args.umbral)} s): "
        + ("cumple." if cumple else "NO cumple.")
    )
    print(f"Equipo: {registro['equipo']}")
    return 1 if args.estricto and not cumple else 0


if __name__ == "__main__":
    raise SystemExit(main())
