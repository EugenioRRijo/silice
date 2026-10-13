"""Gráficos del libro recibido, rehechos con XlsxWriter (spec 1.5, F-D4: "el mismo aspecto").

openpyxl no lee los gráficos de un libro existente, así que se leen del propio `.xlsx` (con
defusedxml): tipo (columnas, barras, líneas, área, torta, anillo), agrupación, series (nombre,
categorías y valores como referencias), color sólido de cada serie, título, títulos de los ejes,
leyenda y anclaje. Las series apuntan a hojas copiadas que conservan sus posiciones (RESUMEN,
GASTOS, CRONOGRAMA), así que las mismas referencias siguen valiendo; un gráfico que lee una hoja que
no sale en la devolución se omite y queda anotado.

Límites declarados: no se reproducen formatos finos (ejes secundarios, etiquetas de datos con
formato, rellenos degradados, estilos de línea): el gráfico conserva tipo, datos, colores sólidos,
títulos, leyenda y tamaño.

Anclajes acotados (revisión de seguridad 1.5): la fila y la columna de `<xdr:from>`/`<xdr:to>` se
acotan a la hoja de Excel (1 048 576 filas, 16 384 columnas) y los desplazamientos y el tamaño a
`TOPE_PX` píxeles: un anclaje enorme o negativo en un libro ajeno no puede colgar el escritor.
"""

from __future__ import annotations

import io
import posixpath
import zipfile
from dataclasses import dataclass, field
from typing import Any

from adapters.hoja_empresa.escritor.formulas import MAX_COL, MAX_FILA

__all__ = ["TOPE_PX", "Grafico", "leer_graficos"]

_EMU_PX = 9525
#: Tope de un desplazamiento o de un lado del gráfico, en píxeles (unas 60 pantallas de alto: ningún
#: gráfico real se le acerca). SUPUESTO_DECLARADO: elegido para acotar el cómputo, no sale de Excel.
TOPE_PX = 65_536
_TIPOS = {
    "barChart": "column",
    "bar3DChart": "column",
    "lineChart": "line",
    "line3DChart": "line",
    "areaChart": "area",
    "pieChart": "pie",
    "pie3DChart": "pie",
    "doughnutChart": "doughnut",
}
_SUBTIPOS = {"stacked": "stacked", "percentStacked": "percent_stacked"}
_LEYENDA = {"r": "right", "l": "left", "t": "top", "b": "bottom", "tr": "top_right"}


@dataclass(slots=True)
class Grafico:
    """Un gráfico listo para XlsxWriter, anclado en (fila, col) 1-based de su hoja."""

    tipo: str
    subtipo: str | None
    series: list[dict[str, Any]]
    titulo: str | None
    eje_x: str | None
    eje_y: str | None
    leyenda: str | None
    fila: int
    col: int
    x_offset: int = 0
    y_offset: int = 0
    hasta: tuple[int, int, int, int] | None = None  # (fila, col, dx, dy) del ancla final
    tamano: tuple[int, int] | None = None  # (ancho, alto) en píxeles si el ancla es de una celda
    hojas: set[str] = field(default_factory=set)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _hijos(el: Any, nombre: str) -> list[Any]:
    return [x for x in list(el) if _local(x.tag) == nombre]


def _hijo(el: Any, nombre: str) -> Any | None:
    return next((x for x in list(el) if _local(x.tag) == nombre), None)


def _buscar(el: Any, nombre: str) -> Any | None:
    return next((x for x in el.iter() if _local(x.tag) == nombre), None)


def _texto_rico(el: Any | None) -> str | None:
    if el is None:
        return None
    partes = [x.text or "" for x in el.iter() if _local(x.tag) == "t"]
    texto = "".join(partes).strip()
    return texto or None


def _ref(el: Any | None) -> str | None:
    if el is None:
        return None
    f = _buscar(el, "f")
    if f is not None and f.text:
        return "=" + f.text.strip()
    v = _buscar(el, "v")
    return v.text if v is not None and v.text else None


def _color(sppr: Any | None) -> str | None:
    if sppr is None:
        return None
    for hijo in list(sppr):
        if _local(hijo.tag) in ("solidFill",):
            rgb = _buscar(hijo, "srgbClr")
            if rgb is not None and rgb.get("val"):
                return "#" + rgb.get("val", "").upper()
    return None


def _hojas_de_ref(ref: str | None) -> set[str]:
    if not ref or not ref.startswith("="):
        return set()
    t = ref[1:]
    if "!" not in t:
        return set()
    hoja = t.split("!", 1)[0]
    if hoja.startswith("'"):
        hoja = hoja[1:-1].replace("''", "'")
    return {hoja}


def _grafico(xml: bytes) -> dict[str, Any] | None:
    from defusedxml import ElementTree

    raiz = ElementTree.fromstring(xml)
    chart = _buscar(raiz, "chart")
    plot = _buscar(raiz, "plotArea") if chart is not None else None
    if plot is None:
        return None
    nodo = next((x for x in list(plot) if _local(x.tag) in _TIPOS), None)
    if nodo is None:
        return None
    tipo = _TIPOS[_local(nodo.tag)]
    bar_dir = _hijo(nodo, "barDir")
    if tipo == "column" and bar_dir is not None and bar_dir.get("val") == "bar":
        tipo = "bar"
    agrup = _hijo(nodo, "grouping")
    subtipo = _SUBTIPOS.get(agrup.get("val", "")) if agrup is not None else None
    series: list[dict[str, Any]] = []
    hojas: set[str] = set()
    for ser in _hijos(nodo, "ser"):
        s: dict[str, Any] = {}
        nombre = _ref(_hijo(ser, "tx"))
        if nombre:
            s["name"] = nombre
        cat = _ref(_hijo(ser, "cat"))
        val = _ref(_hijo(ser, "val"))
        if val is None:
            continue
        if cat:
            s["categories"] = cat
        s["values"] = val
        color = _color(_hijo(ser, "spPr"))
        if color:
            s["line" if tipo == "line" else "fill"] = {"color": color}
        for r in (nombre, cat, val):
            hojas |= _hojas_de_ref(r)
        series.append(s)
    if not series:
        return None
    titulo = None
    t = _hijo(chart, "title") if chart is not None else None
    if t is not None:
        titulo = _texto_rico(t)
    ejes = {}
    for eje in ("catAx", "valAx"):
        e = _hijo(plot, eje)
        if e is not None:
            ejes[eje] = _texto_rico(_hijo(e, "title"))
    leyenda = None
    ley = _hijo(chart, "legend") if chart is not None else None
    if ley is None:
        leyenda = "none"
    else:
        pos = _hijo(ley, "legendPos")
        leyenda = _LEYENDA.get(pos.get("val", "r") if pos is not None else "r", "right")
    return {
        "tipo": tipo,
        "subtipo": subtipo,
        "series": series,
        "titulo": titulo,
        "eje_x": ejes.get("catAx"),
        "eje_y": ejes.get("valAx"),
        "leyenda": leyenda,
        "hojas": hojas,
    }


def _rels(zf: zipfile.ZipFile, ruta: str) -> dict[str, str]:
    from defusedxml import ElementTree

    base = posixpath.dirname(ruta)
    rel = posixpath.join(base, "_rels", posixpath.basename(ruta) + ".rels")
    if rel not in zf.namelist():
        return {}
    out = {}
    for el in ElementTree.fromstring(zf.read(rel)).iter():
        if _local(el.tag) == "Relationship" and el.get("TargetMode") != "External":
            destino = el.get("Target", "")
            if destino.startswith("/"):
                destino = destino[1:]
            else:
                destino = posixpath.normpath(posixpath.join(base, destino))
            out[el.get("Id", "")] = destino
    return out


def leer_graficos(datos: bytes) -> dict[str, list[Grafico]]:
    """Hoja → gráficos que tiene, leídos del `.xlsx` recibido. Lo ilegible se omite."""
    from defusedxml import ElementTree

    out: dict[str, list[Grafico]] = {}
    try:
        zf = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile:
        return out
    with zf:
        try:
            libro = ElementTree.fromstring(zf.read("xl/workbook.xml"))
        except Exception:  # libro dañado: sin gráficos
            return out
        rels_libro = _rels(zf, "xl/workbook.xml")
        for hoja in (x for x in libro.iter() if _local(x.tag) == "sheet"):
            rid = next((v for k, v in hoja.attrib.items() if k.endswith("}id")), None)
            ruta_hoja = rels_libro.get(rid or "")
            if not ruta_hoja:
                continue
            for ruta_dibujo in _rels(zf, ruta_hoja).values():
                if "/drawings/drawing" not in "/" + ruta_dibujo or not ruta_dibujo.endswith(".xml"):
                    continue
                try:
                    graficos = _de_dibujo(zf, ruta_dibujo)
                except Exception:  # dibujo ilegible: se omite (límite declarado)
                    continue
                if graficos:
                    out.setdefault(hoja.get("name", ""), []).extend(graficos)
    return out


def _de_dibujo(zf: zipfile.ZipFile, ruta: str) -> list[Grafico]:
    from defusedxml import ElementTree

    rels = _rels(zf, ruta)
    raiz = ElementTree.fromstring(zf.read(ruta))
    out: list[Grafico] = []
    for anc in list(raiz):
        tipo_anc = _local(anc.tag)
        if tipo_anc not in ("twoCellAnchor", "oneCellAnchor", "absoluteAnchor"):
            continue
        marco = _buscar(anc, "graphicFrame")
        cref = _buscar(marco, "chart") if marco is not None else None
        if cref is None:
            continue
        rid = next((v for k, v in cref.attrib.items() if k.endswith("}id")), None)
        ruta_graf = rels.get(rid or "")
        if not ruta_graf or ruta_graf not in zf.namelist():
            continue
        g = _grafico(zf.read(ruta_graf))
        if g is None:
            continue
        desde = _hijo(anc, "from")
        if desde is None:
            continue

        def num(el: Any, nombre: str, tope: int) -> int:
            """Entero del hijo `nombre`, acotado a [0, tope]."""
            x = _hijo(el, nombre)
            n = int(x.text) if x is not None and x.text else 0
            return min(max(n, 0), tope)

        def fila(el: Any) -> int:
            return num(el, "row", MAX_FILA - 1) + 1

        def col(el: Any) -> int:
            return num(el, "col", MAX_COL - 1) + 1

        def px(el: Any, nombre: str) -> int:
            return num(el, nombre, TOPE_PX * _EMU_PX) // _EMU_PX

        def lado(texto: str | None) -> int:
            n = int(texto) if texto else 0
            return min(max(n, 0), TOPE_PX * _EMU_PX) // _EMU_PX

        hasta = _hijo(anc, "to")
        ext = _hijo(anc, "ext")
        out.append(
            Grafico(
                tipo=g["tipo"],
                subtipo=g["subtipo"],
                series=g["series"],
                titulo=g["titulo"],
                eje_x=g["eje_x"],
                eje_y=g["eje_y"],
                leyenda=g["leyenda"],
                fila=fila(desde),
                col=col(desde),
                x_offset=px(desde, "colOff"),
                y_offset=px(desde, "rowOff"),
                hasta=(fila(hasta), col(hasta), px(hasta, "colOff"), px(hasta, "rowOff"))
                if hasta is not None
                else None,
                tamano=(lado(ext.get("cx")), lado(ext.get("cy"))) if ext is not None else None,
                hojas=g["hojas"],
            )
        )
    return out
