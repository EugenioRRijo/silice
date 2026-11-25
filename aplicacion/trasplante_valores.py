"""Trasplante a nivel XML de valores cacheados `<v>` desde un `.xlsx` recalculado.

Preserva byte a byte el libro original (estilos, nombres definidos, estructura y celdas sin
fórmula) y actualiza únicamente el valor cacheado `<v>` y el atributo `t` de las celdas que
contienen una fórmula `<f>`. No toca `core/`.
"""

from __future__ import annotations

import io
import math
import posixpath
import re
import warnings
import zipfile
from collections.abc import Mapping
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import openpyxl
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import fromstring as xml_seguro
from openpyxl.utils.cell import get_column_letter

from adapters.hoja_empresa.guardia import verificar_archivo

__all__ = ["trasplantar"]

_ATRS_XML = r"(?:\s+[^\s=/<>]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))*\s*"
_CELDA_XML = re.compile(
    rf"<(?P<p>(?:\w+:)?)c\b(?P<attrs>{_ATRS_XML})(?:/>|>(?P<cuerpo>.*?)</(?P=p)c>)",
    re.S,
)
_ATRIBUTO_XML = re.compile(r'(?P<nombre>[^\s=/<>]+)\s*=\s*(?P<q>["\'])(?P<valor>.*?)(?P=q)')
_TAG_F = re.compile(
    rf"<(?P<fp>(?:\w+:)?)f\b(?P<fattrs>{_ATRS_XML})(?:/>|>(?P<ftext>.*?)</(?P=fp)f>)",
    re.S,
)
_TAG_V = re.compile(
    rf"<(?P<vp>(?:\w+:)?)v\b(?P<vattrs>{_ATRS_XML})(?:/>|>(?P<vtext>.*?)</(?P=vp)v>)",
    re.S,
)
_TAG_IS = re.compile(
    rf"<(?P<ip>(?:\w+:)?)is\b(?P<iattrs>{_ATRS_XML})(?:/>|>(?P<itext>.*?)</(?P=ip)is>)",
    re.S,
)
_ATTR_T = re.compile(r"\s+(?:\w+:)?t\s*=\s*(?:\"[^\"]*\"|'[^']*')")

_ERRORES_EXCEL: frozenset[str] = frozenset({
    "#NULL!",
    "#DIV/0!",
    "#VALUE!",
    "#REF!",
    "#NAME?",
    "#NUM!",
    "#N/A",
    "#GETTING_DATA",
    "#SPILL!",
    "#CALC!",
    "#FIELD!",
    "#UNKNOWN!",
    "#BLOCKED!",
    "#CONNECT!",
})
_BASE_EXCEL = datetime(1899, 12, 30)


def _a_xml(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _attr(attrs: str, objetivo: str) -> str | None:
    for m in _ATRIBUTO_XML.finditer(attrs):
        if m.group("nombre").rsplit(":", 1)[-1] == objetivo:
            return m.group("valor")
    return None


def _comprobar_xml(nombre: str, contenido: bytes) -> None:
    try:
        xml_seguro(contenido, forbid_dtd=True)
    except (DefusedXmlException, ParseError) as err:
        raise ValueError(f"XML inválido en «{nombre}»: {err}") from err


def _mapa_hojas(paquete: Mapping[str, bytes]) -> dict[str, str]:
    rels_bytes = paquete.get("xl/_rels/workbook.xml.rels", b"")
    wb_bytes = paquete.get("xl/workbook.xml", b"")
    if not rels_bytes or not wb_bytes:
        return {}
    rels_root = xml_seguro(rels_bytes, forbid_dtd=True)
    destinos: dict[str, str] = {}
    for el in rels_root:
        rid = el.attrib.get("Id")
        target = el.attrib.get("Target", "")
        if rid and target:
            parte = (
                posixpath.normpath(target.lstrip("/"))
                if target.startswith("/")
                else posixpath.normpath(posixpath.join("xl", target))
            )
            destinos[rid] = parte
    wb_root = xml_seguro(wb_bytes, forbid_dtd=True)
    mapa: dict[str, str] = {}
    for el in wb_root.iter():
        if el.tag.rsplit("}", 1)[-1] != "sheet":
            continue
        nombre = el.attrib.get("name")
        rid = next((v for k, v in el.attrib.items() if k.rsplit("}", 1)[-1] == "id"), None)
        if nombre is not None and rid in destinos:
            mapa[nombre] = destinos[rid]
    return mapa


def _leer_valores_recalculados(recalculado: bytes) -> dict[str, dict[str, tuple[object, str]]]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        wb = openpyxl.load_workbook(
            io.BytesIO(recalculado),
            read_only=True,
            data_only=True,
            keep_vba=False,
            keep_links=False,
        )
    por_hoja: dict[str, dict[str, tuple[object, str]]] = {}
    try:
        for ws in wb.worksheets:
            celdas: dict[str, tuple[object, str]] = {}
            for fila in ws.iter_rows(values_only=False):
                for celda in fila:
                    if celda.value is not None:
                        coord = f"{get_column_letter(celda.column)}{celda.row}"
                        celdas[coord] = (celda.value, str(getattr(celda, "data_type", "")))
            por_hoja[ws.title] = celdas
    finally:
        wb.close()
    return por_hoja


def _vacios_recalculados(
    recalculado: bytes,
) -> dict[str, set[str]]:
    """Celdas de fórmula del recalculado cuyo resultado es la cadena vacía (`t="str"`, `<v/>`).

    openpyxl devuelve `None` para ellas y no se distinguen de una celda ausente.
    """
    with zipfile.ZipFile(io.BytesIO(recalculado)) as zf:
        paquete = {info.filename: zf.read(info.filename) for info in zf.infolist()}
    por_hoja: dict[str, set[str]] = {}
    for nombre, parte in _mapa_hojas(paquete).items():
        if parte not in paquete:
            continue
        xml = paquete[parte].decode("utf-8", "replace")
        vacios: set[str] = set()
        for m in _CELDA_XML.finditer(xml):
            cuerpo = m.group("cuerpo") or ""
            if _attr(m.group("attrs"), "t") != "str" or _TAG_F.search(cuerpo) is None:
                continue
            mv = _TAG_V.search(cuerpo)
            coord = _attr(m.group("attrs"), "r")
            if coord and (mv is None or not (mv.group("vtext") or "")):
                vacios.add(coord.upper())
        por_hoja[nombre] = vacios
    return por_hoja


def _fmt_float(valor: float) -> str:
    limpio = 0.0 if valor == 0.0 else valor
    texto = repr(limpio)
    if "e" in texto.lower():
        dec = Decimal(texto)
        if -20 <= dec.adjusted() <= 20:
            return format(dec, "f")
    return texto


def _serial_excel(valor: datetime | date | time) -> str:
    if isinstance(valor, datetime):
        dias = (valor - _BASE_EXCEL).total_seconds() / 86400
    elif isinstance(valor, date):
        dt = datetime(valor.year, valor.month, valor.day)
        dias = (dt - _BASE_EXCEL).total_seconds() / 86400
    else:
        segundos = valor.hour * 3600 + valor.minute * 60 + valor.second + valor.microsecond / 1e6
        dias = segundos / 86400
    return _fmt_float(dias)


def _formatear_valor_xml(valor: Any, data_type: str) -> tuple[str | None, str]:
    if isinstance(valor, bool):
        return "b", ("1" if valor else "0")
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            return "e", "#NUM!"
        norm = valor.copy_abs() if valor.is_zero() else valor
        return None, format(norm, "f")
    if isinstance(valor, int):
        return None, str(valor)
    if isinstance(valor, float):
        if not math.isfinite(valor):
            return "e", "#NUM!"
        return None, _fmt_float(valor)
    if isinstance(valor, (datetime, date, time)):
        return None, _serial_excel(valor)
    if isinstance(valor, str):
        if data_type == "e" or valor in _ERRORES_EXCEL:
            return "e", _a_xml(valor)
        return "str", _a_xml(valor)
    return "str", _a_xml(str(valor))


def _trasplantar_hoja(xml: str, valores: Mapping[str, tuple[object, str]]) -> str:
    def reemplazar(m: re.Match[str]) -> str:
        cuerpo = m.group("cuerpo")
        if not cuerpo:
            return m.group(0)
        mf = _TAG_F.search(cuerpo)
        if mf is None:
            return m.group(0)
        attrs = m.group("attrs")
        coord = _attr(attrs, "r")
        if not coord:
            return m.group(0)
        p = m.group("p")
        attrs_limpios = _ATTR_T.sub("", attrs)
        encontrado = valores.get(coord.upper())
        cuerpo = _TAG_IS.sub("", cuerpo)
        if encontrado is None:
            nuevo_cuerpo = _TAG_V.sub("", cuerpo)
            return f"<{p}c{attrs_limpios}>{nuevo_cuerpo}</{p}c>"
        valor, tipo_oxl = encontrado
        nuevo_t, texto_v = _formatear_valor_xml(valor, tipo_oxl)
        attrs_final = f'{attrs_limpios.rstrip()} t="{nuevo_t}"' if nuevo_t else attrs_limpios
        cuerpo = _TAG_IS.sub("", cuerpo)
        mf = _TAG_F.search(cuerpo)
        assert mf is not None
        nuevo_cuerpo, n = _TAG_V.subn(
            lambda vm, tv=texto_v: f"<{vm.group('vp')}v>{tv}</{vm.group('vp')}v>",
            cuerpo,
            count=1,
        )
        if n == 0:
            nuevo_cuerpo = f"{cuerpo[:mf.end()]}<{p}v>{texto_v}</{p}v>{cuerpo[mf.end():]}"
        return f"<{p}c{attrs_final}>{nuevo_cuerpo}</{p}c>"

    return _CELDA_XML.sub(reemplazar, xml)


def trasplantar(original: bytes, recalculado: bytes) -> bytes:
    """Actualiza en `original` solo los `<v>` y `t` de celdas con fórmula desde `recalculado`."""
    verificar_archivo(original, "original.xlsx")
    verificar_archivo(recalculado, "recalculado.xlsx")

    with zipfile.ZipFile(io.BytesIO(original)) as zf:
        infos = zf.infolist()
        paquete = {info.filename: zf.read(info.filename) for info in infos}

    mapa = _mapa_hojas(paquete)
    valores_rec = _leer_valores_recalculados(recalculado)
    for nombre_hoja, vacios in _vacios_recalculados(recalculado).items():
        celdas = valores_rec.setdefault(nombre_hoja, {})
        for coord in vacios:
            celdas.setdefault(coord, ("", "s"))

    for nombre_hoja, parte in mapa.items():
        if parte not in paquete:
            continue
        xml_orig = paquete[parte].decode("utf-8")
        xml_nuevo = _trasplantar_hoja(xml_orig, valores_rec.get(nombre_hoja, {}))
        if xml_nuevo != xml_orig:
            codificado = xml_nuevo.encode("utf-8")
            _comprobar_xml(parte, codificado)
            paquete[parte] = codificado

    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in infos:
            zout.writestr(info, paquete[info.filename])
    return salida.getvalue()
