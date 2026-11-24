"""Pruebas del trasplante XML de valores cacheados entre libros `.xlsx`."""

from __future__ import annotations

import io
import re
import zipfile
from decimal import Decimal

import openpyxl
import xlsxwriter

from aplicacion.trasplante_valores import trasplantar
from fusion.proceso import procesar_libro
from tests.fixtures.libros_empresa import libro_limpio


class _RecalculadorFalso:
    """Doble local que genera un libro recalculado cambiando valores a mano."""

    def __init__(self, cambios: dict[str, object] | None = None) -> None:
        self._cambios = dict(cambios or {})

    def recalcular(self, datos: bytes) -> bytes:
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
        for clave_celda, nuevo_valor in self._cambios.items():
            hoja, coord = clave_celda.split("!", 1)
            ws = nuevo[hoja] if hoja in nuevo.sheetnames else nuevo.create_sheet(hoja)
            ws[coord] = nuevo_valor
        buf = io.BytesIO()
        nuevo.save(buf)
        nuevo.close()
        return buf.getvalue()


def _leer_xml_hoja(datos: bytes, nombre_archivo: str = "xl/worksheets/sheet1.xml") -> str:
    with zipfile.ZipFile(io.BytesIO(datos)) as zf:
        return zf.read(nombre_archivo).decode("utf-8")


def _tag_celda(xml: str, coord: str) -> str:
    patron = re.compile(rf'<c\b[^>]*\br="{re.escape(coord)}"[^>]*(?:/>|>.*?</c>)', re.S)
    m = patron.search(xml)
    assert m is not None, f"No se encontró la celda {coord}"
    return m.group(0)


def _libro_xlsxwriter(hoja: str, celdas: dict[str, tuple[str | None, object]]) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet(hoja)
    for coord, (formula, valor) in celdas.items():
        if formula is not None:
            ws.write_formula(coord, formula, None, valor)
        elif isinstance(valor, str):
            ws.write_string(coord, valor)
        elif isinstance(valor, bool):
            ws.write_boolean(coord, valor)
        elif isinstance(valor, (int, float, Decimal)):
            ws.write_number(coord, float(valor))
    wb.close()
    return buf.getvalue()


def _libro_valores_openpyxl(hojas: dict[str, dict[str, object]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for nombre, celdas in hojas.items():
        ws = wb.create_sheet(nombre)
        for coord, valor in celdas.items():
            ws[coord] = valor
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def test_trasplante_cambia_solo_v_de_celdas_con_formula_y_conserva_resto_del_zip() -> None:
    construido = libro_limpio()
    fila_p1 = construido.filas_partida["APU-01"]
    recalc = _RecalculadorFalso({f"PRESUPUESTO!P{fila_p1}": Decimal("99.5")}).recalcular(
        construido.datos
    )
    resultado = trasplantar(construido.datos, recalc)

    with (
        zipfile.ZipFile(io.BytesIO(construido.datos)) as z_orig,
        zipfile.ZipFile(io.BytesIO(resultado)) as z_res,
    ):
        assert z_orig.namelist() == z_res.namelist()
        for nombre in z_orig.namelist():
            if nombre.startswith("xl/worksheets/"):
                continue
            assert z_res.read(nombre) == z_orig.read(nombre), f"Cambió {nombre}"
        # PORTADA no tiene fórmulas: debe quedar idéntica byte a byte.
        assert z_res.read("xl/worksheets/sheet1.xml") == z_orig.read("xl/worksheets/sheet1.xml")

    wb_v = openpyxl.load_workbook(io.BytesIO(resultado), read_only=True, data_only=True)
    wb_f = openpyxl.load_workbook(io.BytesIO(resultado), read_only=True, data_only=False)
    try:
        assert wb_v["PRESUPUESTO"][f"P{fila_p1}"].value == 99.5
        assert str(wb_f["PRESUPUESTO"][f"P{fila_p1}"].value).startswith("=")
    finally:
        wb_v.close()
        wb_f.close()


def test_trasplante_pone_texto_numero_booleano_y_error_con_t_correcto() -> None:
    original = _libro_xlsxwriter(
        "Datos",
        {
            "A1": ("=1+1", 2),
            "A2": ('="a"', "a"),
            "A3": ("=1/0", 0),
            "A4": ("=1=1", False),
            "A5": ('=IF(1=0,"x","")', "previo"),
        },
    )
    recalculado = _libro_valores_openpyxl(
        {
            "Datos": {
                "A1": Decimal("12.345"),
                "A2": "Hola & <Mundo>",
                "A3": "#REF!",
                "A4": True,
                "A5": None,
            }
        }
    )

    resultado = trasplantar(original, recalculado)
    xml = _leer_xml_hoja(resultado)

    c_a1 = _tag_celda(xml, "A1")
    assert "t=" not in c_a1
    assert "<v>12.345</v>" in c_a1

    c_a2 = _tag_celda(xml, "A2")
    assert 't="str"' in c_a2
    assert "<v>Hola &amp; &lt;Mundo&gt;</v>" in c_a2

    c_a3 = _tag_celda(xml, "A3")
    assert 't="e"' in c_a3
    assert "<v>#REF!</v>" in c_a3

    c_a4 = _tag_celda(xml, "A4")
    assert 't="b"' in c_a4
    assert "<v>1</v>" in c_a4

    c_a5 = _tag_celda(xml, "A5")
    assert "t=" not in c_a5
    assert "<v" not in c_a5

    wb_v = openpyxl.load_workbook(io.BytesIO(resultado), read_only=True, data_only=True)
    wb_f = openpyxl.load_workbook(io.BytesIO(resultado), read_only=True, data_only=False)
    try:
        ws_v = wb_v["Datos"]
        ws_f = wb_f["Datos"]
        assert ws_v["A1"].value == 12.345
        assert ws_v["A2"].value == "Hola & <Mundo>"
        assert ws_v["A3"].value == "#REF!"
        assert ws_v["A4"].value is True
        assert ws_v["A5"].value is None
        assert ws_f["A1"].value == "=1+1"
        assert ws_f["A5"].value == '=IF(1=0,"x","")'
    finally:
        wb_v.close()
        wb_f.close()


def test_trasplante_agrega_v_si_falta_y_evita_notacion_cientifica() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Calc"
    ws["A1"] = "=1/10000000"
    ws["A2"] = "=1e-5"
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    original = buf.getvalue()
    assert "<v" not in _tag_celda(_leer_xml_hoja(original), "A1")

    recalculado = _libro_valores_openpyxl({"Calc": {"A1": Decimal("0.0000001"), "A2": 1e-5}})
    resultado = trasplantar(original, recalculado)
    xml = _leer_xml_hoja(resultado)

    assert "<v>0.0000001</v>" in _tag_celda(xml, "A1")
    assert "<v>0.00001</v>" in _tag_celda(xml, "A2")


def test_trasplante_respeta_hojas_con_espacios_en_el_nombre() -> None:
    original = _libro_xlsxwriter("Hoja Con Espacios", {"B2": ("=2+3", 5)})
    recalculado = _libro_valores_openpyxl({"Hoja Con Espacios": {"B2": 42}})

    resultado = trasplantar(original, recalculado)
    wb = openpyxl.load_workbook(io.BytesIO(resultado), read_only=True, data_only=True)
    try:
        assert wb["Hoja Con Espacios"]["B2"].value == 42
    finally:
        wb.close()


def test_trasplante_no_toca_celdas_sin_formula() -> None:
    original = _libro_xlsxwriter(
        "Hoja",
        {"A1": ("=1+1", 2), "B1": (None, 100), "B2": (None, "original")},
    )
    recalculado = _libro_valores_openpyxl(
        {"Hoja": {"A1": 7, "B1": 999, "B2": "cambiado"}}
    )

    resultado = trasplantar(original, recalculado)
    xml_orig = _leer_xml_hoja(original)
    xml_res = _leer_xml_hoja(resultado)
    assert _tag_celda(xml_res, "B1") == _tag_celda(xml_orig, "B1")
    assert _tag_celda(xml_res, "B2") == _tag_celda(xml_orig, "B2")
    assert "<v>7</v>" in _tag_celda(xml_res, "A1")


def test_resultado_de_trasplante_lo_lee_procesar_libro_sin_error() -> None:
    construido = libro_limpio()
    fila_p1 = construido.filas_partida["APU-01"]
    recalc = _RecalculadorFalso({f"PRESUPUESTO!P{fila_p1}": Decimal("99.5")}).recalcular(
        construido.datos
    )
    trasplantado = trasplantar(construido.datos, recalc)

    informe = procesar_libro(trasplantado, "limpio.xlsx").informe
    celdas_f1 = {c for h in informe.hallazgos if h.regla == "F1" for c in h.origen_ids}
    assert f"PRESUPUESTO!P{fila_p1}" in celdas_f1
