"""Barre los umbrales viales supuestos en ±50 % sobre el caso vial ficticio e imprime Markdown.

No calibra ningún umbral: solo mide cuántos hallazgos VR cambian al escalar cada constante marcada
como `SUPUESTO_DECLARADO` en `adapters/vial/constantes.py`. Usa la vía ficticia de
`data/samples/vial/via_ficticia.csv` con perturbaciones sintéticas acotadas.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from adapters.vial.constantes import PARTIDAS_VIALES  # noqa: E402
from adapters.vial.derivacion import derivar_tramos  # noqa: E402
from adapters.vial.modelo import Tramo  # noqa: E402
from adapters.vial.reglas import auditar_vial  # noqa: E402
from adapters.vial.tabular import leer_tramos  # noqa: E402
from aplicacion.sensibilidad_umbrales import Fila, barrido, umbrales_supuestos  # noqa: E402
from core.contracts import ItemComputo  # noqa: E402
from core.contracts.apu import ComposicionAPU, ResultadoAPU  # noqa: E402
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto  # noqa: E402
from core.verification.texto import formatear_decimal  # noqa: E402

MUESTRA_VIAL = RAIZ / "data" / "samples" / "vial" / "via_ficticia.csv"


def _presupuesto_desde_items(items: Sequence[ItemComputo]) -> Presupuesto:
    cero = Decimal(0)
    uno = Decimal(1)
    partidas = tuple(
        PartidaPresupuestada(
            item,
            ComposicionAPU(item.codigo_partida, item.descripcion, item.unidad, uno),
            ResultadoAPU(cero, cero, cero, cero, cero, uno),
        )
        for item in items
    )
    return Presupuesto("VIAL-SENSIBILIDAD", date(2026, 11, 23), "USD", partidas)


def caso_vial_ficticio() -> tuple[list[Tramo], Presupuesto]:
    """Carga `via_ficticia.csv` y arma un presupuesto con desvíos ficticios cerca de los límites."""
    tramos = leer_tramos(MUESTRA_VIAL)
    cod_carpeta = PARTIDAS_VIALES["carpeta_mezcla"][0]
    cod_transporte = PARTIDAS_VIALES["transporte_mezcla"][0]
    cod_pintura = PARTIDAS_VIALES["pintura_demarcacion"][0]

    ajustados: list[ItemComputo] = []
    for item in derivar_tramos(tramos):
        if item.origen_id == "tramo:T1:capa:3" and item.codigo_partida in {
            cod_carpeta,
            cod_transporte,
        }:
            item = replace(item, cantidad=item.cantidad * Decimal("1.004"))
        elif item.origen_id == "tramo:T2:capa:4" and item.codigo_partida in {
            cod_carpeta,
            cod_transporte,
        }:
            item = replace(item, cantidad=item.cantidad * Decimal("1.006"))
        elif item.origen_id == "tramo:T1:demarcacion:1" and item.codigo_partida == cod_pintura:
            espec = {k: v for k, v in item.especificaciones.items() if k != "_ancho_linea_cm"}
            item = replace(item, especificaciones=espec)
        ajustados.append(item)
    return tramos, _presupuesto_desde_items(ajustados)


def _coma(valor: Decimal, decimales: int = 2) -> str:
    return formatear_decimal(valor, decimales).replace(".", ",")


def formatear_tabla(filas: Sequence[Fila]) -> str:
    """Tabla Markdown de resultados con coma decimal."""
    lineas = [
        "| Umbral | Factor | Base (VR) | Ahora (VR) | Cambian |",
        "|---|---:|---:|---:|---:|",
    ]
    for fila in filas:
        lineas.append(
            f"| {fila.umbral} | {_coma(fila.factor)} | {fila.base} | {fila.ahora} | "
            f"{fila.cambian} |"
        )
    return "\n".join(lineas)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--umbral",
        action="append",
        default=None,
        help="umbral concreto a barrer (repetible; por omisión, todos los supuestos declarados)",
    )
    args = analizador.parse_args(argv)
    tramos, presupuesto = caso_vial_ficticio()
    umbrales = args.umbral if args.umbral is not None else umbrales_supuestos()
    filas = barrido(lambda: auditar_vial(tramos, presupuesto), umbrales)
    print(formatear_tabla(filas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
