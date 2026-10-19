"""Libro de Excel **ficticio** con la forma visual de los libros de la empresa.

Copia solo el *tipo* de rasgos (títulos en celdas combinadas, encabezados oscuros con letra blanca,
columnas y filas ocultas, fila separadora baja, panel inmovilizado, color de pestaña, comentario y
formato numérico con paréntesis y raya); todos los textos y números son inventados. Ningún dato de
un libro real entra aquí (NORMAS §1). El oráculo está escrito a mano en
`tests/unit/test_libro_visual.py`.
"""

from __future__ import annotations

import io

__all__ = ["libro_visual"]

_OSCURO = "#1F4E79"
_CLARO = "#DCE6F1"
_NUMERO = "#,##0.00;(#,##0.00);—"

#: (n.º, código, descripción, unidad, cantidad, precio unitario) de las filas 5 a 7.
_PARTIDAS = (
    (1, "F-01", "Friso liso <b>m2</b> & más", "m2", 120, 14.5),
    (2, "F-02", "Pared de bloque", "m2", 80, 30),
    (3, "F-03", "Demolición de friso", "m2", 50, 4),
)


def libro_visual() -> bytes:
    """Los bytes de un `.xlsx` de dos hojas (PORTADA y PRESUPUESTO), con fórmulas y valores."""
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    wb.set_properties({"author": "Autor Ficticio", "title": "Libro visual ficticio"})
    base = {"font_name": "Arial", "font_size": 10}

    def f(**kw):
        return wb.add_format({**base, **kw})

    titulo = f(bold=True, font_color="#FFFFFF", bg_color=_OSCURO, font_size=12, valign="vcenter")
    rotulo = f(bold=True)
    texto = f()
    encabezado = f(bold=True, font_color="#FFFFFF", bg_color=_OSCURO, align="center")
    numero = f(num_format=_NUMERO)
    total_texto = f(bold=True, bg_color=_CLARO, align="right")
    total_numero = f(bold=True, bg_color=_CLARO, num_format=_NUMERO)

    portada = wb.add_worksheet("PORTADA")
    portada.set_column("A:A", 2)
    portada.set_column("B:B", 26)
    portada.set_column("C:D", 18)
    portada.set_row(0, 6)
    portada.set_row(1, 30)
    portada.merge_range("B2:E2", "PRESUPUESTO DE OBRA (EJEMPLO FICTICIO)", titulo)
    portada.write("B5", "CLIENTE", rotulo)
    portada.merge_range("C5:D5", "Cliente Ficticio S.A.", texto)
    portada.write("B6", "CONTRATISTA", rotulo)
    portada.merge_range("C6:D6", "Constructora Didáctica", texto)

    hoja = wb.add_worksheet("PRESUPUESTO")
    hoja.set_tab_color(_OSCURO)
    hoja.freeze_panes("A5")
    for col, ancho in (("A", 4), ("B", 12), ("C", 40), ("D", 8), ("E", 12), ("F", 14), ("G", 14)):
        hoja.set_column(f"{col}:{col}", ancho)
    hoja.set_column("H:H", 10, None, {"hidden": True})
    for n, titulo_col in enumerate(
        ("N.º", "Código", "Descripción", "Unidad", "Cantidad", "P. unitario", "Monto", "Aux"), 0
    ):
        hoja.write(3, n, titulo_col, encabezado)
    for fila, (n, codigo, descripcion, unidad, cantidad, precio) in enumerate(_PARTIDAS, start=5):
        hoja.write(fila - 1, 0, n, texto)
        hoja.write(fila - 1, 1, codigo, texto)
        hoja.write(fila - 1, 2, descripcion, texto)
        hoja.write(fila - 1, 3, unidad, texto)
        hoja.write(fila - 1, 4, cantidad, numero)
        hoja.write(fila - 1, 5, precio, numero)
        hoja.write_formula(fila - 1, 6, f"=E{fila}*F{fila}", numero, cantidad * precio)
    hoja.write_comment("E6", "Cantidad del proyectista (ficticio)")
    hoja.set_row(7, None, None, {"hidden": True})
    hoja.write("C8", "FILA AUXILIAR OCULTA", texto)
    hoja.write("G8", 999, numero)
    hoja.set_row(8, 4)
    hoja.merge_range("A10:F10", "TOTAL SIN IVA", total_texto)
    total = sum(c * p for *_, c, p in _PARTIDAS)
    hoja.write_formula("G10", "=SUM(G5:G7)", total_numero, total)

    wb.close()
    return buf.getvalue()
