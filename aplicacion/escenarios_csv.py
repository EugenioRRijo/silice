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

Arbitraje de feature/vivo-control: las cifras las presenta quien llama con la presentación segura
de la API (`api.presentacion.cifra_presentada`: el exacto si no cabe al cuantizar, «no disponible»
si no es finita; la capa de aplicación no importa `api`), y el nombre se neutraliza aquí contra
fórmulas (`aplicacion.formulas`).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Iterable, Mapping
from decimal import Decimal

from aplicacion.formulas import neutralizar_formula

__all__ = ["COLUMNAS_CSV_ESCENARIOS", "csv_de_escenarios"]

#: (columna de `comparar_escenarios`, encabezado del CSV): los de la tabla de la pantalla.
COLUMNAS_CSV_ESCENARIOS = (
    ("escenario", "Escenario"),
    ("total", "Total"),
    ("variacion", "Variación"),
    ("variacion_pct", "Variación %"),
)
_MARCA_UTF8 = "\ufeff"


def csv_de_escenarios(
    filas: Iterable[Mapping[str, object]], *, presentar: Callable[[Decimal], str]
) -> bytes:
    """El CSV (UTF-8 con marca, `;`) de las filas de la tabla de escenarios: el nombre
    neutralizado contra fórmulas y las tres cifras con `presentar`."""
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    escritor.writerow([titulo for _, titulo in COLUMNAS_CSV_ESCENARIOS])
    for fila in filas:
        escritor.writerow(
            [neutralizar_formula(str(fila["escenario"]))]
            + [presentar(Decimal(fila[columna])) for columna, _ in COLUMNAS_CSV_ESCENARIOS[1:]]
        )
    return (_MARCA_UTF8 + buffer.getvalue()).encode("utf-8")
