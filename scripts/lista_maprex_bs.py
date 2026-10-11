# scripts/lista_maprex_bs.py
"""Lista MaPreX julio 2026 en Bs (spec S1 §6.2): referencia de R11.

Copia como texto la columna `precio_bs` de los cuatro `referencia_*.csv` (111 filas verificadas a
mano en M0.2) con su fecha y su Ref; no reconstruye bolivares desde `precio_usd` (redondeado a 4
decimales). Mismo orden y deduplicacion que `scripts/lista_maprex_usd.py`. Columnas: las de UC‑02
mas las opcionales de UC‑17 (`fecha`, `fuente`, `referencia`).

Uso: `uv run python scripts/lista_maprex_bs.py`
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.lista_maprex_usd import ARCHIVOS_ORIGEN, CARPETA  # noqa: E402

RUTA_SALIDA = CARPETA / "lista_maprex_bs.csv"
COLUMNAS_SALIDA = ("tipo", "insumo", "unidad", "precio", "fecha", "fuente", "referencia")
TASA_MAPREX = Decimal("633.3644")
FECHA_TASA_MAPREX = date(2026, 7, 1)
FUENTE_TASA_MAPREX = (
    "MaPreX v26.0.0.1, mano_de_obra.pdf: «01JUL @ 633,3644 BS/$» "
    "(data/precios/maprex_2026-07/README.md)"
)


def filas_canonicas() -> list[dict[str, str]]:
    vistos: dict[tuple[str, str, str], dict[str, str]] = {}
    for ruta in ARCHIVOS_ORIGEN:
        with ruta.open(newline="", encoding="utf-8") as archivo:
            for fila in csv.DictReader(archivo):
                clave = (fila["tipo"], fila["insumo"], fila["unidad"])
                if clave in vistos or not fila["precio_bs"].strip():
                    continue
                vistos[clave] = {
                    "tipo": fila["tipo"],
                    "insumo": fila["insumo"],
                    "unidad": fila["unidad"],
                    "precio": fila["precio_bs"].strip(),
                    "fecha": fila["fecha_vigencia"].strip(),
                    "fuente": f"{fila['archivo']} Ref {fila['ref_maprex']}",
                    "referencia": fila["ref_maprex"].strip(),
                }
    return [vistos[c] for c in sorted(vistos)]


def main() -> int:
    filas = filas_canonicas()
    with RUTA_SALIDA.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_SALIDA)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"{RUTA_SALIDA} generado con {len(filas)} filas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
