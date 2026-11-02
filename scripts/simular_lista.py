"""Generador determinista de listas de precios para pruebas.

Herramienta de prueba, no fuente de mercado (UC-07 es I6.3). Toma la lista vigente del catálogo
y emite variaciones reproducibles aplicando ajustes aleatorios pero deterministas según una semilla.

Uso:
    uv run python scripts/simular_lista.py --salida lista.csv --semilla 42
    uv run python scripts/simular_lista.py --salida lista.csv --semilla 42 --variacion-max 10
    uv run python scripts/simular_lista.py --salida lista.csv --semilla 42 \\
        --insumos "Cemento Portland,Arena"
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

# Ejecutado como `python scripts/simular_lista.py`, sys.path[0] es scripts/, no el raíz del repo.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from aplicacion.simulador import PASO_DE_PRESENTACION, simular  # noqa: E402
from core.catalog import Catalogo, abrir_sesion, crear_motor  # noqa: E402
from scripts.seed import RUTA_POR_DEFECTO  # noqa: E402

# La logica vive en `aplicacion/simulador.py` (RM-1); aqui se reexporta para el CLI y sus pruebas.
__all__ = ["PASO_DE_PRESENTACION", "main", "simular"]


def main(argv: Sequence[str] | None = None) -> int:
    """Lee la lista vigente del catálogo y exporta variaciones a CSV."""
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", required=True, help="ruta del archivo CSV de salida")
    analizador.add_argument(
        "--semilla", type=int, required=True, help="semilla para reproducibilidad"
    )
    analizador.add_argument(
        "--variacion-max",
        type=Decimal,
        default=Decimal("5"),
        help="porcentaje máximo de variación (por defecto 5)",
    )
    analizador.add_argument(
        "--insumos",
        default=None,
        help="nombres de insumos separados por coma; None para todos",
    )
    analizador.add_argument(
        "--base",
        default=RUTA_POR_DEFECTO,
        help=f"ruta de la base de datos SQLite (por defecto {RUTA_POR_DEFECTO})",
    )

    argumentos = analizador.parse_args(argv)

    solo = set(i.strip() for i in argumentos.insumos.split(",")) if argumentos.insumos else None

    ruta_db = Path(argumentos.base)
    motor = crear_motor(f"sqlite:///{ruta_db.as_posix()}")

    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            lista = catalogo.lista_vigente()

            precios_dict = {}
            for precio_insumo in lista.precios:
                insumo = precio_insumo.insumo
                precios_dict[insumo.descripcion] = (
                    insumo.tipo.value,
                    insumo.unidad,
                    precio_insumo.precio,
                )

            filas = simular(precios_dict, argumentos.variacion_max, argumentos.semilla, solo)

            ruta_salida = Path(argumentos.salida)
            with ruta_salida.open("w", newline="", encoding="utf-8") as f:
                escritor = csv.writer(f)
                escritor.writerow(["tipo", "insumo", "unidad", "precio"])
                for tipo, insumo, unidad, precio in filas:
                    escritor.writerow([tipo, insumo, unidad, str(precio)])

            print(f"Lista simulada exportada a {ruta_salida} ({len(filas)} insumos)")
            return 0

    finally:
        motor.dispose()


if __name__ == "__main__":
    sys.exit(main())
