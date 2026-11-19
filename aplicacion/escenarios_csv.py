"""El CSV de la tabla de escenarios (RF-31) como lo abre Excel en español.

Prueba en vivo del 2026-11-18 (frente C, hallazgo 6): el CSV salía con punto decimal y los 28
dígitos del cálculo («4.545454545454545454545454545»). Excel en español separa con punto y coma y
lee la coma decimal y el punto de miles (`aplicacion/computo_csv.py` documenta lo mismo para los
cómputos que entran): el archivo sale así, en UTF-8 con su marca para que las tildes se lean, con
las cifras a los dos decimales de presentación del resto de la aplicación (redondeo de mitad hacia
arriba, NORMAS §2.3). El cálculo no cambia: el exacto sigue en la base y en el núcleo; el CSV es
una presentación, como la tabla de la pantalla.

Decisión (para el acta): dos decimales en vez de los exactos. Un CSV abierto en Excel es lo que
lee la persona; los 28 dígitos no los usa nadie y Excel en español no los leía como número.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping
from decimal import Decimal

from aplicacion.cifras import texto_de_cifra
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal

__all__ = ["COLUMNAS_CSV_ESCENARIOS", "csv_de_escenarios"]

#: (columna de `comparar_escenarios`, encabezado del CSV): los de la tabla de la pantalla.
COLUMNAS_CSV_ESCENARIOS = (
    ("escenario", "Escenario"),
    ("total", "Total"),
    ("variacion", "Variación"),
    ("variacion_pct", "Variación %"),
)
_MARCA_UTF8 = "﻿"


def _cifra(valor: object) -> str:
    """La cifra a dos decimales con coma decimal y punto de miles («1.234,56»)."""
    return texto_de_cifra(Decimal(formatear_decimal(Decimal(valor), DECIMALES_PRESENTACION)))


def csv_de_escenarios(filas: Iterable[Mapping[str, object]]) -> bytes:
    """El CSV (UTF-8 con marca, `;`) de las filas de la tabla de escenarios: el nombre tal cual
    (quien llama ya lo neutralizó contra fórmulas) y las tres cifras a dos decimales."""
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    escritor.writerow([titulo for _, titulo in COLUMNAS_CSV_ESCENARIOS])
    for fila in filas:
        escritor.writerow(
            [str(fila["escenario"])]
            + [_cifra(fila[columna]) for columna, _ in COLUMNAS_CSV_ESCENARIOS[1:]]
        )
    return (_MARCA_UTF8 + buffer.getvalue()).encode("utf-8")
