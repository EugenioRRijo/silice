"""Dobles para medir la auditoría sin LibreOffice real (`scripts/medir_inyeccion.py`)."""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl


class LibreOfficeFalso:
    """Doble de prueba sin LibreOffice real."""

    def version(self) -> str:
        return "LibreOffice 24.8.3.2 (falso)"

    def recalcular(self, datos: bytes, nombre: str) -> bytes:
        origen = openpyxl.load_workbook(
            io.BytesIO(datos), read_only=True, data_only=True, keep_links=False
        )
        nuevo = openpyxl.Workbook()
        nuevo.remove(nuevo.active)
        try:
            for ws_orig in origen.worksheets:
                ws_nueva = nuevo.create_sheet(ws_orig.title)
                for fila_idx, fila in enumerate(ws_orig.iter_rows(values_only=True), start=1):
                    for col_idx, valor in enumerate(fila, start=1):
                        if valor is not None:
                            ws_nueva.cell(row=fila_idx, column=col_idx, value=valor)
        finally:
            origen.close()
        buf = io.BytesIO()
        nuevo.save(buf)
        nuevo.close()
        return buf.getvalue()


def escribir_taxonomia(ruta: Path) -> Path:
    ruta.write_text(
        '[[categorias]]\n'
        'id = "TAX-01"\n'
        'nombre = "Valor fijo"\n'
        'fuente = "Fuente de prueba"\n'
        'operacion = "valor_fijo"\n'
        'peso = 1.0\n'
        'hojas = ["PRESUPUESTO"]\n',
        encoding="utf-8",
    )
    return ruta
