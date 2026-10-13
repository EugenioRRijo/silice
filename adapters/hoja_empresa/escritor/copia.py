"""Copia celda a celda de una hoja del libro recibido (openpyxl) al modelo de salida (spec F-D4).

Se copian las mismas posiciones: valores, fórmulas (en crudo; las reescribe `referencias`), estilos,
comentarios (sin autor), anchos de columna, altos de fila, celdas combinadas, validaciones de lista,
formatos condicionales simples (valor de celda y expresión), configuración de impresión básica,
paneles inmovilizados, visibilidad, color de pestaña, zoom, cuadrícula e imágenes.

Límites declarados: los gráficos no se copian (openpyxl no los lee); tampoco los hipervínculos, la
protección de hoja ni los formatos condicionales de barras, escalas o iconos.
"""

from __future__ import annotations

import io
from collections.abc import Mapping
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from adapters.hoja_empresa.escritor.estilos import Estilo, LectorEstilos
from adapters.hoja_empresa.escritor.formulas import col_num, letra
from adapters.hoja_empresa.escritor.hoja import CeldaSalida, HojaSalida, Imagen
from adapters.hoja_empresa.modelo import clave

__all__ = ["aspecto_de_hoja", "copiar_hoja", "formula_de", "tamano_imagen", "valor_literal"]

_EMU_PX = 9525
_OPERADORES = {
    "equal": "==",
    "notEqual": "!=",
    "greaterThan": ">",
    "lessThan": "<",
    "greaterThanOrEqual": ">=",
    "lessThanOrEqual": "<=",
    "between": "between",
    "notBetween": "not between",
}
_VALIDACIONES = {
    "list": "list",
    "whole": "integer",
    "decimal": "decimal",
    "date": "date",
    "time": "time",
    "textLength": "length",
    "custom": "custom",
}
_OPERADORES_DV = {
    "between": "between",
    "notBetween": "not between",
    "equal": "==",
    "notEqual": "!=",
    "greaterThan": ">",
    "lessThan": "<",
    "greaterThanOrEqual": ">=",
    "lessThanOrEqual": "<=",
}


def formula_de(celda: Any) -> str | None:
    """Texto de la fórmula de una celda openpyxl (con '='), o None."""
    if getattr(celda, "data_type", None) != "f":
        return None
    v = celda.value
    texto = getattr(v, "text", None) or (v if isinstance(v, str) else None)
    if not texto:
        return None
    return texto if texto.startswith("=") else "=" + texto


def valor_literal(v: Any) -> object:
    if v is None or isinstance(v, bool | str | Decimal | datetime | date):
        return v
    if isinstance(v, int | float):
        return Decimal(str(v))
    if isinstance(v, time):
        return v.isoformat()
    return str(v)


def _rangos(sqref: Any) -> list[str]:
    return [str(r) for r in str(sqref).split()]


def copiar_hoja(
    ws: Any,
    estilos: LectorEstilos,
    guardados: Mapping[str, object],
    nombre: str | None = None,
) -> HojaSalida:
    """Copia la hoja openpyxl `ws` a una `HojaSalida` (por defecto con el mismo nombre)."""
    h = HojaSalida(nombre or ws.title)
    for (f, c), cel in ws._cells.items():
        formula = formula_de(cel)
        estilo = estilos.de_celda(cel) if getattr(cel, "has_style", False) else None
        out = CeldaSalida(estilo=estilo)
        if formula is not None:
            out.formula = formula
            out.respaldo = guardados.get(clave(ws.title, f"{letra(c)}{f}"))
        else:
            out.valor = valor_literal(cel.value)
        comentario = getattr(cel, "comment", None)
        if comentario is not None and getattr(comentario, "text", None):
            out.comentario = comentario.text
        if out.formula is None and out.valor is None and estilo is None and not out.comentario:
            continue
        h.celdas[(f, c)] = out
    _dimensiones(ws, h)
    for rango in ws.merged_cells.ranges:
        h.combinadas.append((rango.min_row, rango.min_col, rango.max_row, rango.max_col))
    _validaciones(ws, h)
    _condicionales(ws, h, estilos)
    _impresion(ws, h)
    if ws.freeze_panes:
        celda = str(ws.freeze_panes)
        col = "".join(ch for ch in celda if ch.isalpha())
        fila = int("".join(ch for ch in celda if ch.isdigit()) or 1)
        h.paneles = (fila - 1, col_num(col) - 1)
    h.oculta = ws.sheet_state in ("hidden", "veryHidden")
    tab = getattr(ws.sheet_properties, "tabColor", None)
    if tab is not None:
        h.color_pestana = estilos.color(tab)
    vista = ws.sheet_view
    if vista is not None:
        if vista.zoomScale:
            h.zoom = int(vista.zoomScale)
        h.sin_cuadricula = vista.showGridLines is False
    _imagenes(ws, h)
    return h


def aspecto_de_hoja(ws: Any) -> tuple[dict[int, tuple[float | None, bool]], dict[str, Any]]:
    """Anchos de columna e impresión de una hoja (para la maqueta de los APU)."""
    h = HojaSalida(ws.title)
    _dimensiones(ws, h)
    _impresion(ws, h)
    return h.anchos, h.impresion


def _dimensiones(ws: Any, h: HojaSalida) -> None:
    for cd in ws.column_dimensions.values():
        ancho = cd.width if cd.width and (cd.customWidth or cd.width != 13) else None
        if ancho is None and not cd.hidden:
            continue
        ini, fin = cd.min or col_num(cd.index), cd.max or col_num(cd.index)
        for c in range(ini, min(fin, 16384) + 1):
            h.anchos[c] = (ancho, bool(cd.hidden))
    for f, rd in ws.row_dimensions.items():
        if rd.height is None and not rd.hidden:
            continue
        h.altos[f] = (rd.height, bool(rd.hidden))
    fmt = getattr(ws, "sheet_format", None)
    if fmt is not None and fmt.customHeight and fmt.defaultRowHeight:
        h.alto_defecto = float(fmt.defaultRowHeight)


def _validaciones(ws: Any, h: HojaSalida) -> None:
    for dv in ws.data_validations.dataValidation:
        tipo = _VALIDACIONES.get(dv.type or "")
        if tipo is None:
            continue
        opciones: dict[str, Any] = {"validate": tipo}
        f1 = dv.formula1
        if tipo == "list":
            if f1 is None:
                continue
            if f1.startswith('"') and f1.endswith('"'):
                opciones["source"] = [x for x in f1[1:-1].split(",")]
            else:
                opciones["source"] = "=" + f1.lstrip("=")
        elif tipo == "custom":
            if f1 is None:
                continue
            opciones["value"] = "=" + f1.lstrip("=")
        else:
            opciones["criteria"] = _OPERADORES_DV.get(dv.operator or "between", "between")
            if opciones["criteria"] in ("between", "not between"):
                opciones["minimum"] = _numero_o_formula(f1)
                opciones["maximum"] = _numero_o_formula(dv.formula2)
            else:
                opciones["value"] = _numero_o_formula(f1)
        opciones["ignore_blank"] = bool(dv.allow_blank)
        if dv.showErrorMessage is False:
            opciones["show_error"] = False
        if dv.error:
            opciones["error_message"] = dv.error[:255]
        if dv.errorTitle:
            opciones["error_title"] = dv.errorTitle[:32]
        if dv.prompt:
            opciones["input_message"] = dv.prompt[:255]
        if dv.promptTitle:
            opciones["input_title"] = dv.promptTitle[:32]
        for rango in _rangos(dv.sqref):
            h.validaciones.append((rango, dict(opciones)))


def _numero_o_formula(f: str | None) -> object:
    if f is None:
        return 0
    try:
        return float(f)
    except ValueError:
        return "=" + f.lstrip("=")


def _condicionales(ws: Any, h: HojaSalida, estilos: LectorEstilos) -> None:
    for cf in ws.conditional_formatting:
        for regla in cf.rules:
            estilo = _estilo_dxf(regla.dxf, estilos)
            if regla.type == "cellIs" and regla.operator in _OPERADORES and regla.formula:
                op = _OPERADORES[regla.operator]
                opciones: dict[str, Any] = {"type": "cell", "criteria": op}
                if op in ("between", "not between"):
                    if len(regla.formula) < 2:
                        continue
                    opciones["minimum"] = "=" + regla.formula[0]
                    opciones["maximum"] = "=" + regla.formula[1]
                else:
                    opciones["value"] = "=" + regla.formula[0]
            elif regla.type == "expression" and regla.formula:
                opciones = {"type": "formula", "criteria": "=" + regla.formula[0]}
            else:
                continue
            if regla.stopIfTrue:
                opciones["stop_if_true"] = True
            for rango in _rangos(cf.sqref):
                h.condicionales.append((rango, dict(opciones), estilo))


def _estilo_dxf(dxf: Any, estilos: LectorEstilos) -> Estilo | None:
    if dxf is None:
        return None
    e = Estilo()
    f = dxf.font
    if f is not None:
        e = e.con(
            negrita=bool(f.b),
            cursiva=bool(f.i),
            color=estilos.color(f.color),
        )
    fill = dxf.fill
    if fill is not None:
        color = estilos.color(getattr(fill, "bgColor", None)) or estilos.color(
            getattr(fill, "fgColor", None)
        )
        if color:
            e = e.con(patron=1, fondo=color)
    if dxf.numFmt is not None and dxf.numFmt.formatCode:
        e = e.con(formato=dxf.numFmt.formatCode)
    return e


def _impresion(ws: Any, h: HojaSalida) -> None:
    ps = ws.page_setup
    imp: dict[str, Any] = {}
    if ps.orientation in ("landscape", "portrait"):
        imp["orientacion"] = ps.orientation
    if ps.paperSize:
        try:
            imp["papel"] = int(ps.paperSize)
        except (TypeError, ValueError):
            pass
    pr = getattr(ws.sheet_properties, "pageSetUpPr", None)
    if pr is not None and pr.fitToPage:
        imp["ajuste"] = (int(ps.fitToWidth or 0), int(ps.fitToHeight or 0))
    elif ps.scale:
        try:
            imp["escala"] = int(ps.scale)
        except (TypeError, ValueError):
            pass
    area = ws.print_area
    if area:
        texto = area if isinstance(area, str) else ",".join(area)
        imp["area"] = texto.split(",")[0]
    m = ws.page_margins
    if m is not None:
        imp["margenes"] = (m.left, m.right, m.top, m.bottom)
    if ws.print_options is not None and ws.print_options.horizontalCentered:
        imp["centrar"] = True
    if ws.print_title_rows:
        imp["titulos"] = str(ws.print_title_rows)
    h.impresion = imp


def _imagenes(ws: Any, h: HojaSalida) -> None:
    for img in getattr(ws, "_images", []):
        try:
            datos = img._data()
        except Exception:  # imagen ilegible: se omite (límite declarado)
            continue
        anc = img.anchor
        desde = getattr(anc, "_from", None)
        if desde is None:
            continue
        opciones: dict[str, Any] = {
            "x_offset": int((desde.colOff or 0) / _EMU_PX),
            "y_offset": int((desde.rowOff or 0) / _EMU_PX),
            "object_position": 2,
        }
        tam = tamano_imagen(datos)
        if tam is not None and img.width and img.height:
            opciones["x_scale"] = img.width / tam[0]
            opciones["y_scale"] = img.height / tam[1]
        h.imagenes.append(Imagen(desde.row + 1, desde.col + 1, datos, opciones))


def tamano_imagen(datos: bytes) -> tuple[int, int] | None:
    """Ancho y alto en píxeles de un PNG, GIF o JPEG, leídos de la cabecera (sin Pillow)."""
    if datos[:8] == b"\x89PNG\r\n\x1a\n" and len(datos) >= 24:
        return int.from_bytes(datos[16:20], "big"), int.from_bytes(datos[20:24], "big")
    if datos[:6] in (b"GIF87a", b"GIF89a") and len(datos) >= 10:
        return int.from_bytes(datos[6:8], "little"), int.from_bytes(datos[8:10], "little")
    if datos[:2] == b"\xff\xd8":
        flujo = io.BytesIO(datos)
        flujo.read(2)
        while True:
            marca = flujo.read(2)
            if len(marca) < 2 or marca[0] != 0xFF:
                return None
            largo = int.from_bytes(flujo.read(2), "big")
            if marca[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD):
                bloque = flujo.read(5)
                if len(bloque) < 5:
                    return None
                return int.from_bytes(bloque[3:5], "big"), int.from_bytes(bloque[1:3], "big")
            flujo.seek(largo - 2, io.SEEK_CUR)
    return None
