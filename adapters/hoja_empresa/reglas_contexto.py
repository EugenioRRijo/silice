"""Contexto común de las reglas del libro: lectura de fórmulas sin ejecutarlas y utilidades.

Lo comparten `reglas.py` (L1-L3, L5-L9 y la entrada pública) y `reglas_calculo.py` (L4 y los
complementos de L1 y L5). Vive aparte para que las dos dependan de él y no una de la otra; los
principios y los límites declarados de las reglas están en la cabecera de `reglas.py`.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from openpyxl.utils.cell import column_index_from_string as _col
from openpyxl.utils.cell import get_column_letter as _letra

from adapters.hoja_empresa.modelo import (
    ApuLeido,
    Celda,
    LibroLeido,
    PartidaLeida,
    Rotulo,
    clave,
)
from adapters.hoja_empresa.perfil import Perfil, normalizar
from adapters.hoja_empresa.umbrales import MEDIO_CENTAVO

_CERO = Decimal(0)
#: Medio centavo: por debajo, una diferencia de cuadre es redondeo de presentación.
_TOL_CUADRE = MEDIO_CENTAVO
#: Tolerancia relativa de L3 (valor guardado contra valor leído): ruido de coma flotante de Excel.
_TOL_RELATIVA = Decimal("0.000001")
#: Un `_TOL_CUADRE` sobre un monto ya redondeado a centavos por el propio libro (ROUND(…,2)).
_TOL_CENTAVO = Decimal("0.01")
#: Desglose de PRESUPUESTO en el orden de `Perfil.columnas_desglose` (H…P de la plantilla).
_ORDEN_DESGLOSE = (
    Rotulo.MAT,
    Rotulo.MO,
    Rotulo.EQ,
    Rotulo.TR,
    Rotulo.CD,
    Rotulo.ADM,
    Rotulo.SUB,
    Rotulo.UTI,
    Rotulo.PU,
)
_NOMBRE_ROTULO = {
    Rotulo.MAT: "materiales",
    Rotulo.MO: "mano de obra",
    Rotulo.EQ: "equipos y herramientas",
    Rotulo.TR: "transporte y disposición",
    Rotulo.CD: "costo directo",
    Rotulo.ADM: "administración",
    Rotulo.SUB: "subtotal (costo directo + administración)",
    Rotulo.UTI: "utilidad",
    Rotulo.PU: "precio unitario",
    Rotulo.REND: "rendimiento",
    Rotulo.ESC: "escombro a botar",
    Rotulo.BASE_MO: "subtotal de salarios base",
    Rotulo.EQ_DIA: "subtotal de equipos por día",
    Rotulo.HERR: "herramientas menores",
}
#: Respaldo del rótulo EQ: algunos APU no tienen la línea "Equipos" en el resumen, pero su CD suma
#: el subtotal del bloque de equipos (C-2 APU-06, C-1 APU-08). Es texto de la plantilla, no un dato.
_RESPALDO_EQ = ("SUBTOTAL EQUIPOS Y HERRAMIENTAS",)

_REF = r"(?:(?:'((?:[^']|'')+)'|([A-Za-z_][\w.]*))!)?\$?([A-Z]{1,3})\$?(\d+)"
_RX_REF = re.compile(rf"^{_REF}$")
_RX_REF_EN = re.compile(
    r"(?<![\w.$!:'\]])(?:(?:'((?:[^']|'')+)'|([A-Za-z_][\w.]*))!)?"
    r"\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?(?![\w(!:])"
)
_RX_TEXTO = re.compile(r'"(?:[^"]|"")*"')
_RX_NUMERO = r"(?<![A-Za-z_$\d.])(\d+(?:\.\d+)?|\.\d+)(?![\d.(])"
_RX_ARIT_LITERALES = re.compile(rf"{_RX_NUMERO}\s*[-+*/^]\s*{_RX_NUMERO}")
_RX_FACTOR_DECIMAL = re.compile(r"[*/]\s*(\d*\.\d+)(?![\d.])|(?<![A-Za-z_$\d.])(\d*\.\d+)\s*\*")
_RX_DIVISOR_LITERAL = re.compile(r"/\s*(\d+(?:\.\d+)?)(?![\d.(])")
_RX_UNO_ENTRE = re.compile(r"^1\s*/\s*\(\s*1\s*/\s*(.+)\)$", re.S)
_RX_SECCION = re.compile(r"^\s*[\w.]+\s*·")


# --- Utilidades de celdas y números ---------------------------------------------------------------


def _partir(ref: str) -> tuple[str, int]:
    m = re.match(r"^([A-Z]{1,3})(\d+)$", ref)
    if m is None:
        raise ValueError(ref)
    return m.group(1), int(m.group(2))


def _num(v: object) -> Decimal | None:
    return v if isinstance(v, Decimal) and v.is_finite() else None


def _n0(v: object) -> Decimal:
    """Valor numérico como lo vería `N()` de Excel: lo que no es número vale 0."""
    return _num(v) or _CERO


def _fmt(d: Decimal | None, dec: int = 2) -> str:
    """Número para leer: espacio de miles y coma decimal (1 234,56)."""
    if d is None:
        return "vacía"
    q = d.quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP)
    return f"{q:,.{dec}f}".replace(",", " ").replace(".", ",")


def _fu(d: Decimal | None) -> str:
    """Valor unitario: hasta 5 decimales, sin ceros de relleno."""
    if d is None:
        return "vacía"
    t = _fmt(d, 5).rstrip("0").rstrip(",")
    return t or "0"


def _valor(v: object) -> str:
    if v is None or v == "":
        return "vacía"
    if isinstance(v, Decimal):
        return _fu(v)
    texto = str(v).strip()
    return f"«{texto[:60]}…»" if len(texto) > 60 else f"«{texto}»"


def _centavos(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _filas(nums: Iterable[int]) -> str:
    """[10, 11, 12, 15] -> '10-12, 15'."""
    xs = sorted(set(nums))
    tramos: list[str] = []
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1:
            j += 1
        tramos.append(str(xs[i]) if i == j else f"{xs[i]}-{xs[j]}")
        i = j + 1
    return ", ".join(tramos)


def _hoja_ref(texto_hoja_quoted: str | None, texto_hoja: str | None, actual: str) -> str:
    if texto_hoja_quoted is not None:
        return texto_hoja_quoted.replace("''", "'")
    return texto_hoja if texto_hoja is not None else actual


# --- Análisis de fórmulas sin ejecutarlas ---------------------------------------------------------


def _sin_textos(formula: str) -> str:
    """La fórmula con cada literal de texto vaciado (`"…"` -> `""`), para buscar referencias."""
    return _RX_TEXTO.sub('""', formula)


def _cierre(texto: str, abre: int) -> int | None:
    """Índice del paréntesis que cierra el abierto en `abre`, respetando literales de texto."""
    nivel = 0
    i = abre
    en_texto = False
    while i < len(texto):
        ch = texto[i]
        if ch == '"':
            en_texto = not en_texto
        elif not en_texto:
            if ch == "(":
                nivel += 1
            elif ch == ")":
                nivel -= 1
                if nivel == 0:
                    return i
        i += 1
    return None


def _argumentos(texto: str) -> list[str]:
    """Parte la lista de argumentos de una función por las comas de primer nivel."""
    out: list[str] = []
    nivel = 0
    en_texto = False
    ini = 0
    for i, ch in enumerate(texto):
        if ch == '"':
            en_texto = not en_texto
        elif not en_texto:
            if ch == "(":
                nivel += 1
            elif ch == ")":
                nivel -= 1
            elif ch == "," and nivel == 0:
                out.append(texto[ini:i].strip())
                ini = i + 1
    out.append(texto[ini:].strip())
    return out


def _llamada(expr: str) -> tuple[str, list[str]] | None:
    """`FUNC(a, b)` que ocupa toda la expresión -> ('FUNC', ['a', 'b']); si no, None."""
    m = re.match(r"^([A-Za-z][A-Za-z0-9_.]*)\s*\(", expr)
    if m is None:
        return None
    abre = m.end() - 1
    if _cierre(expr, abre) != len(expr) - 1:
        return None
    return m.group(1).upper(), _argumentos(expr[abre + 1 : -1])


def _partes_concat(expr: str) -> list[str]:
    """Parte una concatenación por los `&` de primer nivel."""
    out: list[str] = []
    nivel = 0
    en_texto = False
    ini = 0
    for i, ch in enumerate(expr):
        if ch == '"':
            en_texto = not en_texto
        elif not en_texto:
            if ch == "(":
                nivel += 1
            elif ch == ")":
                nivel -= 1
            elif ch == "&" and nivel == 0:
                out.append(expr[ini:i].strip())
                ini = i + 1
    out.append(expr[ini:].strip())
    return out


@dataclass(frozen=True, slots=True)
class _Lectura:
    """Una celda que una fórmula lee. `fila_variable`: la fila sale de otra celda (AUX)."""

    destino: Celda
    via_indirect: bool = False
    fila_variable: bool = False
    numerica: bool = False  # envuelta en N(): un texto leído vale 0


class _Analizador:
    """Resuelve referencias, nombres e `INDIRECT` contra los valores guardados del libro."""

    def __init__(self, libro: LibroLeido) -> None:
        self.libro = libro
        self.hojas = {normalizar(h): h for h in libro.hojas}

    def hoja(self, nombre: str) -> str | None:
        return self.hojas.get(normalizar(nombre))

    def valor(self, c: Celda) -> object:
        return self.libro.valores.get(str(c))

    def formula(self, c: Celda) -> str | None:
        return self.libro.formulas.get(str(c))

    def nombre_a_celda(self, nombre: str) -> Celda | None:
        texto = self.libro.nombres.get(nombre)
        if texto is None:
            return None
        m = _RX_REF.match(texto.strip().lstrip("="))
        if m is None or (m.group(1) is None and m.group(2) is None):
            return None
        return Celda(_hoja_ref(m.group(1), m.group(2), ""), f"{m.group(3)}{m.group(4)}")

    def ref(self, texto: str, hoja: str) -> Celda | None:
        """Texto de una referencia a UNA celda (o nombre de una celda) -> Celda."""
        t = texto.strip()
        m = _RX_REF.match(t)
        if m is not None:
            return Celda(_hoja_ref(m.group(1), m.group(2), hoja), f"{m.group(3)}{m.group(4)}")
        if re.fullmatch(r"[A-Za-z_][\w.]*", t):
            return self.nombre_a_celda(t)
        return None

    def _pieza(self, pieza: str, hoja: str) -> tuple[str, bool] | None:
        """Valor de texto de una pieza de concatenación y si es variable (lee una celda)."""
        if len(pieza) >= 2 and pieza[0] == '"' and pieza[-1] == '"':
            return pieza[1:-1].replace('""', '"'), False
        llamada = _llamada(pieza)
        if llamada is not None:
            nombre, args = llamada
            if nombre == "TEXT" and len(args) == 2 and re.fullmatch(r'"0+"', args[1]):
                c = self.ref(args[0], hoja)
                n = _num(self.valor(c)) if c is not None else None
                if n is None or n != n.to_integral_value():
                    return None
                return f"{int(n):0{len(args[1]) - 2}d}", True
            return None
        c = self.ref(pieza, hoja)
        if c is None:
            return None
        v = self.valor(c)
        if isinstance(v, Decimal):
            return (str(int(v)) if v == v.to_integral_value() else str(v)), True
        if isinstance(v, str):
            return v, True
        return None

    def indirect(self, argumento: str, hoja: str) -> _Lectura | None:
        """Resuelve `INDIRECT(argumento)` con los valores guardados; None si no se puede."""
        piezas = _partes_concat(argumento)
        texto = ""
        variable_tras_hoja = False
        visto_excl = False
        for p in piezas:
            r = self._pieza(p, hoja)
            if r is None:
                return None
            t, variable = r
            if visto_excl and variable:
                variable_tras_hoja = True
            texto += t
            if "!" in t:
                visto_excl = True
        m = _RX_REF.match(texto.strip())
        if m is None:
            return None
        destino = Celda(_hoja_ref(m.group(1), m.group(2), hoja), f"{m.group(3)}{m.group(4)}")
        real = self.hoja(destino.hoja)
        if real is None:
            return None
        return _Lectura(Celda(real, destino.ref), True, variable_tras_hoja)

    def lectura_pura(self, formula: str, hoja: str) -> _Lectura | None:
        """Si la fórmula solo lee una celda (sin aritmética), esa celda; si no, None."""
        expr = formula.strip()
        if expr.startswith("="):
            expr = expr[1:]
        numerica = False
        for _ in range(8):
            expr = expr.strip().lstrip("+").strip()
            llamada = _llamada(expr)
            if llamada is not None:
                nombre, args = llamada
                if nombre == "N" and len(args) == 1:
                    expr = args[0]
                    numerica = True
                    continue
                if nombre == "IFERROR" and len(args) == 2:
                    expr = args[0]
                    continue
                if nombre == "IF" and len(args) == 3 and args[1] == '""':
                    expr = args[2]
                    continue
                if nombre == "INDIRECT" and len(args) in (1, 2):
                    r = self.indirect(args[0], hoja)
                    if r is None:
                        return None
                    return _Lectura(r.destino, True, r.fila_variable, numerica)
                return None
            m = _RX_UNO_ENTRE.match(expr)
            if m is not None and _cierre("(" + m.group(1) + ")", 0) == len(m.group(1)) + 1:
                expr = m.group(1)
                continue
            c = self.ref(expr, hoja)
            if c is None:
                return None
            real = self.hoja(c.hoja)
            return _Lectura(Celda(real, c.ref), numerica=numerica) if real is not None else None
        return None

    def lecturas(self, formula: str, hoja: str) -> list[_Lectura]:
        """Todas las celdas sueltas (no rangos) que lee una fórmula, incluidas las de `INDIRECT`."""
        out: list[_Lectura] = []
        i = 0
        mayus = formula.upper()
        while True:
            j = mayus.find("INDIRECT(", i)
            if j < 0:
                break
            fin = _cierre(formula, j + len("INDIRECT"))
            if fin is None:
                break
            args = _argumentos(formula[j + len("INDIRECT(") : fin])
            if args:
                r = self.indirect(args[0], hoja)
                if r is not None:
                    out.append(r)
            i = fin
        for m in _RX_REF_EN.finditer(_sin_textos(formula)):
            if m.group(5) is not None:  # rango: no es la lectura de una celda
                continue
            real = self.hoja(_hoja_ref(m.group(1), m.group(2), hoja))
            if real is not None:
                out.append(_Lectura(Celda(real, f"{m.group(3)}{m.group(4)}")))
        return out

    def celdas_referidas(self, formula: str, hoja: str, tope: int = 400) -> set[str]:
        """Claves `HOJA!REF` de todas las celdas que cita una fórmula, con los rangos expandidos."""
        out: set[str] = set()
        for m in _RX_REF_EN.finditer(_sin_textos(formula)):
            h = self.hoja(_hoja_ref(m.group(1), m.group(2), hoja)) or hoja
            c1, f1 = _col(m.group(3)), int(m.group(4))
            if m.group(5) is None:
                out.add(clave(h, f"{m.group(3)}{f1}"))
                continue
            c2, f2 = _col(m.group(5)), int(m.group(6))
            if (abs(c2 - c1) + 1) * (abs(f2 - f1) + 1) > tope:
                continue
            for c in range(min(c1, c2), max(c1, c2) + 1):
                for f in range(min(f1, f2), max(f1, f2) + 1):
                    out.add(clave(h, f"{_letra(c)}{f}"))
        return out


# --- Contexto común de las reglas -----------------------------------------------------------------


class _Contexto:
    """Lo que varias reglas comparten: perfil, analizador, índices y equivalencias de rótulos."""

    def __init__(self, libro: LibroLeido, perfil: Perfil) -> None:
        self.libro = libro
        self.perfil = perfil
        self.an = _Analizador(libro)
        pref = normalizar(perfil.prefijo_apu)
        self.hojas_apu = {h for h in libro.hojas if normalizar(h).startswith(pref)}
        self.apus = {a.hoja: a for a in libro.apus}
        self.partida_de_apu: dict[str, PartidaLeida] = {}
        for p in libro.partidas:
            if p.hoja_apu is not None and p.hoja_apu not in self.partida_de_apu:
                self.partida_de_apu[p.hoja_apu] = p
        self.partida_por_fila = {p.fila: p for p in libro.partidas}
        self.h_pres = self.an.hoja(perfil.hoja("PRESUPUESTO")) or perfil.hoja("PRESUPUESTO")
        # Fórmulas en el orden del libro (hoja, fila, columna): una sola vez, para el determinismo
        # y para no reordenar el libro entero en cada regla.
        indice = {h: i for i, h in enumerate(libro.hojas)}

        def _orden(k: str) -> tuple[int, int, int]:
            hoja, fila, col = _ordenar_celda(k)
            return indice.get(hoja, len(indice)), fila, col

        self.orden = sorted(libro.formulas, key=_orden)
        self.formulas_de: dict[str, list[str]] = defaultdict(list)
        for k in self.orden:
            self.formulas_de[k.split("!", 1)[0]].append(k)
        # Referencias puras dentro de cada hoja APU (para la clase de equivalencia de un rótulo).
        self.pura: dict[str, str] = {}
        self.inversa: dict[str, set[str]] = defaultdict(set)
        for k, f in libro.formulas.items():
            hoja = k.split("!", 1)[0]
            if hoja not in self.hojas_apu:
                continue
            lec = self.an.lectura_pura(f, hoja)
            if lec is not None and not lec.via_indirect:
                self.pura[k] = str(lec.destino)
                self.inversa[str(lec.destino)].add(k)
        self._equiv: dict[tuple[str, Rotulo], tuple[Celda | None, frozenset[str]]] = {}
        # Celdas por hoja y fila (texto de rótulos) para buscar etiquetas sin recorrer todo.
        self.por_fila: dict[tuple[str, int], list[tuple[int, object]]] = defaultdict(list)
        for k, v in libro.valores.items():
            hoja, ref = k.split("!", 1)
            letras, fila = _partir(ref)
            self.por_fila[(hoja, fila)].append((_col(letras), v))
        for lista in self.por_fila.values():
            lista.sort(key=lambda x: x[0])

    def etiqueta(self, hoja: str, fila: int, hasta_col: int = 6) -> str:
        """El primer texto de la fila (columnas A…F): el rótulo humano de esa fila."""
        for c, v in self.por_fila.get((hoja, fila), ()):
            if c > hasta_col:
                break
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    def celda_rotulo(self, apu: ApuLeido, r: Rotulo) -> Celda | None:
        celda = apu.rotulos.get(r)
        if celda is not None or r is not Rotulo.EQ:
            return celda
        col_rot = _col(self.perfil.columna_rotulos_apu)
        col_val = self.perfil.rotulos_apu[Rotulo.EQ].columna
        for (hoja, fila), celdas in sorted(self.por_fila.items()):
            if hoja != apu.hoja:
                continue
            for c, v in celdas:
                if c == col_rot and isinstance(v, str):
                    t = normalizar(v)
                    if any(t.startswith(normalizar(x)) for x in _RESPALDO_EQ):
                        return Celda(apu.hoja, f"{col_val}{fila}")
        return None

    def equivalentes(self, apu: ApuLeido, r: Rotulo) -> tuple[Celda | None, frozenset[str]]:
        """La celda del rótulo y todas las que valen lo mismo por referencia pura (ida y vuelta)."""
        k = (apu.hoja, r)
        if k in self._equiv:
            return self._equiv[k]
        celda = self.celda_rotulo(apu, r)
        if celda is None:
            self._equiv[k] = (None, frozenset())
            return self._equiv[k]
        conjunto = {str(celda)}
        pendientes = [str(celda)]
        while pendientes:
            x = pendientes.pop()
            vecinos = set(self.inversa.get(x, ()))
            if x in self.pura:
                vecinos.add(self.pura[x])
            for y in vecinos:
                if y not in conjunto and y.split("!", 1)[0] == apu.hoja:
                    conjunto.add(y)
                    pendientes.append(y)
        self._equiv[k] = (celda, frozenset(conjunto))
        return self._equiv[k]

    def es_hoja(self, hoja: str, logica: str) -> bool:
        return normalizar(hoja) == normalizar(self.perfil.hoja(logica))


def _ordenar_celda(origen: str) -> tuple[str, int, int]:
    hoja, ref = origen.split("!", 1)
    try:
        letras, fila = _partir(ref)
    except ValueError:
        return hoja, 0, 0
    return hoja, fila, _col(letras)


# --- Lectura de la lista de precios (L3 y L1) -----------------------------------------------------


def _iguales(a: object, b: object) -> bool:
    if (a is None or a == "") and (b is None or b == "" or b == _CERO):
        return True
    if (b is None or b == "") and a == _CERO:
        return True
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None:
        return abs(na - nb) <= max(abs(na), abs(nb)) * _TOL_RELATIVA
    if isinstance(a, str) and isinstance(b, str):
        return a.strip() == b.strip()
    return a == b


def _lectura_precios(ctx: _Contexto, formula: str, hoja: str) -> Celda | None:
    """`=VLOOKUP(B10,PRECIOS,k,…)` (con o sin IF/IFERROR) -> celda de INSUMOS que lee."""
    m = re.search(r"VLOOKUP\(\s*\$?([A-Z]{1,3})\$?(\d+)\s*,\s*PRECIOS\s*,\s*(\d)", formula, re.I)
    if m is None:
        return None
    codigo = ctx.an.valor(Celda(hoja, f"{m.group(1)}{m.group(2)}"))
    insumo = ctx.libro.insumo(str(codigo).strip()) if isinstance(codigo, str) else None
    rango = ctx.an.libro.nombres.get("PRECIOS", "")
    mr = re.match(r"^(?:'((?:[^']|'')+)'|([^!]+))!\$?([A-Z]{1,3})\$?\d+:", rango.strip())
    if insumo is None or mr is None:
        return None
    try:
        col = _letra(_col(mr.group(3)) + int(m.group(3)) - 1)
    except ValueError:  # columna 0 de VLOOKUP (Excel da #VALUE!) o más allá de ZZZ: no lee nada
        return None
    return Celda(insumo.celda.hoja, f"{col}{_partir(insumo.celda.ref)[1]}")
