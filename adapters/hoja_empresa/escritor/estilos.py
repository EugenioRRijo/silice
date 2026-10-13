"""Estilos de celda: del libro recibido (openpyxl) al libro devuelto (XlsxWriter).

`Estilo` es inmutable y comparable, para que XlsxWriter cree un solo formato por combinación
(`a_xlsxwriter`). Los colores se guardan como 'RRGGBB'. Los colores de tema e indexados del libro se
resuelven contra el tema del propio libro (con su tinte), porque XlsxWriter solo acepta RGB.

Límites declarados: los rellenos degradados se pierden (quedan sin relleno), y los formatos
condicionales con barras, escalas o iconos no se copian (`copia`).
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass, replace
from typing import Any

__all__ = ["Estilo", "LectorEstilos", "color_hex"]

_BORDES = {
    "thin": 1,
    "medium": 2,
    "dashed": 3,
    "dotted": 4,
    "thick": 5,
    "double": 6,
    "hair": 7,
    "mediumDashed": 8,
    "dashDot": 9,
    "mediumDashDot": 10,
    "dashDotDot": 11,
    "mediumDashDotDot": 12,
    "slantDashDot": 13,
}
_PATRONES = {
    "solid": 1,
    "mediumGray": 2,
    "darkGray": 3,
    "lightGray": 4,
    "darkHorizontal": 5,
    "darkVertical": 6,
    "darkDown": 7,
    "darkUp": 8,
    "darkGrid": 9,
    "darkTrellis": 10,
    "lightHorizontal": 11,
    "lightVertical": 12,
    "lightDown": 13,
    "lightUp": 14,
    "lightGrid": 15,
    "lightTrellis": 16,
    "gray125": 17,
    "gray0625": 18,
}
_H = {
    "left": "left",
    "center": "center",
    "right": "right",
    "fill": "fill",
    "justify": "justify",
    "centerContinuous": "center_across",
    "distributed": "distributed",
}
_V = {
    "top": "top",
    "center": "vcenter",
    "bottom": "bottom",
    "justify": "vjustify",
    "distributed": "vdistributed",
}
_SUBRAYADO = {"single": 1, "double": 2, "singleAccounting": 33, "doubleAccounting": 34}

# Paleta indexada clásica de Excel (los 64 primeros índices).
_INDEXADOS = (
    "000000 FFFFFF FF0000 00FF00 0000FF FFFF00 FF00FF 00FFFF "
    "000000 FFFFFF FF0000 00FF00 0000FF FFFF00 FF00FF 00FFFF "
    "800000 008000 000080 808000 800080 008080 C0C0C0 808080 "
    "9999FF 993366 FFFFCC CCFFFF 660066 FF8080 0066CC CCCCFF "
    "000080 FF00FF FFFF00 00FFFF 800080 800000 008080 0000FF "
    "00CCFF CCFFFF CCFFCC FFFF99 99CCFF FF99CC CC99FF FFCC99 "
    "3366FF 33CCCC 99CC00 FFCC00 FF9900 FF6600 666699 969696 "
    "003366 339966 003300 333300 993300 993366 333399 333333"
).split()


def color_hex(texto: str | None) -> str | None:
    """'FF501C1C' o '501C1C' → '501C1C'; cualquier otra cosa → None."""
    if not isinstance(texto, str):
        return None
    t = texto.strip().lstrip("#").upper()
    if len(t) == 8:
        t = t[2:]
    if len(t) != 6 or any(ch not in "0123456789ABCDEF" for ch in t):
        return None
    return t


@dataclass(frozen=True, slots=True)
class Estilo:
    fuente: str | None = None
    tamano: float | None = None
    negrita: bool = False
    cursiva: bool = False
    subrayado: int = 0
    tachado: bool = False
    color: str | None = None
    indice: int = 0  # 1 superíndice, 2 subíndice
    patron: int = 0
    fondo: str | None = None
    fondo2: str | None = None
    bordes: tuple[tuple[int, str | None], ...] = ((0, None), (0, None), (0, None), (0, None))
    horizontal: str | None = None
    vertical: str | None = None
    ajuste: bool = False
    sangria: int = 0
    rotacion: int = 0
    reducir: bool = False
    formato: str | None = None
    bloqueada: bool = True
    oculta: bool = False

    def con(self, **cambios: Any) -> Estilo:
        return replace(self, **cambios)

    def a_xlsxwriter(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.fuente:
            d["font_name"] = self.fuente
        if self.tamano:
            d["font_size"] = self.tamano
        if self.negrita:
            d["bold"] = True
        if self.cursiva:
            d["italic"] = True
        if self.subrayado:
            d["underline"] = self.subrayado
        if self.tachado:
            d["font_strikeout"] = True
        if self.color:
            d["font_color"] = "#" + self.color
        if self.indice:
            d["font_script"] = self.indice
        if self.patron == 1 and self.fondo:
            d["pattern"] = 1
            d["bg_color"] = "#" + self.fondo
        elif self.patron > 1:
            d["pattern"] = self.patron
            if self.fondo:
                d["fg_color"] = "#" + self.fondo
            if self.fondo2:
                d["bg_color"] = "#" + self.fondo2
        for nombre, (tipo, color) in zip(
            ("left", "right", "top", "bottom"), self.bordes, strict=True
        ):
            if tipo:
                d[nombre] = tipo
                if color:
                    d[f"{nombre}_color"] = "#" + color
        if self.horizontal:
            d["align"] = self.horizontal
        if self.vertical:
            d["valign"] = self.vertical
        if self.ajuste:
            d["text_wrap"] = True
        if self.sangria:
            d["indent"] = self.sangria
        if self.rotacion:
            d["rotation"] = self.rotacion if self.rotacion <= 90 else 90 - self.rotacion
        if self.reducir:
            d["shrink"] = True
        if self.formato and self.formato != "General":
            d["num_format"] = self.formato
        if not self.bloqueada:
            d["locked"] = False
        if self.oculta:
            d["hidden"] = True
        return d


class LectorEstilos:
    """Convierte estilos de celdas openpyxl en `Estilo`, con caché por índice de estilo."""

    def __init__(self, tema: bytes | None) -> None:
        self._tema = _colores_tema(tema)
        self._cache: dict[tuple[int, ...], Estilo] = {}

    def color(self, c: Any) -> str | None:
        """Un `openpyxl.styles.colors.Color` → 'RRGGBB' (o None si es automático)."""
        if c is None:
            return None
        tipo = getattr(c, "type", None)
        if tipo == "rgb":
            return color_hex(c.rgb if isinstance(c.rgb, str) else None)
        if tipo == "theme":
            base = self._tema.get(int(c.theme))
            if base is None:
                return None
            return _tinte(base, float(c.tint or 0))
        if tipo == "indexed":
            i = int(c.indexed)
            if 0 <= i < len(_INDEXADOS):
                return _INDEXADOS[i]
            return None
        return None

    def de_celda(self, celda: Any) -> Estilo:
        clave = tuple(getattr(celda, "_style", ()) or ())
        if clave and clave in self._cache:
            return self._cache[clave]
        e = self._construir(celda)
        if clave:
            self._cache[clave] = e
        return e

    def _construir(self, celda: Any) -> Estilo:
        f = celda.font
        fill = celda.fill
        b = celda.border
        a = celda.alignment
        p = celda.protection
        patron = 0
        fondo = fondo2 = None
        tipo_relleno = getattr(fill, "fill_type", None) or getattr(fill, "patternType", None)
        if tipo_relleno in _PATRONES:
            patron = _PATRONES[tipo_relleno]
            fondo = self.color(getattr(fill, "fgColor", None))
            fondo2 = self.color(getattr(fill, "bgColor", None))
            if patron == 1 and fondo is None:
                patron = 0
        bordes = []
        for lado in (b.left, b.right, b.top, b.bottom):
            estilo_b = getattr(lado, "style", None) if lado is not None else None
            tipo_b = _BORDES.get(estilo_b or "", 0)
            bordes.append((tipo_b, self.color(lado.color) if tipo_b and lado is not None else None))
        vert = getattr(f, "vertAlign", None)
        rot = int(getattr(a, "textRotation", 0) or 0)
        return Estilo(
            fuente=f.name,
            tamano=float(f.sz) if f.sz else None,
            negrita=bool(f.b),
            cursiva=bool(f.i),
            subrayado=_SUBRAYADO.get(f.u or "", 0),
            tachado=bool(f.strike),
            color=self.color(f.color),
            indice=1 if vert == "superscript" else 2 if vert == "subscript" else 0,
            patron=patron,
            fondo=fondo,
            fondo2=fondo2,
            bordes=tuple(bordes),
            horizontal=_H.get(a.horizontal or ""),
            vertical=_V.get(a.vertical or ""),
            ajuste=bool(a.wrap_text),
            sangria=int(a.indent or 0),
            rotacion=rot if rot <= 180 else 0,
            reducir=bool(a.shrink_to_fit),
            formato=celda.number_format,
            bloqueada=True if p is None or p.locked is None else bool(p.locked),
            oculta=bool(p.hidden) if p is not None else False,
        )


def _colores_tema(tema: bytes | None) -> dict[int, str]:
    """Índice de color de tema (como lo usa SpreadsheetML) → 'RRGGBB'.

    En el XML el orden es dk1, lt1, dk2, lt2, accent1…6, hlink, folHlink; Excel numera 0 = lt1,
    1 = dk1, 2 = lt2, 3 = dk2 y desde 4 en el orden del XML.
    """
    if not tema:
        return {}
    from defusedxml import ElementTree

    try:
        raiz = ElementTree.fromstring(tema)
    except Exception:  # tema dañado: se ignoran sus colores
        return {}
    esquema = next((el for el in raiz.iter() if el.tag.endswith("}clrScheme")), None)
    if esquema is None:
        return {}
    colores: list[str] = []
    for hijo in list(esquema):
        valor = None
        for el in hijo.iter():
            if el.tag.endswith("}srgbClr"):
                valor = el.get("val")
                break
            if el.tag.endswith("}sysClr"):
                valor = el.get("lastClr")
                break
        colores.append(color_hex(valor) or "000000")
    if len(colores) < 4:
        return {}
    orden = [colores[1], colores[0], colores[3], colores[2], *colores[4:]]
    return dict(enumerate(orden))


def _tinte(rgb: str, tinte: float) -> str:
    if not tinte:
        return rgb
    r, g, b = (int(rgb[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, lum, s = colorsys.rgb_to_hls(r, g, b)
    lum = lum * (1 + tinte) if tinte < 0 else lum * (1 - tinte) + tinte
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, lum)), s)
    return "".join(f"{round(x * 255):02X}" for x in (r, g, b))
