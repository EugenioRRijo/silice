"""Réplica visual del libro de la empresa: `.xlsx` → `LibroVisual` (Sílice 1.2.0, RF-111, RS2-1).

El visor de solo lectura (Univer) dibuja el libro **tal como se ve en Excel**. Este módulo
extrae solo el **aspecto**: relleno, fuente, bordes, alineación, formato numérico, combinadas,
anchos, altos, filas y columnas ocultas, paneles fijos, y por celda el valor mostrado y su fórmula.
No hay un segundo parser (RT-6): las fórmulas y los valores guardados se leen con las mismas piezas
que `lector.py` (`_abrir`, `_celdas_reales`, `_convertir`, `_texto_formula`) y la paleta indexada y
el lector del tema de `escritor/estilos.py` (`_INDEXADOS`, `_colores_tema`).

Contrato neutro (RS2-1): coordenadas de Excel, fila y columna **base 1**, `ref` sin `$`. La
conversión a la instantánea de Univer (base 0, píxeles) ocurre en un solo lugar del frontend
(`frontend-desktop/src/replica/aUniver.ts`). Los números van como texto decimal
(`Decimal(str(v))` con `format(d, "f")`), nunca como `float`.

Aperturas del libro (siempre después de la guardia, F-D10, y sin escribir nunca sobre el original):

1. **Modo normal** (`data_only=False`): única forma en que openpyxl da estilos, combinadas, anchos
   y altos. Es la apertura cara (~7 s en un libro real de 35 hojas, costo declarado en RT-6).
2. **Solo lectura con `data_only=True`**, y solo para las hojas que tienen fórmulas: el valor
   guardado (calculado por Excel) de cada celda con fórmula. Las celdas sin fórmula toman su
   valor de la primera apertura.

Límites declarados:

- **Temas:** los colores de tema (`theme`) salen del tema propio del libro
  (`xl/theme/theme1.xml`, `wb.loaded_theme`, leído con `escritor.estilos._colores_tema`). Si el
  tema falta o es ilegible se usa la paleta de Office por omisión (2013 en adelante,
  `_TEMA_OFFICE`), y los índices que el tema no trae se completan con ella.
- **Tinte (`tint`):** se aplica según ECMA-376 §18.8.19 en HSL con aritmética de coma flotante;
  Excel usa enteros y puede diferir en 1 de 255 en un canal. El empate de redondeo (x,5) va hacia
  abajo, como Excel (blanco más oscuro 50 % = #7F7F7F). Por eso se conservan `_canal`/`_con_tinte`
  y no se usa `LectorEstilos`: su `_tinte` redondea con `round()` (el 127,5 va al par, 128) y
  daría #808080.
- **Rellenos:** solo los sólidos (`solid`). Tramas (`lightGray`...) y degradados se muestran sin
  relleno.
- **Bordes:** solo el estilo de cada lado; el color del borde no viaja. Los estilos que el
  contrato no nombra se acercan al más parecido (`mediumDashed`, `dashDot`, `slantDashDot`... →
  `dashed`).
- **Alineación:** `centerContinuous` → `center`, `distributed` → `justify`; `fill` y la vertical
  `justify`/`distributed` → sin dato (`None`).
- **Estilos condicionales, validaciones, imágenes, gráficos, comentarios y hojas de gráfico:** no se
  replican (las hojas de gráfico no aparecen en `hojas`).
- **Celdas con fórmula nunca calculadas** (libro sin valor guardado): `mostrado == ""`.
- **Ancho de columna:** el que declara el archivo (`width` de `<col>`); un `<col>` sin ancho vale
  lo que openpyxl asume (13). Los rangos `min..max` se reparten columna por columna. Se omite el
  ancho por omisión de Excel (8,43) y el alto por omisión (15 pt). Los anchos y altos de 0 no se
  escriben (la columna o fila oculta va en `ocultas_*`).
- **Tope:** más de `MAX_CELDAS_VISUALES` celdas con valor o estilo en todo el libro →
  `LibroDemasiadoGrande`.

Deuda: `_abrir_normal` repite lo que hace `lector._abrir` (mismos avisos silenciados, mismo
`ArchivoRechazado`); falta un parámetro `solo_lectura` en `lector._abrir`, pero `lector.py` no se
toca en esta sesión (ruta, sesión 2).
"""

from __future__ import annotations

import colorsys
import hashlib
import io
import math
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from openpyxl.cell.cell import Cell
from openpyxl.utils.cell import column_index_from_string, get_column_letter

from adapters.hoja_empresa.escritor.estilos import _INDEXADOS, _colores_tema
from adapters.hoja_empresa.guardia import ArchivoRechazado, verificar_archivo
from adapters.hoja_empresa.lector import _abrir, _celdas_reales, _convertir, _texto_formula

__all__ = [
    "MAX_CELDAS_VISUALES",
    "CeldaVisual",
    "EstiloVisual",
    "HojaVisual",
    "LibroDemasiadoGrande",
    "LibroVisual",
    "replicar_libro",
]

#: Celdas con valor o estilo que `replicar_libro` acepta en todo el libro. Un libro real de la
#: empresa declara a lo sumo 2 548 celdas en su hoja mayor (medido en la guardia, 2026-10-13), o sea
#: unas 90 000 en 35 hojas; 200 000 deja más del doble de margen y acota el tamaño de la respuesta
#: de la API y el trabajo del lienzo. SUPUESTO_DECLARADO.
MAX_CELDAS_VISUALES = 200_000

_ANCHO_POR_OMISION = Decimal("8.43")
_ALTO_POR_OMISION = Decimal("15")
_MAX_COLUMNA = 16384  # XFD

# --- Colores -------------------------------------------------------------------------------------

#: Índices `indexed` de sistema (los 64 primeros son `escritor.estilos._INDEXADOS`, ECMA-376
#: §18.8.27): 64 = color de primer plano (negro), 65 = color de fondo (blanco).
_SISTEMA = {64: "000000", 65: "FFFFFF"}
#: Paleta de tema de Office por omisión (2013 en adelante), en el orden de índices de `theme` de
#: SpreadsheetML: 0 lt1, 1 dk1, 2 lt2, 3 dk2 (los dos pares van intercambiados respecto de
#: `<a:clrScheme>`), 4-9 accent1-6, 10 hlink, 11 folHlink. Solo es el respaldo del tema del libro.
_TEMA_OFFICE: dict[int, str] = dict(
    enumerate(
        (
            "FFFFFF",
            "000000",
            "E7E6E6",
            "44546A",
            "4472C4",
            "ED7D31",
            "A5A5A5",
            "FFC000",
            "5B9BD5",
            "70AD47",
            "0563C1",
            "954F72",
        )  # fmt: skip
    )
)
_HEX = frozenset("0123456789abcdefABCDEF")


def _canal(x: float) -> int:
    """Canal 0..1 → 0..255 con el empate (x,5) hacia abajo, como Excel."""
    return min(255, max(0, math.ceil(x * 255 - 0.5)))


def _con_tinte(hexa: str, tinte: float) -> str:
    """Aplica `tint` (ECMA-376 §18.8.19): luminosidad HSL; < 0 oscurece, > 0 aclara."""
    r, g, b = (int(hexa[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, luz, s = colorsys.rgb_to_hls(r, g, b)
    luz = luz * (1 + tinte) if tinte < 0 else luz * (1 - tinte) + tinte
    rr, gg, bb = colorsys.hls_to_rgb(h, min(1.0, max(0.0, luz)), s)
    return f"{_canal(rr):02X}{_canal(gg):02X}{_canal(bb):02X}"


def _color(c: Any, tema: Mapping[int, str]) -> str | None:
    """Un `Color` de openpyxl → `#RRGGBB`, o `None` (sin color, automático o ilegible)."""
    if c is None:
        return None
    tipo = getattr(c, "type", None)
    base: str | None = None
    if tipo == "rgb":
        v = getattr(c, "rgb", None)
        if isinstance(v, str) and len(v) in (6, 8) and set(v) <= _HEX:
            base = v[-6:].upper()
    elif tipo == "indexed":
        i = getattr(c, "indexed", None)
        if isinstance(i, int):
            base = _INDEXADOS[i] if 0 <= i < len(_INDEXADOS) else _SISTEMA.get(i)
    elif tipo == "theme":
        i = getattr(c, "theme", None)
        if isinstance(i, int):
            base = tema.get(i)
    if base is None:
        return None
    tinte = getattr(c, "tint", 0.0)
    if isinstance(tinte, (int, float)) and math.isfinite(tinte) and tinte:
        base = _con_tinte(base, float(tinte))
    return f"#{base}"


# --- Contrato ------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EstiloVisual:
    """Aspecto de una celda. Se deduplica: las celdas apuntan a un índice de
    `LibroVisual.estilos`."""

    relleno: str | None  # "#RRGGBB" o None (sin relleno)
    fuente: str | None  # nombre, p. ej. "Arial"
    tamano: str | None  # puntos como texto decimal, "10" / "10.5"
    negrita: bool
    cursiva: bool
    subrayado: bool
    color: str | None  # "#RRGGBB"
    alineacion_h: str | None  # "left" | "center" | "right" | "justify" | None (general)
    alineacion_v: str | None  # "top" | "center" | "bottom" | None
    ajustar_texto: bool
    formato_numero: str  # el código de Excel tal cual, "General" por omisión
    # arriba, derecha, abajo, izquierda; cada uno: thin | medium | thick | double | dashed |
    # dotted | hair | None
    bordes: tuple[str | None, str | None, str | None, str | None]


@dataclass(frozen=True, slots=True)
class CeldaVisual:
    ref: str  # "F12", sin $
    fila: int  # base 1
    columna: int  # base 1
    mostrado: str  # valor guardado como texto (Decimal en "f", fecha ISO, texto); "" si vacío
    formula: str | None  # "=F11*E12" si la celda tiene fórmula
    estilo: int  # índice en LibroVisual.estilos


@dataclass(frozen=True, slots=True)
class HojaVisual:
    nombre: str
    visible: bool  # False si hidden o veryHidden
    filas: int  # fila máxima usada (0 si la hoja no tiene celdas)
    columnas: int  # columna máxima usada (0 si la hoja no tiene celdas)
    anchos: Mapping[int, str]  # columna base 1 → ancho en caracteres de Excel, texto decimal
    altos: Mapping[int, str]  # fila base 1 → alto en puntos, texto decimal
    ocultas_filas: tuple[int, ...]
    ocultas_columnas: tuple[int, ...]
    combinadas: tuple[str, ...]  # "A1:D1"
    fijas: str | None  # celda de los paneles congelados, "B5"
    celdas: tuple[CeldaVisual, ...]  # solo las que tienen valor o estilo distinto del por omisión


@dataclass(frozen=True, slots=True)
class LibroVisual:
    nombre: str
    sha256: str
    hojas: tuple[HojaVisual, ...]  # en el orden del libro
    estilos: tuple[EstiloVisual, ...]


class LibroDemasiadoGrande(ArchivoRechazado):
    """El libro tiene más de `MAX_CELDAS_VISUALES` celdas con valor o estilo."""


# --- Extracción ----------------------------------------------------------------------------------

_BORDES = {
    "thin": "thin",
    "medium": "medium",
    "thick": "thick",
    "double": "double",
    "dashed": "dashed",
    "dotted": "dotted",
    "hair": "hair",
    "mediumDashed": "dashed",
    "dashDot": "dashed",
    "mediumDashDot": "dashed",
    "dashDotDot": "dashed",
    "mediumDashDotDot": "dashed",
    "slantDashDot": "dashed",
}
_ALINEACION_H = {
    "left": "left",
    "center": "center",
    "right": "right",
    "justify": "justify",
    "centerContinuous": "center",
    "distributed": "justify",
}
_ALINEACION_V = {"top": "top", "center": "center", "bottom": "bottom"}
_LADOS = ("top", "right", "bottom", "left")  # el orden del contrato: arriba, derecha, abajo, izq.
_SUBRAYADOS = frozenset({"single", "double", "singleAccounting", "doubleAccounting"})


def _decimal_texto(v: object) -> str:
    """Número de la hoja (ancho, alto, tamaño) → texto decimal sin ceros sobrantes: 20.0 → "20"."""
    return format(Decimal(str(v)).normalize(), "f")


def _mostrado(v: object) -> str:
    """Valor guardado ya convertido (`lector._convertir`) → texto mostrado."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, Decimal):
        return format(v, "f")
    return v if isinstance(v, str) else str(v)


def _estilo_de(celda: Any, tema: Mapping[int, str]) -> EstiloVisual:
    f, fondo, bd, al = celda.font, celda.fill, celda.border, celda.alignment
    relleno = _color(fondo.fgColor, tema) if getattr(fondo, "fill_type", None) == "solid" else None
    tamano = f.sz
    return EstiloVisual(
        relleno=relleno,
        fuente=f.name or None,
        tamano=_decimal_texto(tamano) if tamano is not None else None,
        negrita=bool(f.b),
        cursiva=bool(f.i),
        subrayado=f.u in _SUBRAYADOS,
        color=_color(f.color, tema),
        alineacion_h=_ALINEACION_H.get(al.horizontal),
        alineacion_v=_ALINEACION_V.get(al.vertical),
        ajustar_texto=bool(al.wrap_text),
        formato_numero=celda.number_format or "General",
        bordes=tuple(_BORDES.get(getattr(getattr(bd, lado), "style", None)) for lado in _LADOS),  # type: ignore[arg-type]
    )


class _Estilos:
    """Registro de estilos deduplicados, con caché por `style_id` de openpyxl."""

    def __init__(self, tema: Mapping[int, str], defecto: EstiloVisual) -> None:
        self.tema = tema
        self.defecto = defecto
        self.lista: list[EstiloVisual] = []
        self._indice: dict[EstiloVisual, int] = {}
        self._por_id: dict[int, EstiloVisual] = {}

    def de(self, celda: Any) -> EstiloVisual:
        sid = celda.style_id
        e = self._por_id.get(sid)
        if e is None:
            e = self._por_id[sid] = _estilo_de(celda, self.tema)
        return e

    def indice(self, e: EstiloVisual) -> int:
        i = self._indice.get(e)
        if i is None:
            i = self._indice[e] = len(self.lista)
            self.lista.append(e)
        return i


def _abrir_normal(datos: bytes, nombre: str) -> Any:
    import openpyxl

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return openpyxl.load_workbook(
                io.BytesIO(datos), data_only=False, keep_vba=False, keep_links=False
            )
    except Exception as exc:  # openpyxl lanza tipos muy variados ante un XML dañado
        raise ArchivoRechazado(
            f"No se pudo abrir el libro «{nombre}»: el archivo .xlsx está dañado o no es de Excel."
        ) from exc


def _anchos(ws: Any) -> dict[int, str]:
    out: dict[int, str] = {}
    for letra, cd in ws.column_dimensions.items():
        if cd.width is None or cd.width <= 0:
            continue
        ancho = Decimal(str(cd.width))
        if ancho == _ANCHO_POR_OMISION:
            continue
        desde = cd.min or column_index_from_string(letra)
        hasta = min(cd.max or desde, _MAX_COLUMNA)
        for col in range(desde, hasta + 1):
            out[col] = _decimal_texto(cd.width)
    return dict(sorted(out.items()))


def _columnas_ocultas(ws: Any) -> tuple[int, ...]:
    out: set[int] = set()
    for letra, cd in ws.column_dimensions.items():
        if cd.hidden:
            desde = cd.min or column_index_from_string(letra)
            out.update(range(desde, min(cd.max or desde, _MAX_COLUMNA) + 1))
    return tuple(sorted(out))


def _filas(ws: Any) -> tuple[dict[int, str], tuple[int, ...]]:
    altos: dict[int, str] = {}
    ocultas: list[int] = []
    for fila, rd in ws.row_dimensions.items():
        if rd.hidden:
            ocultas.append(fila)
        if rd.height is not None and rd.height > 0 and Decimal(str(rd.height)) != _ALTO_POR_OMISION:
            altos[fila] = _decimal_texto(rd.height)
    return dict(sorted(altos.items())), tuple(sorted(ocultas))


def _combinadas(ws: Any) -> tuple[str, ...]:
    rangos = sorted(
        ws.merged_cells.ranges, key=lambda r: (r.min_row, r.min_col, r.max_row, r.max_col)
    )
    return tuple(r.coord for r in rangos)


def _valores_guardados(wv: Any, titulo: str) -> dict[tuple[int, int], object]:
    return {(c.row, c.column): c.value for c in _celdas_reales(wv[titulo])}


def _hoja(ws: Any, wv: Any, estilos: _Estilos, usadas: int) -> tuple[HojaVisual, int]:
    """Réplica de una hoja; `usadas` son las celdas ya aceptadas en las hojas anteriores."""
    celdas_ws = ws._cells  # noqa: SLF001 - solo las celdas que existen; iter_rows las inventaría
    items = sorted(celdas_ws.items())
    con_formula = any(_texto_formula(c) is not None for _, c in items)
    guardados = _valores_guardados(wv, ws.title) if con_formula else {}
    celdas: list[CeldaVisual] = []
    for (fila, col), c in items:
        formula = _texto_formula(c)
        valor = _convertir(guardados.get((fila, col)) if formula else c.value)
        estilo = estilos.de(c)
        if formula is None and c.value is None and estilo == estilos.defecto:
            continue
        usadas += 1
        if usadas > MAX_CELDAS_VISUALES:
            tope = f"{MAX_CELDAS_VISUALES:,}".replace(",", ".")
            raise LibroDemasiadoGrande(
                f"El libro tiene más de {tope} celdas con valor o formato; es demasiado grande "
                "para mostrarlo en el visor."
            )
        celdas.append(
            CeldaVisual(
                ref=f"{get_column_letter(col)}{fila}",
                fila=fila,
                columna=col,
                mostrado=_mostrado(valor),
                formula=formula,
                estilo=estilos.indice(estilo),
            )
        )
    altos, ocultas_filas = _filas(ws)
    return (
        HojaVisual(
            nombre=ws.title,
            visible=ws.sheet_state == "visible",
            filas=ws.max_row if celdas_ws else 0,
            columnas=ws.max_column if celdas_ws else 0,
            anchos=_anchos(ws),
            altos=altos,
            ocultas_filas=ocultas_filas,
            ocultas_columnas=_columnas_ocultas(ws),
            combinadas=_combinadas(ws),
            fijas=ws.freeze_panes or None,
            celdas=tuple(celdas),
        ),
        usadas,
    )


# --- Entrada pública -----------------------------------------------------------------------------


def replicar_libro(datos: bytes, nombre: str) -> LibroVisual:
    """Réplica visual del libro `.xlsx` (aspecto, valores mostrados y fórmulas), con coordenadas de
    Excel (base 1).

    Pasa primero por la guardia (`ArchivoRechazado`); después hace una apertura en modo normal y,
    si hay fórmulas, otra de solo lectura con los valores guardados. Lanza `LibroDemasiadoGrande`
    si el libro supera `MAX_CELDAS_VISUALES` celdas. Nunca modifica `datos`.
    """
    verificar_archivo(datos, nombre)
    sha = hashlib.sha256(datos).hexdigest()
    wb = _abrir_normal(datos, nombre)
    try:
        wv = _abrir(datos, nombre, data_only=True)
        try:
            hojas_ws = list(wb.worksheets)
            if not hojas_ws:
                return LibroVisual(nombre=nombre, sha256=sha, hojas=(), estilos=())
            # El tema propio del libro manda; lo que no trae se completa con el de Office.
            tema = {**_TEMA_OFFICE, **_colores_tema(wb.loaded_theme)}
            defecto = _estilo_de(Cell(hojas_ws[0], row=1, column=1), tema)
            estilos = _Estilos(tema, defecto)
            hojas: list[HojaVisual] = []
            usadas = 0
            for ws in hojas_ws:
                h, usadas = _hoja(ws, wv, estilos, usadas)
                hojas.append(h)
        except ArchivoRechazado:
            raise
        except Exception as exc:
            raise ArchivoRechazado(
                f"No se pudo leer el libro «{nombre}»: alguna hoja está dañada."
            ) from exc
        finally:
            wv.close()
    finally:
        wb.close()
    return LibroVisual(nombre=nombre, sha256=sha, hojas=tuple(hojas), estilos=tuple(estilos.lista))
