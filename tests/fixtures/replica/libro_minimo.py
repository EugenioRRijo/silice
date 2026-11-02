"""Libro mínimo, **ficticio**, del oráculo compartido de coordenadas (Sílice 1.2.0, Task 2.6).

Lo leen la réplica visual de Python (`adapters/hoja_empresa/visual.py`) y, a través de
`libro_minimo.json`, la conversión a Univer del frontend (`aUniver.test.ts`). Está construido con
XlsxWriter y no con openpyxl por una razón: openpyxl nunca guarda el valor calculado de una fórmula
y la celda `F12` necesita el suyo guardado, como lo deja Excel. El resto lo escribe igual que
Excel: la combinada lleva sus celdas cubiertas con el estilo del origen, los anchos salen de la
fórmula de ECMA-376 (§18.3.1.13) y la fecha es un número de serie con formato de fecha.

Todos los colores son `rgb` explícitos: el oráculo no depende del tema del libro. El único color de
tema es el de la fuente por omisión (`theme="1"`, el texto del tema), que en todo tema de Office es
negro.

Contenido (la tabla completa, con su deducción, está en `ORACULO.md`):

- `PORTADA`: título en negrita de 14 pt, un monto con formato `#,##0.00`, una fecha, un booleano.
  Columna A de 24 caracteres, columnas B:C de 14 (un solo `<col min=2 max=3>`), fila 1 de 21,75 pt.
- `PLAN DE PAGOS` (nombre con espacio): `A1:D1` combinada (cruza la columna C oculta) con negrita,
  relleno y texto ajustado; encabezados con borde; columna C oculta; fila 5 oculta; paneles
  congelados en `B3`; `AA3` con texto; `F12` con la fórmula `=F11*2` y el valor guardado 200.
- `AUX`: hoja oculta con una sola celda.
"""

from __future__ import annotations

import io
from datetime import datetime

NOMBRE = "libro_minimo.xlsx"

#: Fecha fija de creación: el mismo código produce siempre los mismos bytes (y el mismo SHA-256).
_CREADO = datetime(2026, 10, 18)


def libro_minimo() -> bytes:
    """Los bytes del `.xlsx` mínimo. Determinista: dos llamadas dan los mismos bytes."""
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    wb.set_properties({"created": _CREADO, "author": "Oraculo ficticio"})

    negrita14 = wb.add_format({"bold": True, "font_size": 14})
    numero = wb.add_format({"num_format": "#,##0.00"})
    fecha = wb.add_format({"num_format": "dd/mm/yyyy"})
    titulo = wb.add_format(
        {
            "font_name": "Arial",
            "font_size": 12,
            "bold": True,
            "font_color": "#1F3864",
            "bg_color": "#D9E1F2",
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        }
    )
    encabezado = wb.add_format({"bold": True, "border": 1})
    nota = wb.add_format(
        {
            "italic": True,
            "underline": 1,
            "font_color": "#C00000",
            "align": "right",
            "valign": "top",
        }
    )

    # --- PORTADA ---
    portada = wb.add_worksheet("PORTADA")
    portada.set_column("A:A", 24)
    portada.set_column("B:C", 14)
    portada.set_row(0, 21.75)
    portada.write_string("A1", "Obra ficticia", negrita14)
    portada.write_string("A2", "Monto contratado")
    portada.write_number("B2", 1234.5, numero)
    portada.write_string("A3", "Fecha de corte")
    portada.write_datetime("B3", datetime(2026, 10, 18), fecha)
    portada.write_string("A4", "Vigente")
    portada.write_boolean("B4", True)

    # --- PLAN DE PAGOS ---
    plan = wb.add_worksheet("PLAN DE PAGOS")
    plan.set_column("A:A", 20)
    plan.set_column("B:B", 12)
    plan.set_column("C:C", 12, None, {"hidden": True})
    plan.set_column("D:D", 15)
    plan.set_column("F:F", 10)
    plan.set_row(0, 30)
    plan.set_row(4, None, None, {"hidden": True})
    plan.freeze_panes("B3")
    plan.merge_range("A1:D1", "Plan de pagos ficticio", titulo)
    plan.write_string("A2", "Hito", encabezado)
    plan.write_string("B2", "Monto", encabezado)
    plan.write_string("D2", "Fecha", encabezado)
    plan.write_string("A3", "Anticipo")
    plan.write_number("B3", 1500.5, numero)
    plan.write_string("D3", "Tras la columna oculta")
    plan.write_string("AA3", "Nota lejana", nota)
    plan.write_string("A5", "Fila oculta")
    plan.write_number("F11", 100, numero)
    plan.write_formula("F12", "=F11*2", numero, 200)

    # --- AUX (oculta) ---
    aux = wb.add_worksheet("AUX")
    aux.hide()
    aux.write_string("A1", "Hoja oculta")

    wb.close()
    return buf.getvalue()
