"""Aceptación de Silice 1.5 sobre los libros reales de la empresa (spec 1.5 §7).

Por qué existe: la 1.5 se construye sin pruebas nuevas (regla del 2026-10-12) y los libros reales
son confidenciales, así que no pueden ser casos de la suite. Este script es la herramienta de
aceptación que se corre A MANO, en el equipo que tiene los libros, contra la carpeta local donde
están (por ejemplo `docs/auditoria/`, ignorada por Git). No es una prueba de pytest y no corre en
la CI.

Qué comprueba, como metas OK/FALLA con su evidencia:

1. **Hallazgos esperados** (tabla del spec §7 y cifras de las causas raíz H1-H18): para cada libro,
   `fusion.proceso.procesar_libro` debe producir la regla esperada en la celda esperada, con la
   severidad y el impacto documentados.
2. **Valores de Silice**: en A, B-1 y B-2 (cuyo PRESUPUESTO cuadra con sus APU) el P.U. de Silice
   es el P guardado de cada partida; los totales de Silice son coherentes y, donde hay cifra
   documentada, iguales a ella (en C-2, el subtotal entregado más los 205,92 de H1).
3. **Devolución**: el libro devuelto (`devolver`) se escribe en `--salida` y se REABRE con openpyxl:
   sin `#REF!`, sin `INDIRECT`, sin vínculos ni nombres rotos, con un valor guardado en cada
   fórmula, con P y totales iguales a los de Silice, con las hojas AUDITORÍA, TRAZABILIDAD y
   ALERTAS USD-Bs, con el rótulo de P.U. en la misma celda en todos los APU y con la huella
   SHA-256 del libro recibido en sus propiedades.
4. **PDF simples** (001 y 002), por `fusion.proceso.auditar_pdf_simple`: la regla L10 con los
   subtipos esperados.

Por qué los oráculos no salen de Silice: lo esperado viene de un literal documentado (las cifras
de `docs/auditoria/2026-10-13-causas-raiz-libros-arenaza.md`) o de leer el libro RECIBIDO con
openpyxl, aparte del lector del adaptador (celdas con `#REF!`, nombres con vínculo externo, P
guardado, números de partida). Comparar Silice contra Silice no demostraría nada.

Cómo identifica cada libro sin escribir nombres de clientes en el código: si la carpeta tiene un
`expectativas.json` (local, fuera del repositorio) se usa ese; si no, por su contenido: número de
APU y de partidas y subtotal guardado (`FIRMAS`). C-1 y C-2 tienen el mismo subtotal; C-1 es el
que tiene dos APU que reclaman la misma fila (conflicto L2). El PDF de cada libro es el que
comparte nombre base con el `.xlsx`; para C-2 se cotejan además (L11) los PDF cuyos totales
impresos coinciden. Nada de lo que imprime lleva nombres de archivo ni de clientes: los libros se
llaman "Libro A", "Libro B-1"… y toda evidencia pasa por un filtro que borra los nombres reales.

Formato de `expectativas.json` (opcional)::

    {"libros": {"<archivo>.xlsx": "A",
                "<otro>.xlsx": {"etiqueta": "C-2", "pdf": ["<impreso>.pdf"]}}}

Uso::

    uv run python scripts/fusion_verificar.py CARPETA [--salida DIR] [--json]
        [--fecha-libro 2026-07-31] [--fecha-devolucion AAAA-MM-DD] [--pdf-simple RUTA ...]

Código de salida: 0 si todas las metas están en OK, 1 si alguna falla, 2 si no se pudo correr
(falta `fusion.proceso` o la carpeta no existe).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import traceback
import unicodedata
import zipfile
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import openpyxl
from defusedxml.ElementTree import fromstring as leer_xml

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado, Fila, _filas_a_json, render_tabla  # noqa: E402

#: Fecha de los libros (PORTADA "Julio 2026" -> último día del mes, spec F-D8). Se pasa explícita
#: para que la corrida no dependa de cómo el lector interprete la portada.
FECHA_LIBRO = date(2026, 7, 31)
SALIDA_POR_DEFECTO = RAIZ / "data" / "confidencial" / "devoluciones"
PDF_SIMPLES = (
    RAIZ / "data" / "samples" / "telecom" / "Presupuesto_1_ARENAZA.pdf",
    RAIZ / "data" / "samples" / "telecom" / "Presupuesto_2_ARENAZA.pdf",
)

#: Tolerancias explícitas: medio céntimo por celda (la unidad impresa es el céntimo), un céntimo
#: para totales que suman redondeos y 0,05 para impactos documentados con dos decimales a partir
#: de valores redondeados (H1: 1,82565 x 100,53 x 1,10 x 1,02).
TOL_CELDA = Decimal("0.005")
TOL_CENTIMO = Decimal("0.01")
TOL_IMPACTO = Decimal("0.05")

HOJAS_NUEVAS = ("AUDITORÍA", "TRAZABILIDAD", "ALERTAS USD-Bs")
ROTULO_PU = "PRECIO UNITARIO TOTAL"
PROPIEDAD_SHA = "silice_sha256_origen"
NOMBRES_TOTALES = ("SUBSINIVA", "IVATOT", "TOTALGEN")
NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

_RE_REF = re.compile(r"^\$?([A-Z]{1,3})\$?(\d+)")
_RE_DIV12 = re.compile(r"/\s*12(?!\d)")
_RE_TITULO_APU = re.compile(r"PRESUPUESTO'?!\$?[A-Z]{1,3}\$?(\d+)", re.IGNORECASE)
_RE_VINCULO_FORMULA = re.compile(r"\[\d+\]")
_RE_REF_PURA = re.compile(r"^=?\+?(?:'?([^'!]+)'?!)?\$?([A-Z]{1,3})\$?(\d+)$")


# --- Identificación de los libros -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Firma:
    """Lo que distingue a un libro por su contenido (causas raíz, tabla de alcance)."""

    etiqueta: str
    partidas: int
    subtotal: Decimal
    apus: int | None = None
    conflicto_apu: bool | None = None


FIRMAS: tuple[Firma, ...] = (
    Firma("A", 5, Decimal("9955.65"), apus=5),
    Firma("B-1", 16, Decimal("12917.54")),
    Firma("B-2", 16, Decimal("16491.80")),
    Firma("C-1", 9, Decimal("24311.92"), conflicto_apu=True),
    Firma("C-2", 9, Decimal("24311.92"), conflicto_apu=False),
)
ETIQUETAS: tuple[str, ...] = tuple(f.etiqueta for f in FIRMAS)

#: Versión anterior del mismo libro, para las alertas "contra otra versión" (spec §4.3).
OTRA_VERSION: dict[str, str] = {"B-2": "B-1", "C-2": "C-1"}

#: Subtotal sin IVA documentado de lo entregado (causas raíz, tabla de alcance). En C-2, Silice
#: corrige H1 (F-D7) y conserva la utilidad del 2 % (H2): 24 311,92 + 205,92 = 24 517,85
#: (memoria: 1,82565 x 100,53 = 183,5326; x 1,10 x 1,02 = 205,9236; 24 311,9242 + 205,9236).
SUBTOTAL_SILICE: dict[str, tuple[Decimal, Decimal]] = {
    "A": (Decimal("9955.65"), TOL_CELDA + Decimal("0.001")),
    "B-1": (Decimal("12917.54"), TOL_CELDA + Decimal("0.001")),
    "B-2": (Decimal("16491.80"), TOL_CELDA + Decimal("0.001")),
    "C-2": (Decimal("24517.85"), TOL_IMPACTO),
}


@dataclass(slots=True)
class Caso:
    """Un libro de la carpeta ya identificado."""

    etiqueta: str
    ruta: Path
    datos: bytes
    como: str  # "expectativas.json" o "contenido"
    pdf: Path | None = None
    pdf_extra: list[Path] = field(default_factory=list)


def _norm(texto: object) -> str:
    """Mayúsculas, sin acentos, sin NBSP y con espacios simples: para comparar rótulos y hojas."""
    plano = unicodedata.normalize("NFKD", str(texto).replace("\xa0", " "))
    sin_acentos = "".join(c for c in plano if not unicodedata.combining(c))
    return " ".join(sin_acentos.upper().split())


def _dec(valor: object) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, int | float):
        return Decimal(str(valor))
    try:
        return Decimal(str(valor).strip())
    except (InvalidOperation, ValueError):
        return None


def _fmt(valor: Decimal | None, decimales: int = 2) -> str:
    if valor is None:
        return "-"
    return f"{valor:.{decimales}f}"


def _cerca(a: Decimal | None, b: Decimal | None, tol: Decimal) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def _firma_de(libro: Any) -> tuple[int, int, Decimal | None, bool]:
    subtotal = _dec(libro.totales.get("SUBSINIVA"))
    filas = Counter(a.fila_presupuesto for a in libro.apus if a.fila_presupuesto is not None)
    conflicto = any(n > 1 for n in filas.values())
    centimos = subtotal.quantize(Decimal("0.01")) if subtotal is not None else None
    return len(libro.apus), len(libro.partidas), centimos, conflicto


def _identificar(libro: Any) -> str | None:
    apus, partidas, subtotal, conflicto = _firma_de(libro)
    for f in FIRMAS:
        if f.partidas != partidas or subtotal != f.subtotal:
            continue
        if f.apus is not None and f.apus != apus:
            continue
        if f.conflicto_apu is not None and f.conflicto_apu != conflicto:
            continue
        return f.etiqueta
    return None


def _leer_expectativas(carpeta: Path) -> dict[str, tuple[str, list[str]]]:
    ruta = carpeta / "expectativas.json"
    if not ruta.is_file():
        return {}
    crudo = json.loads(ruta.read_text(encoding="utf-8"))
    libros = crudo.get("libros", crudo) if isinstance(crudo, dict) else {}
    salida: dict[str, tuple[str, list[str]]] = {}
    for archivo, valor in libros.items():
        if isinstance(valor, str):
            etiqueta, pdfs = valor, []
        else:
            etiqueta = str(valor.get("etiqueta", ""))
            pdf = valor.get("pdf", [])
            pdfs = [pdf] if isinstance(pdf, str) else list(pdf)
        if etiqueta not in ETIQUETAS:
            raise ValueError(f"expectativas.json: etiqueta desconocida {etiqueta!r}")
        salida[archivo.lower()] = (etiqueta, pdfs)
    return salida


# --- Hallazgos: dónde y cuánto --------------------------------------------------------------------


def _celda_de(origen: str) -> tuple[str, str] | None:
    """`HOJA!CELDA` -> (HOJA normalizada, CELDA sin `$`). None si el origen no es una celda."""
    if origen.startswith("PDF:") or "!" not in origen:
        return None
    hoja, ref = origen.rsplit("!", 1)
    return _norm(hoja.strip().strip("'")), ref.replace("$", "").strip().upper()


def _fila_de(ref: str) -> int | None:
    m = _RE_REF.match(ref)
    return int(m.group(2)) if m else None


def _celdas(h: Any) -> set[tuple[str, str]]:
    return {c for o in h.origen_ids if (c := _celda_de(str(o))) is not None}


def _de(hallazgos: Iterable[Any], regla: str, severidad: str | None = None) -> list[Any]:
    return [
        h
        for h in hallazgos
        if h.regla == regla and (severidad is None or h.severidad.name == severidad)
    ]


def _en_hoja(hallazgos: Iterable[Any], hoja: str) -> list[Any]:
    objetivo = _norm(hoja)
    return [h for h in hallazgos if any(c[0] == objetivo for c in _celdas(h))]


def _filas_en(hallazgos: Iterable[Any], hoja: str) -> set[int]:
    objetivo = _norm(hoja)
    return {
        f
        for h in hallazgos
        for c in _celdas(h)
        if c[0] == objetivo and (f := _fila_de(c[1])) is not None
    }


def _menciona(h: Any, texto: str) -> bool:
    patron = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(texto)}(?![A-Za-z0-9_])", re.IGNORECASE)
    return bool(patron.search(h.descripcion)) or any(patron.search(str(o)) for o in h.origen_ids)


def _lista(valores: Iterable[object], maximo: int = 6) -> str:
    vistos = sorted({str(v) for v in valores}, key=lambda s: (len(s), s))
    resto = len(vistos) - maximo
    return ", ".join(vistos[:maximo]) + (f" (+{resto})" if resto > 0 else "")


# --- Oráculos sobre el libro RECIBIDO (openpyxl, aparte del lector) ------------------------------


def _abrir_wb(datos: bytes, data_only: bool) -> Any:
    return openpyxl.load_workbook(io.BytesIO(datos), data_only=data_only)


def _hoja(wb: Any, nombre: str) -> Any | None:
    objetivo = _norm(nombre)
    return next((ws for ws in wb.worksheets if _norm(ws.title) == objetivo), None)


def _formulas(wb: Any) -> Iterable[tuple[str, str, str]]:
    for ws in wb.worksheets:
        for fila in ws.iter_rows():
            for c in fila:
                v = c.value
                texto = getattr(v, "text", v)  # ArrayFormula
                if isinstance(texto, str) and texto.startswith("="):
                    yield ws.title, c.coordinate, texto


def _refs_rotas(wb_f: Any) -> list[tuple[str, str]]:
    return [(_norm(h), ref) for h, ref, f in _formulas(wb_f) if "#REF!" in f.upper()]


def _nombres_definidos(wb: Any) -> list[tuple[str, str]]:
    nombres = [(n, d.attr_text or "") for n, d in wb.defined_names.items()]
    for ws in wb.worksheets:
        nombres.extend((n, d.attr_text or "") for n, d in ws.defined_names.items())
    return nombres


def _nombres_externos(wb_f: Any) -> list[str]:
    return [n for n, texto in _nombres_definidos(wb_f) if "[" in texto]


def _numeros_duplicados(wb_v: Any) -> dict[int, list[int]]:
    """Número de partida (PRESUPUESTO col. B) -> filas, solo los repetidos. Una fila es partida si
    B es un entero y E (unidad) tiene texto: así no cuentan los capítulos."""
    ws = _hoja(wb_v, "PRESUPUESTO")
    if ws is None:
        return {}
    por_numero: dict[int, list[int]] = {}
    for fila in range(1, ws.max_row + 1):
        numero = _dec(ws[f"B{fila}"].value)
        unidad = ws[f"E{fila}"].value
        if numero is None or numero != numero.to_integral_value() or not str(unidad or "").strip():
            continue
        por_numero.setdefault(int(numero), []).append(fila)
    return {n: filas for n, filas in por_numero.items() if len(filas) > 1}


def _apus_en_conflicto(wb_f: Any) -> dict[int, list[str]]:
    """Fila de PRESUPUESTO -> hojas APU cuyo título (A2) la nombra, solo si son dos o más."""
    por_fila: dict[int, list[str]] = {}
    for ws in wb_f.worksheets:
        if not _norm(ws.title).startswith("APU"):
            continue
        m = _RE_TITULO_APU.search(str(ws["A2"].value or ""))
        if m:
            por_fila.setdefault(int(m.group(1)), []).append(ws.title)
    return {f: hojas for f, hojas in por_fila.items() if len(hojas) > 1}


def _celdas_apu(wb_f: Any, hoja: str) -> tuple[list[str], list[str]]:
    """En la hoja APU: celdas con el literal 0,02 (utilidad escrita a mano, H2) y fórmulas con
    `/12` (rendimiento literal, H12)."""
    ws = _hoja(wb_f, hoja)
    if ws is None:
        return [], []
    literales, divisiones = [], []
    for fila in ws.iter_rows():
        for c in fila:
            v = c.value
            if (
                isinstance(v, int | float)
                and not isinstance(v, bool)
                and _cerca(_dec(v), Decimal("0.02"), Decimal("0.0000001"))
            ):
                literales.append(c.coordinate)
            if isinstance(v, str) and v.startswith("=") and _RE_DIV12.search(v):
                divisiones.append(c.coordinate)
    return literales, divisiones


def _valor_nombre(wb_f: Any, wb_v: Any, nombre: str) -> Decimal | None:
    definido = wb_f.defined_names.get(nombre)
    if definido is None:
        return None
    for hoja, coord in definido.destinations:
        ws = _hoja(wb_v, hoja)
        if ws is not None:
            return _dec(ws[coord.replace("$", "")].value)
    return None


# --- Lo que se evalúa de un libro -----------------------------------------------------------------


@dataclass(slots=True)
class Evaluacion:
    caso: Caso
    resultado: Any = None
    hallazgos: list[Any] = field(default_factory=list)
    error: str = ""
    orig_f: Any = None
    orig_v: Any = None
    devolucion: bytes | None = None
    ruta_devolucion: Path | None = None
    error_devolucion: str = ""
    dev_f: Any = None
    dev_v: Any = None
    error_reabrir: str = ""
    pdf_extra: list[tuple[str, list[Any]]] = field(default_factory=list)

    @property
    def etiqueta(self) -> str:
        return self.caso.etiqueta


Comprobacion = Callable[[Evaluacion], tuple[bool, str]]


def _precios_silice(r: Any) -> dict[int, Decimal] | None:
    """P.U. de Silice por fila de PRESUPUESTO, donde sea que `ResultadoFusion` lo guarde."""
    for fuente in (r, getattr(r, "datos", None), getattr(r, "calculos", None)):
        pu = getattr(fuente, "precios_unitarios", None)
        if isinstance(pu, Mapping) and pu:
            return {int(k): v for k, v in pu.items() if _dec(v) is not None}
    calculos = getattr(r, "calculos", None)
    if isinstance(calculos, Mapping) and calculos:
        por_hoja = {str(k): _dec(getattr(v, "precio_unitario", None)) for k, v in calculos.items()}
        salida = {
            p.fila: pu
            for p in r.libro.partidas
            if p.hoja_apu and (pu := por_hoja.get(p.hoja_apu)) is not None
        }
        return salida or None
    return None


def _totales_silice(r: Any) -> dict[str, Decimal]:
    totales = getattr(r, "totales_silice", None) or {}
    return {str(k): d for k, v in totales.items() if (d := _dec(v)) is not None}


# Comprobaciones de reglas ---------------------------------------------------------------------


def _l1_en(hoja: str, minimo_filas: int) -> Comprobacion:
    def comprobar(ev: Evaluacion) -> tuple[bool, str]:
        en = _en_hoja(_de(ev.hallazgos, "L1", "ERROR"), hoja)
        filas = _filas_en(en, hoja)
        ok = len(en) > 0 and len(filas) >= minimo_filas
        return ok, f"{len(en)} L1 ERROR en {hoja}; filas {_lista(filas) or 'ninguna'}"

    return comprobar


def _l1_rend_b2(ev: Evaluacion) -> tuple[bool, str]:
    esperadas = {("PRESUPUESTO", "F26"), ("PRESUPUESTO", "F27")}
    celdas = {c for h in _de(ev.hallazgos, "L1", "ERROR") for c in _celdas(h)}
    faltan = esperadas - celdas
    vistas = {f"{c[1]}" for c in celdas if c[0] == "PRESUPUESTO"}
    return not faltan, (
        f"L1 en PRESUPUESTO: {_lista(vistas) or 'ninguna'}; faltan {_lista(c[1] for c in faltan)}"
        if faltan
        else "L1 en PRESUPUESTO!F26 y F27 (REND de las partidas 15 y 16)"
    )


def _l5_refs(hoja: str | None, documentadas: int | None) -> Comprobacion:
    """Cada `#REF!` del libro recibido (oráculo openpyxl) tiene un L5 con esa celda."""

    def comprobar(ev: Evaluacion) -> tuple[bool, str]:
        oraculo = [c for c in _refs_rotas(ev.orig_f) if hoja is None or c[0] == _norm(hoja)]
        cubiertas = {c for h in _de(ev.hallazgos, "L5") for c in _celdas(h)}
        faltan = [f"{c[0]}!{c[1]}" for c in oraculo if c not in cubiertas]
        donde = hoja or "el libro"
        texto = f"{len(oraculo) - len(faltan)}/{len(oraculo)} #REF! de {donde} con L5"
        ok = not faltan and len(oraculo) > 0
        if documentadas is not None and len(oraculo) != documentadas:
            ok = False
            texto += f"; el libro tiene {len(oraculo)} y las causas raiz dicen {documentadas}"
        if faltan:
            texto += f"; sin L5: {_lista(faltan)}"
        return ok, texto

    return comprobar


def _l5_nombres(documentados: int | None) -> Comprobacion:
    def comprobar(ev: Evaluacion) -> tuple[bool, str]:
        oraculo = _nombres_externos(ev.orig_f)
        l5 = _de(ev.hallazgos, "L5")
        faltan = [n for n in oraculo if not any(_menciona(h, n) for h in l5)]
        ok = not faltan
        texto = f"{len(oraculo) - len(faltan)}/{len(oraculo)} nombres con vinculo externo con L5"
        if documentados is not None and len(oraculo) != documentados:
            ok = False
            texto += f"; el libro tiene {len(oraculo)} y las causas raiz dicen {documentados}"
        if faltan:
            texto += f"; sin L5: {_lista(faltan)}"
        return ok, texto

    return comprobar


def _l5_todo(ev: Evaluacion) -> tuple[bool, str]:
    ok_refs, t_refs = _l5_refs(None, None)(ev)
    ok_nom, t_nom = _l5_nombres(None)(ev)
    if not _refs_rotas(ev.orig_f):  # un libro sin #REF! no exige L5 por celdas
        ok_refs, t_refs = True, "sin #REF! en el libro"
    return ok_refs and ok_nom, f"{t_refs}; {t_nom}"


def _l7_mediciones(ev: Evaluacion) -> tuple[bool, str]:
    en = _en_hoja(_de(ev.hallazgos, "L7"), "MEDICIONES")
    sev = Counter(h.severidad.name for h in en)
    return len(en) > 0, f"{len(en)} L7 en MEDICIONES ({dict(sev) or 'ninguno'})"


def _l9_procura_b2(ev: Evaluacion) -> tuple[bool, str]:
    esperados = (
        Decimal("-6969.49"),
        Decimal("-4861.47"),
        Decimal("-246.69"),
        Decimal("191309.86"),
    )
    impactos = [_dec(h.impacto) for h in _en_hoja(_de(ev.hallazgos, "L9"), "PROCURA")]
    presentes = [i for i in impactos if i is not None]
    faltan = [e for e in esperados if not any(_cerca(i, e, TOL_CENTIMO) for i in presentes)]
    invertidos = [e for e in faltan if any(_cerca(i, -e, TOL_CENTIMO) for i in presentes)]
    texto = f"impactos L9 en PROCURA: {_lista(_fmt(i) for i in presentes) or 'ninguno'}"
    if faltan:
        texto += f"; faltan {_lista(_fmt(e) for e in faltan)}"
    if invertidos:
        texto += f" (con signo opuesto: {_lista(_fmt(e) for e in invertidos)})"
    return not faltan, texto


def _f1_c2(ev: Evaluacion) -> tuple[bool, str]:
    f1 = _de(ev.hallazgos, "F1")
    en_24 = [h for h in f1 if 24 in _filas_en([h], "PRESUPUESTO")]
    impactos = [_dec(h.impacto) for h in en_24]
    ok = any(
        h.severidad.name == "ERROR" and _cerca(abs(i), Decimal("205.92"), TOL_IMPACTO)
        for h, i in zip(en_24, impactos, strict=True)
        if i is not None
    )
    otros = sorted(_filas_en(f1, "PRESUPUESTO"))
    return ok, (
        f"F1 en PRESUPUESTO fila 24: impacto {_lista(_fmt(i) for i in impactos) or 'ninguno'} "
        f"(esperado 205,92 +-0,05); F1 en filas {_lista(otros) or 'ninguna'}"
    )


def _l4_c2(ev: Evaluacion) -> tuple[bool, str]:
    en = _en_hoja(_de(ev.hallazgos, "L4", "ERROR"), "APU-07")
    con_impacto = [h for h in en if _dec(h.impacto) not in (None, Decimal(0))]
    celdas = {c[1] for h in en for c in _celdas(h) if c[0] == "APU-07"}
    return bool(con_impacto), (
        f"{len(en)} L4 ERROR en APU-07 ({_lista(celdas) or 'sin celda'}); impacto "
        f"{_lista(_fmt(_dec(h.impacto), 4) for h in en) or '-'}"
    )


def _l6_c2(ev: Evaluacion) -> tuple[bool, str]:
    literales, divisiones = _celdas_apu(ev.orig_f, "APU-07")
    l6 = _en_hoja(_de(ev.hallazgos, "L6", "ADVERTENCIA"), "APU-07")
    celdas = {c[1] for h in l6 for c in _celdas(h) if c[0] == "APU-07"}
    utilidad = bool(literales) and bool(celdas & set(literales))
    div12 = bool(divisiones) and bool(celdas & set(divisiones))
    return utilidad and div12, (
        f"L6 en APU-07: {_lista(celdas) or 'ninguna'}; oraculo utilidad 0,02 en "
        f"{_lista(literales) or '-'} ({'OK' if utilidad else 'falta'}), '/12' en "
        f"{_lista(divisiones) or '-'} ({'OK' if div12 else 'falta'})"
    )


#: H18 (causas raíz, V5): en B-2 la utilidad del APU-09 está escrita a mano en 30 %
#: (`G59 = G58*0.3`) y no lee `=UTIL` (10 %). L6 la marca "a confirmar" con impacto informativo
#: (global - local) x base x cantidad = -746,98 USD sin IVA (los 746,98 de más frente al 10 %).
_RE_UTIL_30 = re.compile(r"^=\s*\+?\$?G\$?58\s*\*\s*0?\.30*\s*$", re.IGNORECASE)
IMPACTO_H18 = Decimal("-746.98")


def _l6_util30_b2(ev: Evaluacion) -> tuple[bool, str]:
    ws = _hoja(ev.orig_f, "APU-09")
    formula = str(ws["G59"].value or "") if ws is not None else ""
    oraculo = bool(_RE_UTIL_30.match(formula.replace(" ", "")))
    l6 = [
        h for h in _de(ev.hallazgos, "L6", "ADVERTENCIA") if (_norm("APU-09"), "G59") in _celdas(h)
    ]
    impactos = [_dec(h.impacto) for h in l6]
    con_impacto = any(_cerca(i, IMPACTO_H18, TOL_IMPACTO) for i in impactos)
    invertido = any(_cerca(i, -IMPACTO_H18, TOL_IMPACTO) for i in impactos)
    texto = (
        f"oraculo APU-09!G59 {'= G58*0.3' if oraculo else 'sin G58*0.3'}; "
        f"{len(l6)} L6 ADVERTENCIA en G59; impacto {_lista(_fmt(i) for i in impactos) or '-'} "
        f"(H18: {_fmt(IMPACTO_H18)} +-{TOL_IMPACTO}, informativo)"
    )
    if invertido and not con_impacto:
        texto += " (con signo opuesto)"
    return oraculo and bool(l6) and con_impacto, texto


def _l8_c2(ev: Evaluacion) -> tuple[bool, str]:
    duplicados = _numeros_duplicados(ev.orig_v)
    filas_l8 = _filas_en(_de(ev.hallazgos, "L8", "ADVERTENCIA"), "PRESUPUESTO")
    faltan = [n for n, filas in duplicados.items() if not filas_l8 & set(filas)]
    ok = set(duplicados) == {6, 7} and not faltan
    return ok, (
        f"oraculo: numeros repetidos {dict(sorted(duplicados.items())) or 'ninguno'} "
        f"(documentados 6 y 7); L8 en filas {_lista(filas_l8) or 'ninguna'}"
        + (f"; sin L8: {_lista(faltan)}" if faltan else "")
    )


def _l3_filas(filas: tuple[int, ...]) -> Comprobacion:
    def comprobar(ev: Evaluacion) -> tuple[bool, str]:
        vistas = _filas_en(_de(ev.hallazgos, "L3"), "PRESUPUESTO")
        faltan = [f for f in filas if f not in vistas]
        return not faltan, (
            f"L3 en PRESUPUESTO filas {_lista(vistas) or 'ninguna'}"
            + (f"; faltan {_lista(faltan)}" if faltan else "")
        )

    return comprobar


def _c2_l3_o_parche(ev: Evaluacion) -> tuple[bool, str]:
    """Spec §7 (errata RL-7): L2 ADVERTENCIA en las filas 19 y 22 de C-2 (el original pedía L3).
    RL-7: ningún libro tiene valores guardados desactualizados (lo confirma un oráculo aparte
    sobre las referencias directas de esas filas); el parche manual por fila es L2 ADVERTENCIA."""
    ok_l3, t_l3 = _l3_filas((19, 22))(ev)
    filas_l2 = _filas_en(_de(ev.hallazgos, "L2", "ADVERTENCIA"), "PRESUPUESTO")
    ok_l2 = {19, 22} <= filas_l2
    return ok_l3 or ok_l2, f"{t_l3}; L2 ADVERTENCIA en filas {_lista(filas_l2) or 'ninguna'}"


def _l9_resumen_c2(ev: Evaluacion) -> tuple[bool, str]:
    impactos = [_dec(h.impacto) for h in _en_hoja(_de(ev.hallazgos, "L9"), "RESUMEN")]
    ok = any(i is not None and _cerca(abs(i), Decimal("183.53"), TOL_IMPACTO) for i in impactos)
    return ok, (
        f"impactos L9 en RESUMEN: {_lista(_fmt(i) for i in impactos) or 'ninguno'} "
        "(esperado 183,53 +-0,05)"
    )


def _c1_l3_o_l2(ev: Evaluacion) -> tuple[bool, str]:
    ok_l3, t_l3 = _l3_filas((23, 24))(ev)
    conflicto = _apus_en_conflicto(ev.orig_f)
    l2 = _de(ev.hallazgos, "L2")
    hojas_conflicto = {_norm(h) for hojas in conflicto.values() for h in hojas}
    ok_l2 = bool(conflicto) and any(
        (_filas_en([h], "PRESUPUESTO") & set(conflicto))
        or ({c[0] for c in _celdas(h)} & hojas_conflicto)
        for h in l2
    )
    # Spec §7 (con la errata RL-7): el conflicto de APU (L2) Y los enlaces parcheados de las
    # filas 23 y 24 (L2 ADVERTENCIA); L3 en esas filas vale en lugar del parche.
    filas_adv = _filas_en(_de(ev.hallazgos, "L2", "ADVERTENCIA"), "PRESUPUESTO")
    ok_parche = ok_l3 or {23, 24} <= filas_adv
    return ok_l2 and ok_parche, (
        f"{t_l3}; L2 ADVERTENCIA en filas {_lista(filas_adv) or 'ninguna'}; "
        f"oraculo conflicto de APU: "
        f"{ {f: len(h) for f, h in conflicto.items()} or 'ninguno' }; {len(l2)} L2"
        f" ({'cubre el conflicto' if ok_l2 else 'no cubre el conflicto'})"
    )


def _l11(ev: Evaluacion) -> tuple[bool, str]:
    """L11 debe dispararse si y solo si los totales impresos del PDF emparejado difieren de los
    guardados en el libro (leídos con openpyxl por sus nombres). El PDF "del mismo nombre" puede
    ser de otra versión: en los libros B, los nombres de archivo de los PDF están cruzados respecto
    de los `.xlsx`, y lo correcto entonces es que L11 lo diga."""
    from adapters.hoja_empresa.pdf import leer_totales_impresos

    if ev.caso.pdf is None:
        return False, "no se encontro el PDF impreso del libro en la carpeta"
    impresos = leer_totales_impresos(ev.caso.pdf.read_bytes(), "pdf")
    guardados = [_valor_nombre(ev.orig_f, ev.orig_v, n) for n in NOMBRES_TOTALES]
    difiere = not all(
        _cerca(a, b, TOL_CELDA)
        for a, b in zip((impresos.subtotal, impresos.iva, impresos.total), guardados, strict=True)
    )
    errores = _de(ev.hallazgos, "L11", "ERROR")
    avisos = _de(ev.hallazgos, "L11", "ADVERTENCIA")
    extra = [(n, _de(hs, "L11", "ERROR")) for n, hs in ev.pdf_extra]
    ok = bool(errores) == difiere and not avisos and all(not e for _, e in extra)
    texto = (
        f"PDF emparejado: sin IVA impreso {_fmt(impresos.subtotal)}, libro {_fmt(guardados[0])} "
        f"({'difieren' if difiere else 'coinciden'}); {len(errores)} L11 ERROR, "
        f"{len(avisos)} L11 ADVERTENCIA"
    )
    if extra:
        texto += f"; otros {len(extra)} PDF con los mismos totales: " + ", ".join(
            f"{len(e)} ERROR" for _, e in extra
        )
    return ok, texto


# Comprobaciones de valores de Silice -----------------------------------------------------------


def _pu_igual_guardado(partidas_documentadas: int) -> Comprobacion:
    def comprobar(ev: Evaluacion) -> tuple[bool, str]:
        pus = _precios_silice(ev.resultado)
        if pus is None:
            return False, "ResultadoFusion no expone el P.U. de Silice por fila"
        ws = _hoja(ev.orig_v, "PRESUPUESTO")
        filas = [p.fila for p in ev.resultado.libro.partidas]
        malas = []
        for fila in filas:
            guardado = _dec(ws[f"P{fila}"].value) if ws is not None else None
            if not _cerca(pus.get(fila), guardado, TOL_CELDA):
                malas.append(f"fila {fila}: {_fmt(pus.get(fila), 4)} vs {_fmt(guardado, 4)}")
        ok = not malas and len(filas) == partidas_documentadas
        texto = f"{len(filas) - len(malas)}/{len(filas)} partidas con |PU Silice - P| < 0,005"
        if len(filas) != partidas_documentadas:
            texto += f" (documentadas {partidas_documentadas})"
        if malas:
            texto += f"; {_lista(malas, 4)}"
        return ok, texto

    return comprobar


def _totales_coherentes(ev: Evaluacion) -> tuple[bool, str]:
    tot = _totales_silice(ev.resultado)
    sub, iva, gen = (tot.get(n) for n in NOMBRES_TOTALES)
    if sub is None or iva is None or gen is None:
        return False, f"totales_silice incompletos: {sorted(tot)}"
    problemas = []
    if not _cerca(gen, sub + iva, TOL_CENTIMO):
        problemas.append(f"TOTALGEN {_fmt(gen)} != SUB + IVA {_fmt(sub + iva)}")
    sub_o = _valor_nombre(ev.orig_f, ev.orig_v, "SUBSINIVA")
    iva_o = _valor_nombre(ev.orig_f, ev.orig_v, "IVATOT")
    if sub_o and iva_o is not None:
        razon = iva_o / sub_o
        if not _cerca(iva, sub * razon, TOL_CENTIMO):
            problemas.append(f"IVATOT {_fmt(iva)} != SUB x {_fmt(razon, 4)}")
    pus = _precios_silice(ev.resultado) or {}
    suma = sum(
        (p.cantidad * pus[p.fila] for p in ev.resultado.libro.partidas if p.fila in pus),
        Decimal(0),
    )
    if pus and not _cerca(sub, suma, TOL_CENTIMO):
        problemas.append(f"SUB {_fmt(sub)} != sum(cant x PU) {_fmt(suma)}")
    esperado = SUBTOTAL_SILICE.get(ev.etiqueta)
    if esperado is not None and not _cerca(sub, esperado[0], esperado[1]):
        problemas.append(f"SUB {_fmt(sub)} != documentado {_fmt(esperado[0])}")
    texto = f"SUB {_fmt(sub)} IVA {_fmt(iva)} TOTAL {_fmt(gen)}"
    if esperado is not None:
        texto += f" (documentado {_fmt(esperado[0])})"
    return not problemas, texto + (f"; {'; '.join(problemas)}" if problemas else "")


# Comprobaciones de la devolución ---------------------------------------------------------------


def _requiere_devolucion(comprobar: Comprobacion) -> Comprobacion:
    def envuelta(ev: Evaluacion) -> tuple[bool, str]:
        if ev.devolucion is None:
            return False, f"sin devolucion: {ev.error_devolucion or 'no se genero'}"
        if ev.dev_f is None:
            return False, f"no reabre: {ev.error_reabrir}"
        return comprobar(ev)

    return envuelta


def _d_reabre(ev: Evaluacion) -> tuple[bool, str]:
    if ev.devolucion is None:
        return False, f"sin devolucion: {ev.error_devolucion or 'no se genero'}"
    if ev.dev_f is None:
        return False, f"openpyxl no la reabre: {ev.error_reabrir}"
    return True, f"reabre ({len(ev.dev_f.sheetnames)} hojas, {len(ev.devolucion)} bytes)"


def _d_sin_ref(ev: Evaluacion) -> tuple[bool, str]:
    rotas = [f"{h}!{c}" for h, c, f in _formulas(ev.dev_f) if "#REF!" in f.upper()]
    return not rotas, f"{len(rotas)} formulas con #REF!" + (f": {_lista(rotas)}" if rotas else "")


def _d_sin_indirect(ev: Evaluacion) -> tuple[bool, str]:
    con = [f"{h}!{c}" for h, c, f in _formulas(ev.dev_f) if "INDIRECT(" in f.upper()]
    nombres = [n for n, t in _nombres_definidos(ev.dev_f) if "INDIRECT(" in t.upper()]
    malas = con + nombres
    return not malas, f"{len(con)} formulas y {len(nombres)} nombres con INDIRECT" + (
        f": {_lista(malas)}" if malas else ""
    )


def _d_sin_vinculos(ev: Evaluacion) -> tuple[bool, str]:
    nombres = _nombres_definidos(ev.dev_f)
    externos = [n for n, t in nombres if "[" in t]
    rotos = [n for n, t in nombres if "#REF!" in t.upper()]
    with zipfile.ZipFile(io.BytesIO(ev.devolucion or b"")) as z:
        partes = [n for n in z.namelist() if n.startswith("xl/externalLinks/")]
    en_formulas = [f"{h}!{c}" for h, c, f in _formulas(ev.dev_f) if _RE_VINCULO_FORMULA.search(f)]
    ok = not (externos or rotos or partes or en_formulas)
    return ok, (
        f"nombres con '[': {len(externos)}; nombres rotos: {len(rotos)}; "
        f"xl/externalLinks: {len(partes)}; formulas con [n]: {len(en_formulas)}"
        + (f" ({_lista(externos + rotos + en_formulas)})" if not ok else "")
    )


def _hojas_xml(z: zipfile.ZipFile) -> list[tuple[str, str]]:
    """(nombre de hoja, parte XML) leyendo workbook.xml y sus relaciones."""
    libro = leer_xml(z.read("xl/workbook.xml"))
    rels = leer_xml(z.read("xl/_rels/workbook.xml.rels"))
    destino = {r.get("Id"): r.get("Target", "") for r in rels.iter(f"{NS_PKG_REL}Relationship")}
    hojas = []
    for s in libro.iter(f"{NS_MAIN}sheet"):
        target = destino.get(s.get(f"{NS_REL}id"), "")
        parte = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
        hojas.append((s.get("name", ""), parte))
    return hojas


def _d_valores_guardados(ev: Evaluacion) -> tuple[bool, str]:
    """Cada `<c>` con `<f>` tiene `<v>`. Un `<v>` vacío es texto vacío: XlsxWriter escribe así un
    resultado `""` (sin `t="str"`). Se acepta solo si la fórmula puede devolver `""`: lleva `""`
    escrita, o es una referencia pura (`=B13`, `=+'HOJA'!B13`) a otra celda de texto vacío ya
    aceptada (punto fijo). Un `<v>` vacío en cualquier otra fórmula es un valor que falta."""
    total = 0
    vacias: dict[tuple[str, str], str] = {}  # (hoja, celda) -> fórmula, con <v> vacío o sin <v>
    sin_v: set[tuple[str, str]] = set()
    with zipfile.ZipFile(io.BytesIO(ev.devolucion or b"")) as z:
        for nombre, parte in _hojas_xml(z):
            raiz = leer_xml(z.read(parte))
            for c in raiz.iter(f"{NS_MAIN}c"):
                f = c.find(f"{NS_MAIN}f")
                if f is None:
                    continue
                total += 1
                v = c.find(f"{NS_MAIN}v")
                if v is not None and (v.text or ""):
                    continue
                celda = (_norm(nombre), str(c.get("r", "")))
                vacias[celda] = f.text or ""
                if v is None:
                    sin_v.add(celda)
    aceptadas = {k for k, f in vacias.items() if k not in sin_v and '""' in f}
    cambio = True
    while cambio:
        cambio = False
        for k, f in vacias.items():
            m = _RE_REF_PURA.match(f.strip())
            if k in aceptadas or k in sin_v or m is None:
                continue
            destino = (_norm(m.group(1)) if m.group(1) else k[0], f"{m.group(2)}{m.group(3)}")
            if destino in aceptadas:
                aceptadas.add(k)
                cambio = True
    sin_valor = [f"{h}!{r}" for h, r in vacias if (h, r) not in aceptadas]
    return not sin_valor and total > 0, (
        f"{total - len(sin_valor)}/{total} formulas con valor guardado "
        f"({len(aceptadas)} texto vacio)"
        + (f"; sin valor: {_lista(sin_valor)}" if sin_valor else "")
    )


def _d_p_igual_silice(ev: Evaluacion) -> tuple[bool, str]:
    pus = _precios_silice(ev.resultado)
    if pus is None:
        return False, "ResultadoFusion no expone el P.U. de Silice por fila"
    ws = _hoja(ev.dev_v, "PRESUPUESTO")
    if ws is None:
        return False, "la devolucion no tiene PRESUPUESTO"
    malas = []
    for fila, pu in sorted(pus.items()):
        guardado = _dec(ws[f"P{fila}"].value)
        if not _cerca(guardado, pu, TOL_CELDA):
            malas.append(f"P{fila}: {_fmt(guardado, 4)} vs {_fmt(pu, 4)}")
    return not malas, f"{len(pus) - len(malas)}/{len(pus)} P de PRESUPUESTO = PU Silice" + (
        f"; {_lista(malas, 4)}" if malas else ""
    )


def _d_nombres_totales(ev: Evaluacion) -> tuple[bool, str]:
    tot = _totales_silice(ev.resultado)
    partes, ok = [], True
    for n in NOMBRES_TOTALES:
        valor = _valor_nombre(ev.dev_f, ev.dev_v, n)
        bien = _cerca(valor, tot.get(n), TOL_CELDA)
        ok = ok and bien
        partes.append(f"{n} {_fmt(valor)}{'' if bien else f' vs Silice {_fmt(tot.get(n))}'}")
    return ok, "; ".join(partes)


def _d_hojas_nuevas(ev: Evaluacion) -> tuple[bool, str]:
    faltan = [h for h in HOJAS_NUEVAS if h not in ev.dev_f.sheetnames]
    return not faltan, "AUDITORIA, TRAZABILIDAD y ALERTAS USD-Bs presentes" if not faltan else (
        f"faltan {_lista(faltan)}; hojas: {_lista(ev.dev_f.sheetnames, 30)}"
    )


def _d_rotulo_pu(ev: Evaluacion) -> tuple[bool, str]:
    objetivo = _norm(ROTULO_PU)
    por_hoja: dict[str, str | None] = {}
    for ws in ev.dev_f.worksheets:
        if not _norm(ws.title).startswith("APU"):
            continue
        por_hoja[ws.title] = next(
            (
                c.coordinate
                for fila in ws.iter_rows()
                for c in fila
                if isinstance(c.value, str) and objetivo in _norm(c.value)
            ),
            None,
        )
    sin = [h for h, c in por_hoja.items() if c is None]
    distintas = Counter(c for c in por_hoja.values() if c is not None)
    destinos = {
        coord
        for n, d in ev.dev_f.defined_names.items()
        if re.fullmatch(r"APU_\w+_PU", n)
        for _, coord in d.destinations
    }
    ok = bool(por_hoja) and not sin and len(distintas) == 1
    return ok, (
        f"{len(por_hoja)} APU; rotulo PU en {dict(distintas) or 'ninguna'}"
        + (f"; sin rotulo: {_lista(sin)}" if sin else "")
        + f"; nombres APU_*_PU apuntan a {_lista(destinos) or 'ninguno'}"
    )


def _d_huella(ev: Evaluacion) -> tuple[bool, str]:
    esperada = hashlib.sha256(ev.caso.datos).hexdigest()
    with zipfile.ZipFile(io.BytesIO(ev.devolucion or b"")) as z:
        if "docProps/custom.xml" not in z.namelist():
            return False, "la devolucion no tiene docProps/custom.xml"
        raiz = leer_xml(z.read("docProps/custom.xml"))
    valor = next(
        ("".join(p.itertext()).strip() for p in raiz if p.get("name") == PROPIEDAD_SHA),
        None,
    )
    if valor is None:
        return False, f"sin propiedad {PROPIEDAD_SHA}"
    ok = valor.lower() == esperada
    return ok, f"{PROPIEDAD_SHA} {'=' if ok else '!='} SHA-256 del recibido ({esperada[:12]}...)"


# --- Tabla de metas -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MetaLibro:
    codigo: str
    titulo: str
    comprobar: Comprobacion


METAS_REGLAS: dict[str, tuple[MetaLibro, ...]] = {
    "A": (
        MetaLibro("L1-CRONO", "L1 en CRONOGRAMA (>= 5 partidas)", _l1_en("CRONOGRAMA", 5)),
        MetaLibro("L1-AUX", "L1 en AUX", _l1_en("AUX", 1)),
        MetaLibro("L5-RESUMEN", "L5 en los 4 #REF! de RESUMEN", _l5_refs("RESUMEN", 4)),
        MetaLibro("L5-EXT", "L5 en los 11 nombres externos", _l5_nombres(11)),
    ),
    "B-1": (),
    "B-2": (
        MetaLibro("L1-REND", "L1 en REND de partidas 15 y 16 (F26, F27)", _l1_rend_b2),
        MetaLibro("L1-CRONO", "L1 en CRONOGRAMA", _l1_en("CRONOGRAMA", 1)),
        MetaLibro("L1-AUX", "L1 en AUX", _l1_en("AUX", 1)),
        MetaLibro("L9-PROCURA", "L9 en PROCURA con los 4 Dif. de H7", _l9_procura_b2),
        MetaLibro("L5-RESUMEN", "L5 en los 4 #REF! de RESUMEN", _l5_refs("RESUMEN", 4)),
        MetaLibro("L5-EXT", "L5 en los 11 nombres externos", _l5_nombres(11)),
        MetaLibro("L7", "L7 en MEDICIONES", _l7_mediciones),
        MetaLibro("L6", "L6 utilidad 30 % en APU-09!G59 (H18)", _l6_util30_b2),
    ),
    "C-1": (MetaLibro("L2", "L2 del conflicto y parches en filas 23 y 24", _c1_l3_o_l2),),
    "C-2": (
        MetaLibro("F1", "F1 en fila 24, impacto 205,92", _f1_c2),
        MetaLibro("L4", "L4 en APU-07", _l4_c2),
        MetaLibro("L6", "L6 utilidad 2 % y /12 en APU-07", _l6_c2),
        MetaLibro("L8", "L8 en los numeros 6 y 7", _l8_c2),
        MetaLibro("L3-RL7", "L3 o (RL-7) L2 ADV en filas 19 y 22", _c2_l3_o_parche),
        MetaLibro("L9-RESUMEN", "L9 en RESUMEN, 183,53", _l9_resumen_c2),
        MetaLibro("L5-CRONO", "L5 en los 6 #REF! de CRONOGRAMA", _l5_refs("CRONOGRAMA", 6)),
    ),
}

#: Partidas documentadas de los libros cuyo PRESUPUESTO cuadra con sus APU (P.U. = P guardado).
PARTIDAS_CUADRAN: dict[str, int] = {"A": 5, "B-1": 16, "B-2": 16}

METAS_COMUNES: tuple[MetaLibro, ...] = (
    MetaLibro("L5-TODO", "L5 en todo #REF! y nombre externo", _l5_todo),
    MetaLibro("L11", "PDF entregado = libro (sin L11)", _l11),
    MetaLibro("TOT", "Totales de Silice coherentes", _totales_coherentes),
)

METAS_DEVOLUCION: tuple[MetaLibro, ...] = (
    MetaLibro("D-REABRE", "Devolucion reabre con openpyxl", _d_reabre),
    MetaLibro("D-REF", "Devolucion sin #REF!", _requiere_devolucion(_d_sin_ref)),
    MetaLibro("D-INDIRECT", "Devolucion sin INDIRECT", _requiere_devolucion(_d_sin_indirect)),
    MetaLibro(
        "D-VINCULOS",
        "Devolucion sin vinculos ni nombres rotos",
        _requiere_devolucion(_d_sin_vinculos),
    ),
    MetaLibro(
        "D-VALORES", "Cada formula con valor guardado", _requiere_devolucion(_d_valores_guardados)
    ),
    MetaLibro("D-P", "P de PRESUPUESTO = PU Silice", _requiere_devolucion(_d_p_igual_silice)),
    MetaLibro(
        "D-TOTALES", "SUBSINIVA/IVATOT/TOTALGEN = Silice", _requiere_devolucion(_d_nombres_totales)
    ),
    MetaLibro(
        "D-HOJAS", "Hojas AUDITORIA, TRAZABILIDAD, ALERTAS", _requiere_devolucion(_d_hojas_nuevas)
    ),
    MetaLibro(
        "D-PU-CELDA", "Rotulo PU en la misma celda en todo APU", _requiere_devolucion(_d_rotulo_pu)
    ),
    MetaLibro("D-SHA", "Propiedad silice_sha256_origen", _requiere_devolucion(_d_huella)),
)


def _metas_de(etiqueta: str) -> tuple[MetaLibro, ...]:
    propias = METAS_REGLAS.get(etiqueta, ())
    pu = (
        (MetaLibro("PU", "PU Silice = P guardado", _pu_igual_guardado(PARTIDAS_CUADRAN[etiqueta])),)
        if etiqueta in PARTIDAS_CUADRAN
        else ()
    )
    return (*propias, *METAS_COMUNES, *pu, *METAS_DEVOLUCION)


# --- PDF simples (L10) ----------------------------------------------------------------------------

_SUBTIPOS_L10: tuple[tuple[str, str, str], ...] = (
    ("unidades", "suma de unidades distintas", ""),
    ("incoherente", "unidad × cantidad × precio incoherente", ""),
    ("pendiente", "precio pendiente", ""),
    ("MO fuera del total", "nota que contradice el total", "mano de obra"),
)


def _con_subtipo(hallazgos: Iterable[Any], prefijo: str, contiene: str = "") -> list[Any]:
    p, c = _norm(prefijo), _norm(contiene)
    return [
        h
        for h in hallazgos
        if h.regla == "L10" and _norm(h.descripcion).startswith(p) and c in _norm(h.descripcion)
    ]


def _revisar_pdf_simple(datos: bytes, nombre: str) -> tuple[Any, list[Any]]:
    """Por la entrada del producto (`fusion.proceso.auditar_pdf_simple`, la que usan la UI y la
    API); si esa versión de `fusion` aún no la tiene, por el adaptador directamente."""
    try:
        from fusion.proceso import auditar_pdf_simple
    except ImportError:
        from adapters.hoja_empresa.pdf import leer_pdf_simple, reglas_pdf_simple

        pdf = leer_pdf_simple(datos, nombre)
        return pdf, list(reglas_pdf_simple(pdf))
    resultado = auditar_pdf_simple(datos, nombre)
    return resultado.pdf, list(resultado.hallazgos)


def _metas_pdf_simples(rutas: Sequence[Path]) -> list[Fila]:
    filas: list[Fila] = []
    for k, ruta in enumerate(rutas, start=1):
        try:
            pdf, hallazgos = _revisar_pdf_simple(ruta.read_bytes(), f"pdf_simple_{k}.pdf")
        except Exception as e:  # noqa: BLE001 - la meta informa la falla, no la oculta
            filas.append(Fila(f"PDF-{k}.L10", "L10 sobre el PDF simple", Estado.FALLA, _falla(e)))
            continue
        numero = pdf.numero if pdf.numero in ("001", "002") else f"{k:03d}"
        faltan = [n for n, pre, con in _SUBTIPOS_L10 if not _con_subtipo(hallazgos, pre, con)]
        filas.append(
            Fila(
                f"PDF-{numero}.L10",
                "L10: unidades, incoherente, pendiente, MO",
                Estado.FALLA if faltan else Estado.OK,
                f"{len(hallazgos)} L10; "
                + (f"faltan {_lista(faltan)}" if faltan else "los 4 subtipos presentes"),
            )
        )
        if numero != "002":
            continue
        arit = _con_subtipo(hallazgos, "aritmética de fila")
        items = {i for i in (14, 18) if any(f"ITEM {i} " in _norm(h.descripcion) for h in arit)}
        suma = sum((_dec(h.impacto) or Decimal(0) for h in arit), Decimal(0))
        ok = items == {14, 18} and _cerca(suma, Decimal("4.65"), TOL_CELDA)
        filas.append(
            Fila(
                "PDF-002.L10-ARIT",
                "L10 aritmetica en items 14 y 18 (+4,65)",
                Estado.OK if ok else Estado.FALLA,
                f"items {_lista(items) or 'ninguno'}; impacto total {_fmt(suma)} (H17: 4,65)",
            )
        )
        comp = _con_subtipo(hallazgos, "cómputos ≠ presupuesto")
        pares = {(_dec(h.valor_observado), _dec(h.valor_esperado)) for h in comp}
        esperados = {
            (Decimal(90), Decimal(80)),
            (Decimal(4), Decimal(3)),
            (Decimal(5), Decimal(10)),
        }
        faltan_p = [f"{e[1]}->{e[0]}" for e in esperados if e not in pares]
        filas.append(
            Fila(
                "PDF-002.L10-COMP",
                "L10 computos != presupuesto (H16)",
                Estado.FALLA if faltan_p else Estado.OK,
                f"{len(comp)} hallazgos; "
                + (
                    f"faltan {_lista(faltan_p)}" if faltan_p else "80->90 m, 3->4 y 10->5 presentes"
                ),
            )
        )
    return filas


# --- Orquestación ---------------------------------------------------------------------------------


def _falla(e: BaseException) -> str:
    marco = traceback.extract_tb(e.__traceback__)[-1] if e.__traceback__ else None
    donde = f" en {Path(marco.filename).name}:{marco.lineno}" if marco else ""
    return f"{type(e).__name__}{donde}: {str(e)[:160]}"


def _casos(carpeta: Path) -> tuple[dict[str, Caso], list[str]]:
    """Identifica los libros. Devuelve {etiqueta: Caso} y avisos (sin nombres de archivo)."""
    from adapters.hoja_empresa.lector import leer_libro

    expectativas = _leer_expectativas(carpeta)
    pdfs = sorted(carpeta.glob("*.pdf"))
    casos: dict[str, Caso] = {}
    avisos: list[str] = []
    for ruta in sorted(carpeta.glob("*.xlsx")):
        if ruta.name.startswith("~$"):
            continue
        datos = ruta.read_bytes()
        huella = hashlib.sha256(datos).hexdigest()[:8]
        pdf_nombres: list[str] = []
        if ruta.name.lower() in expectativas:
            etiqueta, pdf_nombres = expectativas[ruta.name.lower()]
            como = "expectativas.json"
        else:
            try:
                etiqueta = _identificar(leer_libro(datos, ruta.name))
            except Exception as e:  # noqa: BLE001
                avisos.append(f"libro sha {huella}: el lector fallo ({_falla(e)})")
                continue
            como = "contenido"
            if etiqueta is None:
                avisos.append(f"libro sha {huella}: no coincide con ninguna firma (ignorado)")
                continue
        if etiqueta in casos:
            avisos.append(f"libro sha {huella}: otro libro {etiqueta} (se usa el primero)")
            continue
        caso = Caso(etiqueta, ruta, datos, como)
        if pdf_nombres:
            rutas_pdf = [carpeta / n for n in pdf_nombres if (carpeta / n).is_file()]
            caso.pdf, caso.pdf_extra = (rutas_pdf[0], rutas_pdf[1:]) if rutas_pdf else (None, [])
        else:
            caso.pdf = next((p for p in pdfs if p.stem.lower() == ruta.stem.lower()), None)
        casos[etiqueta] = caso
    if "C-2" in casos and not expectativas:
        _pdf_por_totales(casos["C-2"], pdfs)
    return casos, avisos


def _pdf_por_totales(caso: Caso, pdfs: Sequence[Path]) -> None:
    """Para C-2: los PDF impresos cuyos totales coinciden con los guardados del libro."""
    from adapters.hoja_empresa.pdf import leer_totales_impresos

    wb_f, wb_v = _abrir_wb(caso.datos, False), _abrir_wb(caso.datos, True)
    guardado = [_valor_nombre(wb_f, wb_v, n) for n in NOMBRES_TOTALES]
    for ruta in pdfs:
        if ruta == caso.pdf:
            continue
        try:
            t = leer_totales_impresos(ruta.read_bytes(), "pdf")
        except Exception:  # noqa: BLE001 - un PDF que no se lee no es candidato
            continue
        if all(
            _cerca(a, b, TOL_CENTIMO)
            for a, b in zip((t.subtotal, t.iva, t.total), guardado, strict=True)
        ):
            if caso.pdf is None:
                caso.pdf = ruta
            else:
                caso.pdf_extra.append(ruta)


def _evaluar_libro(
    caso: Caso,
    procesar: Callable[..., Any],
    devolver: Callable[[Any], bytes],
    args: Any,
    otro: bytes | None = None,
) -> Evaluacion:
    """Procesa un libro con nombres neutros (`libro_A.xlsx`): así ningún nombre de archivo real
    entra en los hallazgos ni en la devolución que se imprime. `otro` es la otra versión del mismo
    libro (B-1 para B-2), para las alertas "contra otra versión" (spec §4.3)."""
    ev = Evaluacion(caso)
    ev.orig_f, ev.orig_v = _abrir_wb(caso.datos, False), _abrir_wb(caso.datos, True)
    pdf = caso.pdf.read_bytes() if caso.pdf else None
    try:
        ev.resultado = procesar(
            caso.datos,
            f"libro_{caso.etiqueta}.xlsx",
            pdf=pdf,
            pdf_nombre=f"libro_{caso.etiqueta}.pdf" if pdf else "",
            contexto=None,
            fecha_libro=args.fecha_libro,
            fecha_devolucion=args.fecha_devolucion,
            otro=otro,
        )
        ev.hallazgos = list(ev.resultado.informe.hallazgos)
    except Exception as e:  # noqa: BLE001
        ev.error = _falla(e)
        return ev
    if caso.pdf_extra:
        from adapters.hoja_empresa.pdf import cotejar_con_libro, leer_totales_impresos

        for k, ruta in enumerate(caso.pdf_extra, start=1):
            nombre = f"libro_{caso.etiqueta}_extra{k}.pdf"
            t = leer_totales_impresos(ruta.read_bytes(), nombre)
            ev.pdf_extra.append((nombre, cotejar_con_libro(t, ev.resultado.libro)))
    try:
        ev.devolucion = devolver(ev.resultado)
    except Exception as e:  # noqa: BLE001
        ev.error_devolucion = _falla(e)
        return ev
    args.salida.mkdir(parents=True, exist_ok=True)
    ev.ruta_devolucion = args.salida / f"devolucion_libro_{caso.etiqueta}.xlsx"
    ev.ruta_devolucion.write_bytes(ev.devolucion)
    try:
        ev.dev_f = openpyxl.load_workbook(ev.ruta_devolucion, data_only=False)
        ev.dev_v = openpyxl.load_workbook(ev.ruta_devolucion, data_only=True)
    except Exception as e:  # noqa: BLE001
        ev.dev_f = ev.dev_v = None
        ev.error_reabrir = _falla(e)
    return ev


def _filas_de(ev: Evaluacion) -> list[Fila]:
    prefijo = f"{ev.etiqueta}."
    filas = [
        Fila(
            prefijo + "PROCESO",
            f"Libro {ev.etiqueta}: procesar_libro (por {ev.caso.como})",
            Estado.FALLA if ev.error else Estado.OK,
            ev.error or f"{len(ev.hallazgos)} hallazgos",
        )
    ]
    for meta in _metas_de(ev.etiqueta):
        if ev.error:
            filas.append(Fila(prefijo + meta.codigo, meta.titulo, Estado.FALLA, "no se proceso"))
            continue
        try:
            ok, evidencia = meta.comprobar(ev)
        except Exception as e:  # noqa: BLE001
            ok, evidencia = False, f"la comprobacion fallo: {_falla(e)}"
        filas.append(
            Fila(prefijo + meta.codigo, meta.titulo, Estado.OK if ok else Estado.FALLA, evidencia)
        )
    return filas


def _prohibidos(carpeta: Path, evaluaciones: Iterable[Evaluacion]) -> list[str]:
    """Textos que no pueden salir por pantalla: nombres de archivo y datos de PORTADA."""
    textos = {p.stem for p in carpeta.iterdir() if p.is_file()}
    for ev in evaluaciones:
        portada = getattr(getattr(ev.resultado, "libro", None), "portada", None)
        for campo in ("cliente", "obra", "contratista", "ubicacion"):
            textos.add(str(getattr(portada, campo, "") or ""))
    return sorted((t for t in textos if len(t.strip()) >= 4), key=len, reverse=True)


def _limpiar(texto: str, prohibidos: Sequence[str]) -> str:
    for p in prohibidos:
        texto = re.sub(re.escape(p), "[...]", texto, flags=re.IGNORECASE)
    return texto


def _resumen(evaluaciones: Sequence[Evaluacion], avisos: Sequence[str], salida: Path) -> str:
    lineas = ["", "RESUMEN"]
    for ev in evaluaciones:
        conteo = Counter(f"{h.regla}/{h.severidad.name[:3]}" for h in ev.hallazgos)
        detalle = ", ".join(f"{k} {v}" for k, v in sorted(conteo.items())) or "sin hallazgos"
        lineas.append(f"  Libro {ev.etiqueta} ({ev.caso.como}): {detalle}")
    for aviso in avisos:
        lineas.append(f"  Aviso: {aviso}")
    if any(ev.ruta_devolucion for ev in evaluaciones):
        lineas.append(f"  Devoluciones en: {salida}")
    return "\n".join(lineas)


def _fecha(texto: str) -> date:
    return date.fromisoformat(texto)


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("carpeta", type=Path, help="carpeta local con los libros .xlsx y sus PDF")
    p.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    p.add_argument("--json", action="store_true", help="metas en JSON en vez de tabla")
    p.add_argument("--fecha-libro", type=_fecha, default=FECHA_LIBRO)
    p.add_argument("--fecha-devolucion", type=_fecha, default=date.today())
    p.add_argument("--pdf-simple", type=Path, nargs="*", default=list(PDF_SIMPLES))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = _parsear_args(argv)
    if not args.carpeta.is_dir():
        print(f"No existe la carpeta de libros: {args.carpeta}", file=sys.stderr)
        return 2
    try:
        from fusion.proceso import devolver, procesar_libro
    except ImportError as e:
        print(
            f"Falta fusion.proceso: corre esto cuando V2 este integrada ({type(e).__name__}: {e}).",
            file=sys.stderr,
        )
        return 2

    casos, avisos = _casos(args.carpeta)
    evaluaciones = [
        _evaluar_libro(
            casos[e],
            procesar_libro,
            devolver,
            args,
            otro=casos[OTRA_VERSION[e]].datos if OTRA_VERSION.get(e) in casos else None,
        )
        for e in ETIQUETAS
        if e in casos
    ]
    filas: list[Fila] = []
    for etiqueta in ETIQUETAS:
        if etiqueta not in casos:
            filas.append(
                Fila(
                    f"{etiqueta}.PRESENTE",
                    f"Libro {etiqueta} en la carpeta",
                    Estado.FALLA,
                    "no se identifico en la carpeta",
                )
            )
    for ev in evaluaciones:
        filas.extend(_filas_de(ev))
    filas.extend(_metas_pdf_simples(args.pdf_simple))

    prohibidos = _prohibidos(args.carpeta, evaluaciones)
    filas = [Fila(f.codigo, f.titulo, f.estado, _limpiar(f.evidencia, prohibidos)) for f in filas]
    if args.json:
        print(_filas_a_json(filas))
    else:
        print(render_tabla(filas))
        print(_limpiar(_resumen(evaluaciones, avisos, args.salida), prohibidos))
    return 0 if all(f.estado is Estado.OK for f in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
