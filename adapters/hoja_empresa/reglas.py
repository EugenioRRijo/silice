"""Reglas del libro L1-L9 (spec 1.5 §3) sobre un `LibroLeido`.

Cada regla compara lo que el libro **dice** (sus fórmulas) con lo que el libro **calcula** (sus
valores guardados) y con la forma real de cada APU (sus rótulos). Así detecta las causas raíz C1-C6
del análisis de los libros de la empresa sin ejecutar ninguna fórmula: las fórmulas se leen como
texto con expresiones regulares propias y los `INDIRECT` se resuelven con el valor guardado de las
celdas que concatenan (lo mismo que haría Excel en el momento en que se guardó el libro).

Principios:

- **La celda de origen siempre.** Todo hallazgo lleva en `origen_ids` las celdas `HOJA!REF`
  implicadas: la que tiene la fórmula, la que lee y, si la hay, la que debería leer.
- **Descripción para un administrador.** Cada descripción dice qué celda, qué lee, qué debería leer
  y qué efecto tiene, sin jerga de hoja de cálculo más allá de la referencia de celda.
- **El auditor no decide la intención** (F-D7). Lo que puede ser intencional (una utilidad
  escrita a mano, un rendimiento literal) es ADVERTENCIA "a confirmar"; lo que no admite dos
  lecturas es ERROR.
- **Sin falsos positivos por forma.** Una celda que lee el subtotal del bloque (`G12`) en lugar de
  la línea del resumen (`G43 = G12`) lee bien: se acepta toda celda que el rótulo lee o que lee al
  rótulo por referencia pura ("clase de equivalencia" del rótulo).
- **Determinismo.** Mismo libro, mismos hallazgos y en el mismo orden (regla, hoja, fila, columna).

Límites declarados:

- Solo se resuelven `INDIRECT` cuyo argumento concatena textos, celdas y `TEXT(celda,"00")`. Otro
  `INDIRECT` no se juzga (no se adivina).
- L3 compara lecturas puras (directa, `=+X`, nombre de una celda, `N()`, `IFERROR(X,…)`,
  `IF(…,"",X)`, `1/(1/X)`, `INDIRECT` resuelto y `VLOOKUP(código,PRECIOS,k,…)`); no recalcula
  aritmética (eso es F1, con el motor del núcleo).
- L4 y L6 solo miran los APU unidos a una partida: una plantilla sin partida no entra al
  presupuesto (L2 la informa).
- Los impactos de L6 son informativos: suponen que el resto del APU no cambia.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from adapters.hoja_empresa.modelo import (
    ApuLeido,
    Celda,
    LibroLeido,
    PartidaLeida,
    Rotulo,
    clave,
)
from adapters.hoja_empresa.perfil import Perfil, cargar_perfil, normalizar
from core.contracts.verificacion import Hallazgo, Severidad

__all__ = ["REGLAS_LIBRO", "reglas_del_libro"]

REGLAS_LIBRO: tuple[tuple[str, str], ...] = (
    ("L1", "Referencia desalineada"),
    ("L2", "Enlace partida ↔ APU roto"),
    ("L3", "Valor guardado ≠ fórmula"),
    ("L4", "Componente fuera del total"),
    ("L5", "Referencia rota o externa"),
    ("L6", "Parámetro global sobrescrito"),
    ("L7", "Dato dentro de fórmula"),
    ("L8", "Número de partida duplicado"),
    ("L9", "Cuadre interno"),
)

_CERO = Decimal(0)
_UNO = Decimal(1)
#: Medio centavo: por debajo, una diferencia de cuadre es redondeo de presentación.
_TOL_CUADRE = Decimal("0.005")
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
#: Componentes del costo directo (L4).
_COMPONENTES = (Rotulo.MAT, Rotulo.MO, Rotulo.EQ, Rotulo.TR)
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


def _col(letras: str) -> int:
    n = 0
    for ch in letras:
        n = n * 26 + (ord(ch) - 64)
    return n


def _letra(col: int) -> str:
    out = ""
    while col:
        col, r = divmod(col - 1, 26)
        out = chr(65 + r) + out
    return out


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


# --- L1 Referencia desalineada --------------------------------------------------------------------


def _rotulo_de_columna(ctx: _Contexto) -> dict[str, Rotulo]:
    cp = ctx.perfil.columnas_presupuesto
    out = {cp["rendimiento"]: Rotulo.REND}
    out.update(dict(zip(ctx.perfil.columnas_desglose, _ORDEN_DESGLOSE, strict=False)))
    return out


def _l1_comparar(
    ctx: _Contexto,
    origen: Celda,
    leida: Celda,
    apu: ApuLeido,
    r: Rotulo,
    quien: str,
    efecto: str,
    apu_leido: str | None = None,
) -> Hallazgo | None:
    """Compara la celda leída con la clase del rótulo `r` en `apu`; hallazgo si no coincide."""
    correcta, equivalentes = ctx.equivalentes(apu, r)
    v_leido = ctx.an.valor(leida)
    if apu_leido is None and str(leida) in equivalentes:
        return None
    nombre = _NOMBRE_ROTULO[r]
    if correcta is None:
        if _n0(v_leido) == 0:
            return None
        return Hallazgo(
            regla="L1",
            severidad=Severidad.ERROR,
            descripcion=(
                f"{origen} ({quien}) lee {leida} (valor {_valor(v_leido)}) como {nombre}, pero "
                f"{apu.hoja} no tiene ese rótulo: el valor correcto es 0. {efecto}"
            ),
            origen_ids=(str(origen), str(leida)),
            valor_observado=_num(v_leido),
            valor_esperado=_CERO,
        )
    v_ok = ctx.an.valor(correcta)
    if apu_leido is not None:
        motivo = (
            f"lee la hoja {apu_leido}, pero la partida está unida a {apu.hoja}: el {nombre} "
            f"correcto está en {correcta}"
        )
    else:
        motivo = f"el {nombre} de {apu.hoja} está en {correcta}"
    return Hallazgo(
        regla="L1",
        severidad=Severidad.ERROR,
        descripcion=(
            f"{origen} ({quien}) lee {leida} (valor {_valor(v_leido)}) como {nombre}; {motivo} "
            f"(valor {_valor(v_ok)}). {efecto}"
        ),
        origen_ids=(str(origen), str(leida), str(correcta)),
        valor_observado=_num(v_leido),
        valor_esperado=_num(v_ok),
    )


def _l1_presupuesto(ctx: _Contexto) -> list[Hallazgo]:
    mapa = _rotulo_de_columna(ctx)
    out: list[Hallazgo] = []
    for p in ctx.libro.partidas:
        if p.hoja_apu is None or p.hoja_apu not in ctx.apus:
            continue
        apu = ctx.apus[p.hoja_apu]
        for letra, r in mapa.items():
            origen = Celda(ctx.h_pres, f"{letra}{p.fila}")
            f = ctx.an.formula(origen)
            if not f:
                continue
            for lec in ctx.an.lecturas(f, ctx.h_pres):
                if lec.destino.hoja not in ctx.hojas_apu:
                    continue
                otro = lec.destino.hoja if lec.destino.hoja != apu.hoja else None
                efecto = (
                    "Efecto: la columna REND. muestra un rendimiento que no es el de la partida."
                    if r is Rotulo.REND
                    else f"Efecto: el {_NOMBRE_ROTULO[r]} de la fila no es el de su APU."
                )
                h = _l1_comparar(
                    ctx, origen, lec.destino, apu, r, f"partida {p.numero}", efecto, otro
                )
                if h is not None:
                    out.append(h)
    return out


def _l1_cronograma(ctx: _Contexto, hoja: str) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    for k in ctx.formulas_de.get(hoja, ()):
        f = ctx.libro.formulas[k]
        origen = Celda(hoja, k.split("!", 1)[1])
        _, fila = _partir(origen.ref)
        for lec in ctx.an.lecturas(f, hoja):
            apu = ctx.apus.get(lec.destino.hoja)
            if apu is None:
                continue
            numero = next(
                (v for c, v in ctx.por_fila.get((hoja, fila), ()) if isinstance(v, Decimal)), None
            )
            quien = f"partida {int(numero)}" if numero is not None else f"fila {fila}"
            v = _n0(ctx.an.valor(lec.destino))
            efecto = (
                "Efecto: la duración de la partida da 0 días y la curva S, el avance planificado "
                "y la holgura quedan falseados."
                if v == 0
                else "Efecto: la duración de la partida se calcula con otro rendimiento y la "
                "curva S y el avance planificado quedan falseados."
            )
            h = _l1_comparar(ctx, origen, lec.destino, apu, Rotulo.REND, quien, efecto)
            if h is not None:
                out.append(h)
    return out


def _l1_aux(ctx: _Contexto, hoja: str) -> list[Hallazgo]:
    """AUX lee filas fijas de cada APU: una fila por línea de insumo y una celda de escombro."""
    filas_leidas: dict[str, set[int]] = defaultdict(set)
    primera: dict[str, str] = {}
    escombro: dict[str, tuple[Celda, Celda]] = {}
    for k in ctx.formulas_de.get(hoja, ()):
        origen = Celda(hoja, k.split("!", 1)[1])
        _, fila = _partir(origen.ref)
        for lec in ctx.an.lecturas(ctx.libro.formulas[k], hoja):
            if lec.destino.hoja not in ctx.apus:
                continue
            ah = lec.destino.hoja
            if lec.fila_variable:
                filas_leidas[ah].add(_partir(lec.destino.ref)[1])
                primera.setdefault(ah, str(origen))
            elif _seccion_escombro(ctx, hoja, fila):
                escombro.setdefault(ah, (origen, lec.destino))
    out: list[Hallazgo] = []
    for ah in sorted(set(filas_leidas) | set(escombro), key=ctx.libro.hojas.index):
        apu = ctx.apus[ah]
        col_cod = ctx.perfil.columnas_linea["codigo"]
        lineas = {_partir(ln.celda_codigo.ref)[1]: ln.codigo for ln in apu.lineas}
        partes: list[str] = []
        origenes: list[str] = []
        observado = esperado = None
        if ah in filas_leidas:
            leidas = filas_leidas[ah]
            faltan = sorted(set(lineas) - leidas)
            de_mas = sorted(
                f
                for f in leidas - set(lineas)
                if ctx.an.valor(Celda(ah, f"{col_cod}{f}")) not in (None, "")
            )
            if faltan:
                codigos = ", ".join(f"{lineas[f]} (fila {f})" for f in faltan)
                partes.append(f"deja sin leer {len(faltan)} línea(s) de insumo reales: {codigos}")
                origenes.extend(f"{ah}!{col_cod}{f}" for f in faltan)
            if de_mas:
                textos = ", ".join(
                    f"{f} ({_valor(ctx.an.valor(Celda(ah, f'{col_cod}{f}')))})" for f in de_mas
                )
                partes.append(f"lee filas que no son líneas de insumo: {textos}")
            if partes:
                origenes.insert(0, primera[ah])
                partes[0] = (
                    f"AUX lee de {ah} las filas fijas {_filas(leidas)} para la lista de compras; "
                    + partes[0]
                )
        if ah in escombro:
            origen, leida = escombro[ah]
            correcta, equivalentes = ctx.equivalentes(apu, Rotulo.ESC)
            v_leido = ctx.an.valor(leida)
            v_ok = ctx.an.valor(correcta) if correcta is not None else _CERO
            if str(leida) not in equivalentes and _n0(v_leido) != _n0(v_ok):
                donde = (
                    f"en vez de {correcta} (valor {_valor(v_ok)})"
                    if correcta is not None
                    else "pero ese APU no tiene bloque de escombro (debería ser 0)"
                )
                partes.append(
                    f"{origen} toma el escombro de {leida} (valor {_valor(v_leido)}) {donde}"
                )
                origenes.extend([str(origen), str(leida)])
                if correcta is not None:
                    origenes.append(str(correcta))
                observado, esperado = _num(v_leido), _n0(v_ok)
        if not partes:
            continue
        out.append(
            Hallazgo(
                regla="L1",
                severidad=Severidad.ERROR,
                descripcion=(
                    "; ".join(partes)
                    + ". Efecto: PROCURA (lista de compras y escombro) no corresponde al "
                    "presupuesto."
                ),
                origen_ids=tuple(dict.fromkeys(origenes)),
                valor_observado=observado,
                valor_esperado=esperado,
            )
        )
    return out


def _seccion_escombro(ctx: _Contexto, hoja: str, fila: int) -> bool:
    """¿La fila está bajo un encabezado de AUX que habla de escombro?"""
    pref = normalizar(ctx.perfil.prefijo_apu)
    for f in range(fila, 0, -1):
        t = normalizar(ctx.etiqueta(hoja, f, hasta_col=1))
        if t and not t.startswith(pref):
            return "escombro" in t
    return False


def _l1_otras(ctx: _Contexto, hoja: str) -> list[Hallazgo]:
    """Otras hojas: solo se juzga lo que el rótulo de la fila permite saber (escombro o
    rendimiento); cualquier otra lectura de un APU no tiene un rótulo esperado y no se adivina."""
    out: list[Hallazgo] = []
    for k in ctx.formulas_de.get(hoja, ()):
        f = ctx.libro.formulas[k]
        origen = Celda(hoja, k.split("!", 1)[1])
        _, fila = _partir(origen.ref)
        lecs = [x for x in ctx.an.lecturas(f, hoja) if x.destino.hoja in ctx.apus]
        if not lecs:
            continue
        t = normalizar(ctx.etiqueta(hoja, fila))
        if "escombro" in t:
            r = Rotulo.ESC
        elif "rendimiento" in t:
            r = Rotulo.REND
        else:
            continue
        for lec in lecs:
            h = _l1_comparar(
                ctx,
                origen,
                lec.destino,
                ctx.apus[lec.destino.hoja],
                r,
                f"«{ctx.etiqueta(hoja, fila)[:50]}»",
                f"Efecto: {hoja} usa otro dato del APU como {_NOMBRE_ROTULO[r]}.",
            )
            if h is not None:
                out.append(h)
    return out


def _l1(ctx: _Contexto) -> list[Hallazgo]:
    out = _l1_presupuesto(ctx)
    for hoja in ctx.libro.hojas:
        if hoja in ctx.hojas_apu or hoja == ctx.h_pres:
            continue
        if ctx.es_hoja(hoja, "CRONOGRAMA"):
            out.extend(_l1_cronograma(ctx, hoja))
        elif ctx.es_hoja(hoja, "AUX"):
            out.extend(_l1_aux(ctx, hoja))
        else:
            out.extend(_l1_otras(ctx, hoja))
    return out


# --- L2 Enlace partida ↔ APU roto -----------------------------------------------------------------


def _l2(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    libro = ctx.libro
    titulo = ctx.perfil.celda_titulo_apu
    reclamos: dict[int, list[ApuLeido]] = defaultdict(list)
    for a in libro.apus:
        if a.fila_presupuesto is not None:
            reclamos[a.fila_presupuesto].append(a)
    for fila in sorted(reclamos):
        apus = reclamos[fila]
        if len(apus) < 2:
            continue
        p = ctx.partida_por_fila.get(fila)
        ganador = p.hoja_apu if p is not None else None
        nombres = " y ".join(a.hoja for a in apus)
        quien = f"la fila {fila} de {ctx.h_pres}" + (f" (partida {p.numero})" if p else "")
        desc = (
            f"Las hojas {nombres} tienen el mismo título {titulo} = +{ctx.h_pres}!D{fila}: las dos "
            f"dicen ser {quien}. "
        )
        desc += (
            f"Silice la unió a {ganador} (coincide por número o por P.U. guardado). "
            if ganador
            else "Ninguna se pudo unir. "
        )
        desc += (
            "Efecto: el título del otro APU no corresponde a su partida y cualquier fórmula que "
            "dependa del nombre de la hoja (parche manual, causa C2) puede leer el APU equivocado."
        )
        out.append(
            Hallazgo(
                regla="L2",
                severidad=Severidad.ERROR,
                descripcion=desc,
                origen_ids=tuple(f"{a.hoja}!{titulo}" for a in apus) + (f"{ctx.h_pres}!D{fila}",),
            )
        )
    for a in libro.apus:
        p = ctx.partida_de_apu.get(a.hoja)
        if p is None or a.fila_presupuesto is None or a.fila_presupuesto == p.fila:
            continue
        nombrada = ctx.partida_por_fila.get(a.fila_presupuesto)
        out.append(
            Hallazgo(
                regla="L2",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{a.hoja} está unido a la fila {p.fila} de {ctx.h_pres} (partida {p.numero}, "
                    f"«{p.descripcion[:60]}»), pero su título {titulo} apunta a la fila "
                    f"{a.fila_presupuesto}"
                    + (f" («{nombrada.descripcion[:60]}»)" if nombrada else "")
                    + ". Efecto: el APU impreso lleva el nombre de otra partida."
                ),
                origen_ids=(f"{a.hoja}!{titulo}", f"{ctx.h_pres}!D{p.fila}"),
            )
        )
    for p in libro.partidas:
        if p.hoja_apu is None:
            out.append(
                Hallazgo(
                    regla="L2",
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"La partida {p.numero} (fila {p.fila} de {ctx.h_pres}, "
                        f"«{p.descripcion[:60]}») no tiene APU: ningún título la nombra y no hay "
                        f"una hoja libre con su número o con su P.U. Efecto: su precio no se puede "
                        f"recalcular ni rastrear."
                    ),
                    origen_ids=(f"{ctx.h_pres}!B{p.fila}",),
                )
            )
    usados = set(ctx.partida_de_apu)
    plantillas = [a for a in libro.apus if a.hoja not in usados]
    for a in libro.apus:
        if a.hoja in usados and "#REF!" in (a.titulo or ""):
            out.append(
                Hallazgo(
                    regla="L2",
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"El título de {a.hoja} ({titulo}) es #REF!: la partida que nombraba se "
                        f"borró. Efecto: el APU impreso no dice a qué partida pertenece."
                    ),
                    origen_ids=(f"{a.hoja}!{titulo}",),
                )
            )
    if plantillas:
        rotos = [a.hoja for a in plantillas if "#REF!" in (a.titulo or "")]
        out.append(
            Hallazgo(
                regla="L2",
                severidad=Severidad.INFO,
                descripcion=(
                    f"Hojas de plantilla sin partida: {', '.join(a.hoja for a in plantillas)}. "
                    "Ninguna fila del presupuesto las usa; no se copian a la devolución"
                    + (f" (título #REF! en {', '.join(rotos)})" if rotos else "")
                    + "."
                ),
                origen_ids=tuple(f"{a.hoja}!{titulo}" for a in plantillas),
            )
        )
    return out


# --- L3 Valor guardado ≠ fórmula ------------------------------------------------------------------


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
    col = _letra(_col(mr.group(3)) + int(m.group(3)) - 1)
    return Celda(insumo.celda.hoja, f"{col}{_partir(insumo.celda.ref)[1]}")


def _l3(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    col_pu = ctx.perfil.columnas_presupuesto["precio_unitario"]
    col_monto = ctx.perfil.columnas_presupuesto["monto"]
    for k in ctx.orden:
        f = ctx.libro.formulas[k]
        hoja, ref = k.split("!", 1)
        lec = ctx.an.lectura_pura(f, hoja)
        destino = lec.destino if lec is not None else None
        if destino is None and hoja in ctx.hojas_apu:
            destino = _lectura_precios(ctx, f, hoja)
        if destino is None or str(destino) == k:
            continue
        guardado = ctx.libro.valores.get(k)
        leido = ctx.an.valor(destino)
        if isinstance(leido, str) and leido.startswith("#"):
            continue  # error leído: lo informa L5 y el IFERROR de la fórmula lo tapa
        if lec is not None and lec.numerica:
            leido = _n0(leido)
        if _iguales(guardado, leido):
            continue
        letras, fila = _partir(ref)
        p = ctx.partida_por_fila.get(fila) if hoja == ctx.h_pres else None
        if hoja in ctx.hojas_apu:
            p = ctx.partida_de_apu.get(hoja)
        dif = _num(leido)
        g = _num(guardado)
        impacto = None
        mueve = p is not None and p.cantidad != 0
        if hoja == ctx.h_pres and letras == col_pu and mueve and dif is not None and g is not None:
            impacto = _centavos(p.cantidad * (dif - g))
        elif hoja == ctx.h_pres and letras == col_monto and dif is not None and g is not None:
            impacto = _centavos(dif - g)
            mueve = True
        elif hoja == ctx.h_pres and letras not in (col_pu, col_monto):
            mueve = False
        sev = Severidad.ERROR if mueve else Severidad.ADVERTENCIA
        efecto = (
            "Efecto: el monto de la partida cambia al recalcular el libro."
            if mueve
            else "Efecto: el libro no estaba recalculado; al abrirlo en Excel el valor cambia"
            + (" (la partida tiene cantidad 0, no mueve el total)." if p is not None else ".")
        )
        out.append(
            Hallazgo(
                regla="L3",
                severidad=sev,
                descripcion=(
                    f"{k} guarda {_valor(guardado)}, pero su fórmula lee {destino}, que vale "
                    f"{_valor(leido)}. {efecto}"
                ),
                impacto=impacto,
                origen_ids=(k, str(destino)),
                valor_observado=g,
                valor_esperado=dif,
            )
        )
    return out + _l3_plantilla(ctx)


def _l3_plantilla(ctx: _Contexto) -> list[Hallazgo]:
    """P.U. de PRESUPUESTO parcheado a mano contra la fórmula de la plantilla (por número): L2.

    Ruling del líder (2026-10-13, bitácora 1.5): esto NO es L3. Los valores guardados de estos
    libros coinciden con sus fórmulas (Excel los guardó recalculados); lo que hay es un ENLACE
    parcheado a
    mano y atado al nombre de la hoja. Por eso se informa como L2 (enlace partida-APU frágil),
    ADVERTENCIA y sin impacto: la cifra es el riesgo si la fórmula volviera a la de la plantilla, no
    un error del total entregado.

    La fórmula de la plantilla lee el P.U. con `INDIRECT("'APU-"&TEXT($Bnn,"00")&"'!…")`: la hoja
    del NÚMERO de la partida. En los libros C esa fórmula se sustituyó a mano por una referencia
    directa a una hoja con otro nombre (`='APU-08'!G44` en la partida 6). El valor guardado sale del
    parche; la fórmula de la plantilla, recalculada sobre el mismo libro, daría otro (es lo que pasa
    si se recalcula con la plantilla, se renombran o se reordenan las hojas: hallazgo H5, causa C2).
    Solo se compara la columna del P.U. (la que mueve el monto) y solo si la hoja del número existe.
    """
    out: list[Hallazgo] = []
    col_pu = ctx.perfil.columnas_presupuesto["precio_unitario"]
    for p in ctx.libro.partidas:
        k = clave(ctx.h_pres, f"{col_pu}{p.fila}")
        f = ctx.libro.formulas.get(k)
        lec = ctx.an.lectura_pura(f, ctx.h_pres) if f else None
        if lec is None or lec.via_indirect or lec.destino.hoja not in ctx.hojas_apu:
            continue
        por_numero = ctx.an.hoja(f"{ctx.perfil.prefijo_apu}-{p.numero:02d}")
        if por_numero is None or por_numero == lec.destino.hoja:
            continue
        plantilla = Celda(por_numero, lec.destino.ref)
        guardado = ctx.libro.valores.get(k)
        segun_plantilla = _n0(ctx.an.valor(plantilla))
        if _iguales(guardado, segun_plantilla):
            continue
        g = _n0(guardado)
        riesgo = _centavos(p.cantidad * (segun_plantilla - g)) if p.cantidad != 0 else None
        efecto = (
            f"el monto de la partida cambiaría en {_fmt(riesgo)} USD sin IVA."
            if riesgo is not None
            else "la partida tiene cantidad 0 y no mueve el total, pero su P.U. cambiaría."
        )
        out.append(
            Hallazgo(
                regla="L2",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{k} (partida {p.numero}) guarda {_valor(guardado)}, coherente con su "
                    "fórmula, pero esa "
                    f"fórmula se cambió a mano para leer {lec.destino}; la de la plantilla lee la "
                    f"hoja del número de partida, {plantilla}, que vale {_valor(segun_plantilla)}. "
                    "El enlace depende del nombre de la hoja: si el libro se recalcula con la "
                    f"fórmula de la plantilla o se renombran o reordenan las hojas, {efecto}"
                ),
                origen_ids=(k, str(lec.destino), str(plantilla)),
                valor_observado=g,
                valor_esperado=segun_plantilla,
            )
        )
    return out


# --- L4 Componente fuera del total ----------------------------------------------------------------


def _l4(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    for apu in ctx.libro.apus:
        p = ctx.partida_de_apu.get(apu.hoja)
        celda_cd = apu.rotulos.get(Rotulo.CD)
        cd = apu.guardados.get(Rotulo.CD)
        if p is None or celda_cd is None or cd is None:
            continue
        f_cd = ctx.an.formula(celda_cd) or ""
        citadas = ctx.an.celdas_referidas(f_cd, apu.hoja) if f_cd else set()
        suma = _CERO
        fuera: list[tuple[Rotulo, Celda, Decimal]] = []
        for r in _COMPONENTES:
            celda, equivalentes = ctx.equivalentes(apu, r)
            if celda is None:
                continue
            v = _n0(ctx.an.valor(celda))
            suma += v
            if f_cd and v != 0 and not (citadas & equivalentes):
                fuera.append((r, celda, v))
        dif = suma - cd
        if not fuera and abs(dif) <= _TOL_CUADRE:
            continue
        factor = (_UNO + apu.administracion) * (_UNO + apu.utilidad)
        impacto = _centavos(dif * factor * p.cantidad)
        if fuera:
            que = ", ".join(f"{_NOMBRE_ROTULO[r]} ({c}, {_fu(v)} USD/u)" for r, c, v in fuera)
            detalle = f"la fórmula {celda_cd} {f_cd} deja fuera {que}"
        else:
            detalle = f"{celda_cd} no es la suma de los componentes"
        out.append(
            Hallazgo(
                regla="L4",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"Costo directo de {apu.hoja} (partida {p.numero}): {detalle}. El CD guardado "
                    f"es {_fu(cd)} USD/u y la suma de materiales, mano de obra, equipos y "
                    f"transporte es {_fu(suma)} USD/u. Efecto: con administración "
                    f"({_fu(apu.administracion)}) y utilidad ({_fu(apu.utilidad)}) del APU y la "
                    f"cantidad {_fu(p.cantidad)}, la partida queda corta en {_fmt(impacto)} USD "
                    "sin IVA."
                ),
                impacto=impacto,
                origen_ids=(str(celda_cd), *(str(c) for _, c, _ in fuera)),
                valor_observado=cd,
                valor_esperado=suma,
            )
        )
    return out


# --- L5 Referencia rota o externa -----------------------------------------------------------------


def _archivo(destino: str) -> str:
    """Solo el nombre del archivo de un vínculo (sin ruta de red ni de disco)."""
    from urllib.parse import unquote

    return unquote(re.split(r"[\\/]", destino.rstrip("/\\"))[-1]) or destino


def _l5(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    por_hoja: dict[str, list[str]] = defaultdict(list)
    externas: dict[str, list[str]] = defaultdict(list)
    for k in ctx.orden:
        f = ctx.libro.formulas[k]
        hoja = k.split("!", 1)[0]
        if "#REF!" in f.upper():
            por_hoja[hoja].append(k)
        if re.search(r"\[\d+\]", _sin_textos(f)):
            externas[hoja].append(k)
    for hoja in sorted(por_hoja, key=ctx.libro.hojas.index):
        celdas = por_hoja[hoja]
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{len(celdas)} fórmula(s) de {hoja} con #REF! (la celda u hoja que citaban "
                    f"se borró): {', '.join(c.split('!', 1)[1] for c in celdas)}. Efecto: esas "
                    "celdas muestran #REF! o un valor que ya no se puede rastrear."
                ),
                origen_ids=tuple(celdas),
            )
        )
    for hoja in sorted(externas, key=ctx.libro.hojas.index):
        celdas = externas[hoja]
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{len(celdas)} fórmula(s) de {hoja} leen otro libro: "
                    f"{', '.join(c.split('!', 1)[1] for c in celdas)}. Efecto: fuera del equipo "
                    "que tiene ese libro el valor no se puede recalcular."
                ),
                origen_ids=tuple(celdas),
            )
        )
    rotos = sorted(n for n, t in ctx.libro.nombres.items() if "#REF!" in t.upper())
    if rotos:
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{len(rotos)} nombre(s) definido(s) apuntan a #REF!: {', '.join(rotos)}. "
                    "Efecto: una fórmula que los use da #REF!; quedan de una hoja copiada o de "
                    "celdas borradas."
                ),
                origen_ids=tuple(f"nombre:{n}" for n in rotos),
            )
        )
    con_libro = sorted(
        (n for n, t in ctx.libro.nombres.items() if re.search(r"\[\d+\]", t)),
        key=lambda n: (len(n), n),
    )
    if con_libro:
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{len(con_libro)} nombre(s) definido(s) apuntan a otro libro: "
                    f"{', '.join(con_libro)}. Efecto: fuera del equipo que tiene ese libro, "
                    "cualquier fórmula que los use da #REF! (la hoja se copió desde otro libro)."
                ),
                origen_ids=tuple(f"nombre:{n}" for n in con_libro),
            )
        )
    for destino in dict.fromkeys(_archivo(v) for v in ctx.libro.vinculos_externos):
        out.append(
            Hallazgo(
                regla="L5",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"El libro guarda un vínculo a otro libro en una ruta de red: «{destino}». "
                    "Efecto: Excel pide actualizarlo al abrir; la devolución lo quita."
                ),
                origen_ids=(f"vinculo:{destino}",),
            )
        )
    return out


# --- L6 Parámetro global sobrescrito --------------------------------------------------------------


def _usa_nombre(formula: str | None, nombre: str, celda_param: Celda | None) -> bool:
    if not formula:
        return False
    sin = _sin_textos(formula)
    if re.search(rf"(?<![\w.]){re.escape(nombre)}(?![\w.(])", sin, re.I):
        return True
    if celda_param is not None:
        hoja, ref = celda_param.hoja, celda_param.ref
        letras, fila = _partir(ref)
        patron = rf"{re.escape(hoja)}'?!\$?{letras}\$?{fila}(?!\d)"
        return re.search(patron, sin) is not None
    return False


def _l6_porcentajes(ctx: _Contexto, apu: ApuLeido, p: PartidaLeida) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    params = ctx.libro.parametros
    col_pct = ctx.perfil.columna_porcentaje_apu
    casos = (
        (Rotulo.ADM, "ADMON", params.administracion, Rotulo.CD, "administración"),
        (Rotulo.UTI, "UTIL", params.utilidad, Rotulo.SUB, "utilidad"),
    )
    for r, nombre, global_, base_r, texto in casos:
        celda_g = apu.rotulos.get(r)
        if celda_g is None or nombre not in params.celdas:
            continue
        fila = _partir(celda_g.ref)[1]
        celda_f = Celda(apu.hoja, f"{col_pct}{fila}")
        f_g = ctx.an.formula(celda_g)
        f_f = ctx.an.formula(celda_f)
        param = params.celdas.get(nombre)
        if _usa_nombre(f_g, nombre, param):
            continue
        usa_f = bool(f_g) and re.search(
            rf"(?<![A-Z$]){col_pct}\$?{fila}(?!\d)", _sin_textos(f_g or "").replace("$", "")
        )
        if usa_f and _usa_nombre(f_f, nombre, param):
            continue
        local: Decimal | None
        if usa_f:
            local = _num(ctx.an.valor(celda_f))
            donde = celda_f
        else:
            m = re.search(r"\*\s*(\d*\.?\d+)\s*$", f_g or "")
            local = Decimal(m.group(1)) if m else _num(ctx.an.valor(celda_f))
            donde = celda_g if m else celda_f
        if local is None or local == global_:
            continue
        base = apu.guardados.get(base_r)
        impacto = _centavos((global_ - local) * base * p.cantidad) if base is not None else None
        out.append(
            Hallazgo(
                regla="L6",
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"A confirmar: la {texto} de {apu.hoja} (partida {p.numero}) está escrita a "
                    f"mano en {donde} = {_fu(local)}, en lugar de leer el parámetro global "
                    f"{nombre} ({_fu(global_)}). "
                    + (
                        f"Con el parámetro global la partida cambiaría en {_fmt(impacto)} USD sin "
                        "IVA (informativo). "
                        if impacto is not None
                        else ""
                    )
                    + "Puede ser intencional: la devolución conserva el valor escrito."
                ),
                impacto=impacto,
                origen_ids=tuple(dict.fromkeys((str(donde), str(celda_g)))),
                valor_observado=local,
                valor_esperado=global_,
            )
        )
    return out


def _l6_rendimiento(ctx: _Contexto, apu: ApuLeido, p: PartidaLeida) -> list[Hallazgo]:
    rend = apu.guardados.get(Rotulo.REND)
    celda_rend = apu.rotulos.get(Rotulo.REND)
    celda_mat = apu.rotulos.get(Rotulo.MAT)
    filas_mo_eq = [_partir(ln.celda_codigo.ref)[1] for ln in apu.lineas if ln.tipo.value != "MT"]
    if rend is None or celda_rend is None or not filas_mo_eq:
        return []
    desde = min(filas_mo_eq)
    hasta = _partir(celda_mat.ref)[1] if celda_mat is not None else 10**6
    distintos: dict[Decimal, list[str]] = defaultdict(list)
    for k in ctx.formulas_de.get(apu.hoja, ()):
        if not desde <= _partir(k.split("!", 1)[1])[1] < hasta:
            continue
        for m in _RX_DIVISOR_LITERAL.finditer(_sin_textos(ctx.libro.formulas[k])):
            distintos[Decimal(m.group(1))].append(k)
    out: list[Hallazgo] = []
    for literal in sorted(distintos):
        celdas = list(dict.fromkeys(distintos[literal]))
        if literal == rend:
            sev, intro = Severidad.INFO, "Rendimiento escrito dentro de fórmulas, igual al del APU"
            efecto = "Hoy da lo mismo, pero si cambia el rendimiento esas celdas no lo siguen."
        else:
            sev, intro = (
                Severidad.ADVERTENCIA,
                "A confirmar: rendimiento escrito dentro de fórmulas",
            )
            efecto = (
                f"Esas celdas dividen entre {_fu(literal)} y no entre el rendimiento del APU "
                f"({celda_rend} = {_fu(rend)}): el costo por unidad de equipos o consumo no sigue "
                "al rendimiento."
            )
        out.append(
            Hallazgo(
                regla="L6",
                severidad=sev,
                descripcion=(
                    f"{intro} en {apu.hoja} (partida {p.numero}): "
                    f"{', '.join(c.split('!', 1)[1] for c in celdas)} usan «/{_fu(literal)}». "
                    + efecto
                ),
                origen_ids=(*celdas, str(celda_rend)),
                valor_observado=literal,
                valor_esperado=rend,
            )
        )
    return out


def _l6(ctx: _Contexto) -> list[Hallazgo]:
    out: list[Hallazgo] = []
    for apu in ctx.libro.apus:
        p = ctx.partida_de_apu.get(apu.hoja)
        if p is None:
            continue
        out.extend(_l6_porcentajes(ctx, apu, p))
        out.extend(_l6_rendimiento(ctx, apu, p))
    return out


# --- L7 Dato dentro de fórmula --------------------------------------------------------------------


def _l7(ctx: _Contexto) -> list[Hallazgo]:
    hoja = ctx.an.hoja(ctx.perfil.hoja("MEDICIONES"))
    if hoja is None:
        return []
    secciones: dict[str, list[str]] = {}
    for k in ctx.formulas_de.get(hoja, ()):
        f = _sin_textos(ctx.libro.formulas[k])
        if not (_RX_ARIT_LITERALES.search(f) or _RX_FACTOR_DECIMAL.search(f)):
            continue
        fila = _partir(k.split("!", 1)[1])[1]
        seccion = next(
            (
                t
                for x in range(fila, 0, -1)
                if _RX_SECCION.match(t := ctx.etiqueta(hoja, x, hasta_col=1))
            ),
            hoja,
        )
        secciones.setdefault(seccion, []).append(k)
    out: list[Hallazgo] = []
    for seccion, celdas in secciones.items():
        ejemplos = "; ".join(
            f"{c.split('!', 1)[1]} {ctx.libro.formulas[c]}" for c in celdas[:4]
        ) + ("; …" if len(celdas) > 4 else "")
        out.append(
            Hallazgo(
                regla="L7",
                severidad=Severidad.INFO,
                descripcion=(
                    f"{hoja}, sección «{seccion[:60]}»: {len(celdas)} fórmula(s) con medidas o "
                    f"factores escritos dentro ({ejemplos}). Efecto: esos datos no tienen celda "
                    "propia ni fuente, y no se pueden revisar ni rastrear."
                ),
                origen_ids=tuple(celdas),
            )
        )
    return out


# --- L8 Número de partida duplicado ---------------------------------------------------------------


def _l8(ctx: _Contexto) -> list[Hallazgo]:
    por_numero: dict[int, list[PartidaLeida]] = defaultdict(list)
    for p in ctx.libro.partidas:
        por_numero[p.numero].append(p)
    duplicados = {n: ps for n, ps in por_numero.items() if len(ps) > 1}
    if not duplicados:
        return []
    col_num = ctx.perfil.columnas_presupuesto["numero"]
    rx_pres = re.compile(
        rf"(?:'{re.escape(ctx.h_pres)}'|{re.escape(ctx.h_pres)})!\$?{col_num}\$?\d", re.I
    )
    con_match: set[str] = set()
    con_suma: set[str] = set()
    for k, f in ctx.libro.formulas.items():
        hoja = k.split("!", 1)[0]
        if hoja == ctx.h_pres or not rx_pres.search(f):
            continue
        fu = f.upper()
        if "MATCH(" in fu or "VLOOKUP(" in fu or "LOOKUP(" in fu:
            con_match.add(hoja)
        if "SUMIF" in fu:
            con_suma.add(hoja)
    orden = ctx.libro.hojas.index
    efectos: list[str] = []
    if con_match:
        efectos.append(
            f"{', '.join(sorted(con_match, key=orden))} buscan la partida por número (MATCH) y "
            "toman siempre la primera fila"
        )
    if con_suma:
        efectos.append(
            f"{', '.join(sorted(con_suma, key=orden))} suman por número (SUMIF) y mezclan las "
            "filas repetidas"
        )
    efecto = (
        "; ".join(efectos) + "."
        if efectos
        else "Ninguna hoja derivada busca por número en este libro, pero el número repetido "
        "confunde la lectura del presupuesto y de cualquier hoja que se agregue."
    )
    out: list[Hallazgo] = []
    for n in sorted(duplicados):
        ps = duplicados[n]
        filas = ", ".join(
            f"fila {p.fila} («{p.descripcion[:40]}», cantidad {_fu(p.cantidad)})" for p in ps
        )
        out.append(
            Hallazgo(
                regla="L8",
                severidad=Severidad.ADVERTENCIA,
                descripcion=f"El número de partida {n} se repite en {ctx.h_pres}: {filas}. "
                + efecto,
                origen_ids=tuple(f"{ctx.h_pres}!{col_num}{p.fila}" for p in ps),
            )
        )
    return out


# --- L9 Cuadre interno ----------------------------------------------------------------------------


def _l9_presupuesto(ctx: _Contexto) -> list[Hallazgo]:
    letra = dict(zip(_ORDEN_DESGLOSE, ctx.perfil.columnas_desglose, strict=False))
    col_ver = ctx.perfil.columnas_presupuesto["verificacion"]
    reglas = (
        ((Rotulo.MAT, Rotulo.MO, Rotulo.EQ, Rotulo.TR), Rotulo.CD),
        ((Rotulo.CD, Rotulo.ADM), Rotulo.SUB),
        ((Rotulo.SUB, Rotulo.UTI), Rotulo.PU),
    )
    out: list[Hallazgo] = []
    for p in ctx.libro.partidas:
        g = p.guardados
        cuadro_pu = True
        for sumandos, total in reglas:
            lt = letra[total]
            if lt not in g or not any(letra[s] in g for s in sumandos):
                continue
            suma = sum((g.get(letra[s], _CERO) for s in sumandos), _CERO)
            dif = suma - g[lt]
            if abs(dif) <= _TOL_CUADRE:
                continue
            if total is Rotulo.PU:
                cuadro_pu = False
            cols = "+".join(letra[s] for s in sumandos)
            impacto = _centavos(dif * p.cantidad)
            out.append(
                Hallazgo(
                    regla="L9",
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"Desglose de la partida {p.numero} (fila {p.fila} de {ctx.h_pres}): "
                        f"{cols} = {_fu(suma)} USD/u, pero {lt}{p.fila} "
                        f"({_NOMBRE_ROTULO[total]}) = {_fu(g[lt])}; diferencia {_fu(dif)} USD/u. "
                        f"Efecto: con la cantidad {_fu(p.cantidad)}, {_fmt(impacto)} USD que el "
                        "desglose muestra y el total no cobra (o al revés)."
                    ),
                    impacto=impacto,
                    origen_ids=tuple(f"{ctx.h_pres}!{letra[s]}{p.fila}" for s in sumandos)
                    + (f"{ctx.h_pres}!{lt}{p.fila}",),
                    valor_observado=g[lt],
                    valor_esperado=suma,
                )
            )
        celda_r = Celda(ctx.h_pres, f"{col_ver}{p.fila}")
        r = _num(ctx.an.valor(celda_r))
        if cuadro_pu and r is not None and abs(r) >= _TOL_CENTAVO:
            out.append(
                Hallazgo(
                    regla="L9",
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"La verificación {celda_r} de la partida {p.numero} vale {_fu(r)} "
                        "(debería ser 0)."
                    ),
                    impacto=_centavos(r * p.cantidad),
                    origen_ids=(str(celda_r),),
                    valor_observado=r,
                    valor_esperado=_CERO,
                )
            )
    return out


def _celdas_con_formula(ctx: _Contexto, hoja: str) -> Iterator[tuple[str, int, Decimal]]:
    for k in ctx.formulas_de.get(hoja, ()):
        v = _num(ctx.libro.valores.get(k))
        if v is not None:
            yield k, _partir(k.split("!", 1)[1])[1], v


def _l9_dif(ctx: _Contexto, logica: str, prefijos: tuple[str, ...], que: str) -> list[Hallazgo]:
    hoja = ctx.an.hoja(ctx.perfil.hoja(logica))
    if hoja is None:
        return []
    out: list[Hallazgo] = []
    for k, fila, v in _celdas_con_formula(ctx, hoja):
        etiqueta = ctx.etiqueta(hoja, fila)
        if not any(normalizar(etiqueta).startswith(normalizar(x)) for x in prefijos):
            continue
        if abs(v) < _TOL_CENTAVO:
            continue
        out.append(
            Hallazgo(
                regla="L9",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{k} «{etiqueta[:70]}» vale {_fmt(v)} USD (debería ser 0). Efecto: {que}"
                ),
                impacto=_centavos(v),
                origen_ids=(k,),
                valor_observado=v,
                valor_esperado=_CERO,
            )
        )
    return out


def _l9_resumen(ctx: _Contexto) -> list[Hallazgo]:
    hoja = ctx.an.hoja(ctx.perfil.hoja("RESUMEN"))
    nombre_sub = ctx.perfil.nombres_totales[0]
    celda_sub = ctx.an.nombre_a_celda(nombre_sub)
    sub = ctx.libro.totales.get(nombre_sub)
    if hoja is None or sub is None:
        return []
    out: list[Hallazgo] = []
    for k, fila, v in _celdas_con_formula(ctx, hoja):
        f = ctx.libro.formulas[k]
        m = re.fullmatch(
            r"=\s*SUM\(\s*\$?([A-Z]{1,3})\$?(\d+)\s*:\s*\$?([A-Z]{1,3})\$?(\d+)\s*\)", f
        )
        etiqueta = normalizar(ctx.etiqueta(hoja, fila))
        es_composicion = es_costo = False
        if m is not None and m.group(1) == m.group(3):
            fs = [
                ctx.libro.formulas.get(f"{hoja}!{m.group(1)}{x}", "").upper()
                for x in range(int(m.group(2)), int(m.group(4)) + 1)
            ]
            es_composicion = sum("SUMPRODUCT(" in x for x in fs) >= 2
            # El costo de la obra suma montos que leen PRESUPUESTO, no pesos en %.
            es_costo = etiqueta.startswith("costo de la obra") and any(
                normalizar(ctx.h_pres) in normalizar(x) for x in fs
            )
        if not (es_composicion or es_costo):
            continue
        dif = v - sub
        if abs(dif) < _TOL_CENTAVO:
            continue
        que = "el total de la composición del costo" if es_composicion else "el costo de la obra"
        out.append(
            Hallazgo(
                regla="L9",
                severidad=Severidad.ERROR,
                descripcion=(
                    f"{k} ({que}) suma {_fmt(v)} USD, pero el subtotal sin IVA del presupuesto "
                    f"({nombre_sub}"
                    + (f", {celda_sub}" if celda_sub else "")
                    + f") es {_fmt(sub)} USD: la hoja no cuadra por {_fmt(dif)} USD. Efecto: algún "
                    "componente que el desglose muestra no está en el total (o al revés)."
                ),
                impacto=_centavos(dif),
                origen_ids=(k,) + ((str(celda_sub),) if celda_sub else ()),
                valor_observado=v,
                valor_esperado=sub,
            )
        )
    return out


def _l9(ctx: _Contexto) -> list[Hallazgo]:
    return (
        _l9_presupuesto(ctx)
        + _l9_resumen(ctx)
        + _l9_dif(
            ctx,
            "PROCURA",
            ("Dif.",),
            "la lista de compras no corresponde al presupuesto (se compraría de más o de menos).",
        )
        + _l9_dif(
            ctx,
            "PLAN DE PAGOS",
            ("Verificación",),
            "el plan de pagos no suma el total del presupuesto.",
        )
    )


# --- Entrada pública ------------------------------------------------------------------------------


_REGLAS = (_l1, _l2, _l3, _l4, _l5, _l6, _l7, _l8, _l9)


def reglas_del_libro(libro: LibroLeido, perfil: Perfil | None = None) -> list[Hallazgo]:
    """Aplica L1-L9 al libro y devuelve los hallazgos en orden de regla y de celda.

    `perfil` es la plantilla con que se leyó el libro (por defecto `libro.perfil`). Las reglas no
    modifican el libro ni lanzan por una rareza: lo que no se puede juzgar se omite (ver los
    límites declarados en la cabecera del módulo).
    """
    ctx = _Contexto(libro, perfil or cargar_perfil(libro.perfil))
    hallazgos: list[Hallazgo] = []
    for regla in _REGLAS:
        hallazgos.extend(regla(ctx))
    return hallazgos
