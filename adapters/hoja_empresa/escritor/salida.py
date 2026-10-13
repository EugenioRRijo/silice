"""Vuelca el `LibroSalida` a un `.xlsx` con XlsxWriter (spec 1.5, F-D3 y F-D10).

- Todo texto se escribe con `write_string` (nunca se interpreta como fórmula, número ni URL) y toda
  fórmula con `write_formula` y su valor calculado.
- Sin macros, sin vínculos externos y sin autor: autor y empresa = "Silice", más las propiedades
  personalizadas `silice_sha256_origen`, `silice_version` y `silice_fecha`.
- Las celdas combinadas se escriben antes que el contenido, para que cada celda conserve su propio
  estilo (bordes) dentro del rango.
- Última barrera de seguridad (revisión 1.5): una fórmula, validación, formato condicional, nombre
  definido o serie de gráfico que la lista negra de `formulas.motivo_peligro` rechaza no se escribe
  como fórmula (la celda sale con su valor, como texto si es texto). La devolución ya las convierte
  y anota antes (`devolucion`); aquí solo se impide que una se cuele.
- Un gráfico se escribe con su tamaño acotado (`graficos.TOPE_PX`) y, si XlsxWriter lo rechaza, se
  omite: `revisar_grafico` lo prueba antes en un libro de ensayo para que la devolución lo anote.
"""

from __future__ import annotations

import io
import re
import warnings
import zipfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import xlsxwriter
from xlsxwriter.exceptions import OverlappingRange

from adapters.hoja_empresa.escritor.calculos import Err
from adapters.hoja_empresa.escritor.estilos import Estilo
from adapters.hoja_empresa.escritor.formulas import MAX_COL, MAX_FILA, es_formula_peligrosa
from adapters.hoja_empresa.escritor.graficos import TOPE_PX
from adapters.hoja_empresa.escritor.hoja import NADA, HojaSalida, LibroSalida

__all__ = ["escribir_xlsx", "revisar_grafico", "tamano_grafico", "valor_para_xlsx"]

#: Máximo de columnas o filas que se recorren para medir un gráfico anclado a dos celdas.
_MAX_PASOS = 2_000

_OPCIONES = {
    "in_memory": True,
    "strings_to_formulas": False,
    "strings_to_numbers": False,
    "strings_to_urls": False,
    "nan_inf_to_errors": True,
}


def valor_para_xlsx(v: object) -> object:
    """El resultado guardado de una fórmula en el tipo que acepta XlsxWriter."""
    if v is NADA or v is None:
        return 0
    if isinstance(v, bool):
        return v
    if isinstance(v, Decimal | int | float):
        return float(v) + 0.0  # sin "-0.0"
    if isinstance(v, Err):
        return v.codigo
    if isinstance(v, datetime | date):
        base = datetime(1899, 12, 30)
        d = v if isinstance(v, datetime) else datetime(v.year, v.month, v.day)
        return (d - base).total_seconds() / 86400
    return str(v)


class _Formatos:
    def __init__(self, wb: Any) -> None:
        self.wb = wb
        self._cache: dict[Estilo, Any] = {}
        self._dxf: dict[Estilo, Any] = {}

    def de(self, e: Estilo | None) -> Any:
        if e is None:
            return None
        f = self._cache.get(e)
        if f is None:
            f = self.wb.add_format(e.a_xlsxwriter())
            self._cache[e] = f
        return f

    def dxf(self, e: Estilo | None) -> Any:
        if e is None:
            return None
        f = self._dxf.get(e)
        if f is None:
            f = self.wb.add_format(e.a_xlsxwriter())
            self._dxf[e] = f
        return f


def _ancho_usuario(ancho: float | None) -> float | None:
    """El ancho que hay que darle a XlsxWriter para que escriba en el XML el ancho `ancho` del
    libro original (XlsxWriter suma el margen de celda: 5 píxeles sobre 7 por carácter)."""
    if ancho is None:
        return None
    if ancho >= 1 + 5 / 7:
        return ancho - 5 / 7
    return max(ancho * 7 / 12, 0.0)


def _sin_hoja(rango: str) -> str:
    return rango.split("!")[-1].replace("$", "")


def _dimensiones(ws: Any, h: HojaSalida) -> None:
    if h.alto_defecto:
        ws.set_default_row(h.alto_defecto)
    for c, (ancho, oculta) in sorted(h.anchos.items()):
        opciones = {"hidden": True} if oculta else {}
        ws.set_column(c - 1, c - 1, _ancho_usuario(ancho), None, opciones)
    for f, (alto, oculta) in sorted(h.altos.items()):
        opciones = {"hidden": True} if oculta else {}
        ws.set_row(f - 1, alto, None, opciones)


def _escribir_hoja(wb: Any, fm: _Formatos, h: HojaSalida) -> Any:
    ws = wb.add_worksheet(h.nombre)
    _dimensiones(ws, h)
    for f1, c1, f2, c2 in h.combinadas:
        if (f1, c1) == (f2, c2):
            continue
        tope = h.celdas.get((f1, c1))
        try:
            ws.merge_range(f1 - 1, c1 - 1, f2 - 1, c2 - 1, "", fm.de(tope.estilo if tope else None))
        except OverlappingRange:
            continue
    for (f, c), cel in sorted(h.celdas.items()):
        r, k = f - 1, c - 1
        fmt = fm.de(cel.estilo)
        if cel.formula and not es_formula_peligrosa(cel.formula):
            valor = cel.fijo if cel.fijo is not NADA else cel.calculado
            ws.write_formula(r, k, cel.formula, fmt, valor_para_xlsx(valor))
        else:
            v = cel.valor
            if cel.formula:  # peligrosa: su valor, nunca la fórmula
                v = cel.fijo if cel.fijo is not NADA else cel.calculado
                v = cel.respaldo if v is NADA else v
                v = v.codigo if isinstance(v, Err) else v
            if isinstance(v, str):
                if v == "":
                    ws.write_blank(r, k, None, fmt)
                else:
                    ws.write_string(r, k, v, fmt)
            elif isinstance(v, bool):
                ws.write_boolean(r, k, v, fmt)
            elif isinstance(v, Decimal | int | float):
                ws.write_number(r, k, float(v), fmt)
            elif isinstance(v, datetime | date):
                ws.write_datetime(r, k, v, fmt)
            elif v is None:
                ws.write_blank(r, k, None, fmt)
            else:
                ws.write_string(r, k, str(v), fmt)
        if cel.comentario:
            ws.write_comment(r, k, cel.comentario[:32767], {"author": "Silice"})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for rango, opciones in h.validaciones:
            if _opciones_peligrosas(opciones):
                continue
            ws.data_validation(_sin_hoja(rango), opciones)
        for rango, opciones, estilo in h.condicionales:
            if _opciones_peligrosas(opciones):
                continue
            op = dict(opciones)
            if estilo is not None:
                op["format"] = fm.dxf(estilo)
            ws.conditional_format(_sin_hoja(rango), op)
    _impresion(ws, h)
    if h.paneles is not None and h.paneles != (0, 0):
        ws.freeze_panes(*h.paneles)
    if h.color_pestana:
        ws.set_tab_color("#" + h.color_pestana)
    if h.zoom:
        ws.set_zoom(h.zoom)
    if h.sin_cuadricula:
        ws.hide_gridlines(2)
    for img in h.imagenes:
        nombre = "imagen.png" if img.datos[:4] == b"\x89PNG" else "imagen.jpeg"
        ws.insert_image(
            img.fila - 1, img.col - 1, nombre, {"image_data": io.BytesIO(img.datos), **img.opciones}
        )
    for g in h.graficos:
        try:
            _grafico(wb, ws, h, g)
        except Exception:  # noqa: BLE001 - un gráfico que XlsxWriter rechaza se omite
            continue
    return ws


def _opciones_peligrosas(opciones: dict[str, Any]) -> bool:
    return any(
        es_formula_peligrosa(opciones.get(k))
        for k in ("source", "value", "minimum", "maximum", "criteria")
    )


def _serie_peligrosa(serie: dict[str, Any]) -> bool:
    return any(es_formula_peligrosa(serie.get(k)) for k in ("name", "categories", "values"))


def _px_col(h: HojaSalida, c: int) -> int:
    ancho = h.anchos.get(c, (None, False))
    if ancho[1]:
        return 0
    w = ancho[0] if ancho[0] is not None else 8.43
    return int(w * 7 + 0.5) + 5 if w >= 1 else int(w * 12 + 0.5)


def _px_fila(h: HojaSalida, f: int) -> int:
    alto = h.altos.get(f, (None, False))
    if alto[1]:
        return 0
    pt = alto[0] if alto[0] is not None else (h.alto_defecto or 15.0)
    return int(pt * 4 / 3 + 0.5)


def _px_tramo(medida: Any, h: HojaSalida, ini: int, fin: int) -> int:
    """Píxeles de las columnas (o filas) [ini, fin) según `medida`, sin pasar de `TOPE_PX` ni de
    `_MAX_PASOS` recorridas: un anclaje enorme no recorre un millón de filas."""
    total = 0
    for i in range(ini, min(fin, ini + _MAX_PASOS)):
        total += medida(h, i)
        if total >= TOPE_PX:
            return TOPE_PX
    return total


def _acotar(n: int) -> int:
    return min(max(int(n), 0), TOPE_PX)


def tamano_grafico(h: HojaSalida, g: Any) -> tuple[int, int]:
    """Ancho y alto en píxeles con que se escribe el gráfico, acotados a `TOPE_PX`."""
    if g.hasta is not None:
        f2, c2, dx, dy = g.hasta
        ancho = _px_tramo(_px_col, h, g.col, c2) - g.x_offset + dx
        alto = _px_tramo(_px_fila, h, g.fila, f2) - g.y_offset + dy
    elif g.tamano is not None:
        ancho, alto = g.tamano
    else:
        ancho, alto = 480, 288
    return _acotar(ancho), _acotar(alto)


def revisar_grafico(h: HojaSalida, g: Any) -> str | None:
    """None si el gráfico se puede escribir; si no, por qué se omite.

    Lo prueba en un libro de ensayo en memoria (la misma llamada que `escribir_xlsx`, cerrando el
    libro para que XlsxWriter valide también las series), así la devolución puede anotarlo en las
    transformaciones del calcado antes de escribir.
    """
    if any(_serie_peligrosa(s) for s in g.series):
        return "una serie lee otro libro o usa una función que sale del libro"
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, _OPCIONES)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ws = wb.add_worksheet(h.nombre)
            _dimensiones(ws, h)
            _grafico(wb, ws, h, g)
            wb.close()
    except Exception as exc:  # noqa: BLE001 - cualquier rechazo de XlsxWriter omite el gráfico
        wb.fileclosed = True
        return f"XlsxWriter no lo pudo escribir ({type(exc).__name__})"
    try:
        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
            dibujos = [n for n in zf.namelist() if n.startswith("xl/drawings/drawing")]
            xml = zf.read(dibujos[0]).decode("utf-8") if dibujos else ""
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError):
        return "XlsxWriter no lo pudo escribir"
    if not xml:
        return "XlsxWriter no lo pudo anclar en la hoja"
    ancla = re.compile(r"<xdr:col>(\d+)</xdr:col>.*?<xdr:row>(\d+)</xdr:row>", re.S)
    for col, fila in ancla.findall(xml):
        if int(col) >= MAX_COL or int(fila) >= MAX_FILA:
            return "su anclaje queda fuera de la hoja"
    return None


def _grafico(wb: Any, ws: Any, h: HojaSalida, g: Any) -> None:
    if any(_serie_peligrosa(s) for s in g.series):
        return
    opciones: dict[str, Any] = {"type": g.tipo}
    if g.subtipo and g.tipo in ("column", "bar", "line", "area"):
        opciones["subtype"] = g.subtipo
    chart = wb.add_chart(opciones)
    if chart is None:
        return
    for serie in g.series:
        chart.add_series(dict(serie))
    if g.titulo:
        chart.set_title({"name": g.titulo})
    if g.tipo not in ("pie", "doughnut"):
        if g.eje_x:
            chart.set_x_axis({"name": g.eje_x})
        if g.eje_y:
            chart.set_y_axis({"name": g.eje_y})
    if g.leyenda == "none":
        chart.set_legend({"none": True})
    elif g.leyenda:
        chart.set_legend({"position": g.leyenda})
    ancho, alto = tamano_grafico(h, g)
    if ancho > 20 and alto > 20:
        chart.set_size({"width": ancho, "height": alto})
    ws.insert_chart(
        g.fila - 1,
        g.col - 1,
        chart,
        {"x_offset": _acotar(g.x_offset), "y_offset": _acotar(g.y_offset), "object_position": 1},
    )


def _impresion(ws: Any, h: HojaSalida) -> None:
    imp = h.impresion
    if imp.get("orientacion") == "landscape":
        ws.set_landscape()
    elif imp.get("orientacion") == "portrait":
        ws.set_portrait()
    if imp.get("papel"):
        ws.set_paper(imp["papel"])
    if "ajuste" in imp:
        ws.fit_to_pages(*imp["ajuste"])
    elif imp.get("escala"):
        ws.set_print_scale(imp["escala"])
    if imp.get("area"):
        area = _sin_hoja(imp["area"])
        if re.fullmatch(r"[A-Z]{1,3}\d+:[A-Z]{1,3}\d+", area):
            ws.print_area(area)
    if imp.get("margenes"):
        izq, der, arr, aba = imp["margenes"]
        ws.set_margins(left=izq, right=der, top=arr, bottom=aba)
    if imp.get("centrar"):
        ws.center_horizontally()
    titulos = imp.get("titulos")
    if titulos:
        m = re.search(r"\$?(\d+):\$?(\d+)", titulos)
        if m:
            ws.repeat_rows(int(m.group(1)) - 1, int(m.group(2)) - 1)


def escribir_xlsx(libro: LibroSalida) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, _OPCIONES)
    fm = _Formatos(wb)
    hojas = [_escribir_hoja(wb, fm, libro.hojas[n]) for n in libro.orden]
    visibles = [i for i, n in enumerate(libro.orden) if not libro.hojas[n].oculta]
    if visibles:
        hojas[visibles[0]].activate()
        hojas[visibles[0]].set_first_sheet()
    for i, n in enumerate(libro.orden):
        if libro.hojas[n].oculta and i != (visibles[0] if visibles else -1):
            hojas[i].hide()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for nombre, texto in sorted(libro.nombres.items()):
            if es_formula_peligrosa(texto):
                continue
            wb.define_name(nombre, texto)
    wb.set_properties(dict(libro.propiedades))
    for k, v in libro.propiedades_extra.items():
        wb.set_custom_property(k, v, "text")
    wb.close()
    return buf.getvalue()
