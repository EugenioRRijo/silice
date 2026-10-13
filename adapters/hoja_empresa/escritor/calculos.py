"""Calculador de fórmulas en `Decimal` para los valores guardados del libro devuelto.

XlsxWriter guarda cada fórmula con el valor que se le dé; ese valor tiene que ser el que daría Excel
(spec 1.5, F-D3: "valores guardados iguales a los de Silice"). Este módulo evalúa las fórmulas del
libro devuelto sobre el modelo en memoria (`hoja.LibroSalida`):

- las celdas sembradas (`fijo`) valen lo que calculó Silice: P.U., componentes de cada APU,
  cantidades y totales;
- el resto (descripciones por VLOOKUP, subtotales, montos, hojas derivadas) se calcula aquí, con la
  semántica de Excel para el subconjunto de funciones que usa la plantilla de la empresa.

Toda la aritmética es `Decimal` (NORMAS §2.3). Una función que el calculador no conoce lanza
`NoSoportado`; la celda toma entonces su valor guardado del libro recibido y queda anotada.

Semántica de Excel que se respeta: vacío = 0 en aritmética y "" en texto; comparación de textos sin
distinguir mayúsculas; números < textos < lógicos al comparar tipos distintos; errores que se
propagan (salvo en IFERROR/ISERROR); ROUND y ROUNDUP alejándose del cero; intersección implícita
cuando un rango se usa como escalar; `#NUM!` cuando un número sale del rango de Excel (desborde) y
`#VALUE!` cuando un texto pasa de 32 767 caracteres.

Defensas ante un libro hostil (revisión de seguridad 1.5). El libro viene de fuera y una fórmula
puede pedir un trabajo desmedido; ninguna defensa cambia el valor de una fórmula que termina:

- Los rangos se RECORREN solo hasta la última fila y columna usadas de la hoja destino: más allá
  todas las celdas están vacías, y lo que aportan se calcula sin visitarlas (COUNTIF cuenta las
  vacías de una vez). El rango conserva su tamaño nominal, porque la intersección implícita, INDEX,
  el número de columna de VLOOKUP y la forma de SUMPRODUCT dependen de él.
- Un presupuesto de celdas visitadas (`MAX_VISITAS`) y de tiempo (`MAX_SEGUNDOS`) por libro, y una
  profundidad máxima de referencias encadenadas (`MAX_PROFUNDIDAD`). Al pasarse, la fórmula se
  corta ENTERA (`NoSoportado`): la celda más externa toma su valor guardado del libro recibido y
  queda anotada, en vez de calcularse a medias con un número equivocado.
- Los números fuera del rango de Excel dan `#NUM!` (nunca se convierten a entero: `int()` de un
  `Decimal` de mil millones de cifras no termina) y los comodines de COUNTIF/SUMIF/MATCH/VLOOKUP se
  comparan sin expresiones regulares (un patrón como `*a*a*a*a*b` hacía retroceder sin fin).
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal, InvalidOperation
from typing import Any

from openpyxl.formula.tokenizer import Token

from adapters.hoja_empresa.escritor.formulas import MAX_COL, MAX_FILA, Ref, analizar_ref, tokens
from adapters.hoja_empresa.escritor.hoja import NADA, LibroSalida

__all__ = [
    "MAX_PROFUNDIDAD",
    "MAX_SEGUNDOS",
    "MAX_VISITAS",
    "Err",
    "Evaluador",
    "NoSoportado",
    "a_numero",
    "texto_general",
]

_CERO = Decimal(0)
_UNO = Decimal(1)
_EPOCA = datetime(1899, 12, 30)

#: Celdas que un `Evaluador` visita como máximo en todo el libro (cada lectura de una celda cuenta,
#: también las que ya estaban calculadas). SUPUESTO_DECLARADO (revisión de seguridad 1.5): la
#: devolución del libro real más grande visita del orden de cien mil celdas; cinco millones dejan
#: un margen de decenas de veces y se recorren en pocos segundos.
MAX_VISITAS = 5_000_000
#: Segundos de cálculo por libro (`time.monotonic`, desde la primera celda visitada).
#: SUPUESTO_DECLARADO (revisión de seguridad 1.5): un libro real se calcula en menos de un segundo;
#: 30 s es lo más que se hace esperar al usuario antes de conservar los valores guardados.
MAX_SEGUNDOS = 30.0
#: Celdas con fórmula anidadas como máximo (A1 usa A2, que usa A3...). SUPUESTO_DECLARADO (revisión
#: de seguridad 1.5): cada nivel ocupa entre 5 y 10 marcos de la pila de Python, cuyo límite es
#: 1 000; con 80 niveles el corte llega antes que el `RecursionError` y no depende de quién llame.
#: Los libros reales no pasan de unos pocos niveles porque se evalúan fila por fila y lo calculado
#: queda en memoria.
MAX_PROFUNDIDAD = 80
#: Exponente decimal máximo de un número de Excel (doble IEEE: 1,8E+308). Fuera de él, `#NUM!`; por
#: debajo de 1E-308, cero.
_MAX_EXPONENTE = 308
#: Caracteres máximos de un texto: el límite de una celda que Microsoft publica en "Especificaciones
#: y límites de Excel" (32 767). Pasarlo da `#VALUE!`, como en Excel; además impide que una cadena
#: A2=A1&A1, A3=A2&A2... duplique el texto en cada fila hasta agotar la memoria.
_MAX_TEXTO = 32767
_MOTIVO_PROFUNDO = f"cadena de referencias de más de {MAX_PROFUNDIDAD} niveles"


class NoSoportado(Exception):  # noqa: N818
    """La fórmula usa algo que el calculador no implementa."""


class _Corte(NoSoportado):
    """La fórmula no se calcula ENTERA: se agotó el presupuesto de celdas o de tiempo, o la cadena
    de referencias es demasiado profunda.

    A diferencia de un `NoSoportado` corriente, las celdas intermedias no lo atrapan (tomarían su
    valor guardado y la de arriba se calcularía a medias, con un número equivocado): sube hasta la
    celda más externa, que es la que conserva su valor guardado y queda anotada.
    """


@dataclass(frozen=True, slots=True)
class Err:
    codigo: str

    def __str__(self) -> str:
        return self.codigo


_DIV0 = Err("#DIV/0!")
_VALOR = Err("#VALUE!")
_NA = Err("#N/A")
_REF = Err("#REF!")
_NUM = Err("#NUM!")
_NOMBRE = Err("#NAME?")


class _Propaga(Exception):  # noqa: N818
    def __init__(self, err: Err) -> None:
        self.err = err


@dataclass(frozen=True, slots=True)
class Rango:
    hoja: str
    f1: int
    c1: int
    f2: int
    c2: int

    @property
    def filas(self) -> int:
        return self.f2 - self.f1 + 1

    @property
    def cols(self) -> int:
        return self.c2 - self.c1 + 1


# --- Conversión ----------------------------------------------------------------------------------


def a_numero(v: object) -> Decimal:
    """Coerción aritmética de Excel; lanza _Propaga si no es posible."""
    if isinstance(v, Err):
        raise _Propaga(v)
    if v is None:
        return _CERO
    if isinstance(v, bool):
        return _UNO if v else _CERO
    if isinstance(v, Decimal):
        return v
    if isinstance(v, int | float):
        return Decimal(str(v))
    if isinstance(v, datetime | date):
        return _serial(v)
    if isinstance(v, str):
        n = _texto_a_numero(v)
        if n is None:
            raise _Propaga(_VALOR)
        return n
    raise _Propaga(_VALOR)


def _serial(v: datetime | date) -> Decimal:
    if not isinstance(v, datetime):
        v = datetime(v.year, v.month, v.day)
    delta = v - _EPOCA
    return Decimal(delta.days) + Decimal(delta.seconds) / Decimal(86400)


def _texto_a_numero(s: str) -> Decimal | None:
    t = s.strip().replace(",", "")
    if not t:
        return None
    pct = t.endswith("%")
    if pct:
        t = t[:-1]
    try:
        n = Decimal(t)
    except InvalidOperation:
        return None
    if not n.is_finite():
        return None
    if n and n.adjusted() > _MAX_EXPONENTE:
        return None  # VALUE("1E999") es #VALUE! en Excel
    if n and n.adjusted() < -_MAX_EXPONENTE:
        return _CERO
    return n / 100 if pct else n


def _acotar(n: Decimal) -> Decimal:
    """Un resultado numérico dentro del rango de Excel: `#NUM!` si se desborda, cero si es menor
    que el número positivo más pequeño."""
    if not n.is_finite():
        raise _Propaga(_NUM)
    if n:
        e = n.adjusted()
        if e > _MAX_EXPONENTE:
            raise _Propaga(_NUM)
        if e < -_MAX_EXPONENTE:
            return _CERO
    return n


def _texto_acotado(t: str) -> str:
    if len(t) > _MAX_TEXTO:
        raise _Propaga(_VALOR)
    return t


def _coincide(texto: str, patron: str) -> bool:
    """Comodines de Excel (`*` cualquier tira, `?` un carácter) sin expresiones regulares.

    Algoritmo de dos punteros con vuelta a la última estrella: a lo sumo len(texto) × len(patron)
    pasos, nunca el retroceso exponencial de `re` con varias `.*`. Ambos textos llegan ya en
    `casefold`.
    """
    t = p = 0
    estrella, marca = -1, 0
    while t < len(texto):
        if p < len(patron) and patron[p] == "*":
            estrella, marca = p, t
            p += 1
        elif p < len(patron) and (patron[p] == "?" or patron[p] == texto[t]):
            t += 1
            p += 1
        elif estrella >= 0:
            marca += 1
            t, p = marca, estrella + 1
        else:
            return False
    while p < len(patron) and patron[p] == "*":
        p += 1
    return p == len(patron)


def texto_general(v: object) -> str:
    """Un valor como lo concatena Excel con '&' (formato General, hasta 15 cifras)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, Decimal):
        if v == v.to_integral_value():
            return str(int(v))
        d = v
        if d.adjusted() < 15:
            cifras = 15 - d.adjusted() - 1
            d = d.quantize(Decimal(1).scaleb(-max(cifras, 0)), rounding=ROUND_HALF_UP)
        t = format(d.normalize(), "f")
        return t
    if isinstance(v, datetime | date):
        return texto_general(_serial(v))
    return str(v)


def _a_texto(v: object) -> str:
    if isinstance(v, Err):
        raise _Propaga(v)
    return texto_general(v)


def _a_bool(v: object) -> bool:
    if isinstance(v, Err):
        raise _Propaga(v)
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, Decimal | int | float):
        return v != 0
    if isinstance(v, str):
        u = v.strip().upper()
        if u == "TRUE":
            return True
        if u == "FALSE":
            return False
    raise _Propaga(_VALOR)


def _rango_tipo(v: object) -> int:
    if isinstance(v, bool):
        return 2
    if isinstance(v, str):
        return 1
    return 0


def _comparar(a: object, b: object) -> int:
    """-1, 0 o 1 con las reglas de Excel (vacío según el otro operando)."""
    if isinstance(a, Err):
        raise _Propaga(a)
    if isinstance(b, Err):
        raise _Propaga(b)
    if a is None:
        a = "" if isinstance(b, str) else False if isinstance(b, bool) else _CERO
    if b is None:
        b = "" if isinstance(a, str) else False if isinstance(a, bool) else _CERO
    if isinstance(a, datetime | date):
        a = _serial(a)
    if isinstance(b, datetime | date):
        b = _serial(b)
    ta, tb = _rango_tipo(a), _rango_tipo(b)
    if ta != tb:
        return -1 if ta < tb else 1
    if ta == 1:
        x, y = str(a).casefold(), str(b).casefold()
    else:
        x, y = a, b  # type: ignore[assignment]
    if x == y:
        return 0
    return -1 if x < y else 1  # type: ignore[operator]


def _redondear(n: Decimal, digitos: int, modo: str) -> Decimal:
    q = Decimal(1).scaleb(-digitos)
    try:
        return n.quantize(q, rounding=modo)
    except InvalidOperation as exc:
        raise _Propaga(_NUM) from exc


# --- Análisis sintáctico -------------------------------------------------------------------------

_PRECEDENCIA = {
    "=": 1,
    "<>": 1,
    "<": 1,
    ">": 1,
    "<=": 1,
    ">=": 1,
    "&": 2,
    "+": 3,
    "-": 3,
    "*": 4,
    "/": 4,
    "^": 5,
}


class _Analizador:
    def __init__(self, formula: str) -> None:
        self.t = [x for x in tokens(formula) if x.type != Token.WSPACE]
        self.i = 0

    def _ver(self) -> Token | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def _tomar(self) -> Token:
        t = self.t[self.i]
        self.i += 1
        return t

    def analizar(self) -> tuple:
        if not self.t:
            return ("n", _CERO)
        nodo = self._expr(0)
        if self.i != len(self.t):
            raise NoSoportado("sobran tokens")
        return nodo

    def _expr(self, minimo: int) -> tuple:
        izq = self._unario()
        while True:
            t = self._ver()
            if t is None or t.type != Token.OP_IN:
                return izq
            if t.value == ":":
                raise NoSoportado("operador de rango")
            p = _PRECEDENCIA.get(t.value)
            if p is None:
                raise NoSoportado(f"operador {t.value}")
            if p < minimo:
                return izq
            self._tomar()
            der = self._expr(p + 1)
            izq = ("bin", t.value, izq, der)

    def _unario(self) -> tuple:
        t = self._ver()
        if t is not None and t.type == Token.OP_PRE:
            self._tomar()
            return ("u", t.value, self._unario())
        x = self._primario()
        while (t := self._ver()) is not None and t.type == Token.OP_POST:
            self._tomar()
            x = ("pct", x)
        return x

    def _primario(self) -> tuple:
        t = self._tomar()
        if t.type == Token.OPERAND:
            if t.subtype == Token.NUMBER:
                n = Decimal(t.value)
                if n and n.adjusted() > _MAX_EXPONENTE:
                    return ("e", "#NUM!")  # Excel no admite 1E999 en una fórmula
                return ("n", n if not n or n.adjusted() >= -_MAX_EXPONENTE else _CERO)
            if t.subtype == Token.TEXT:
                return ("s", t.value[1:-1].replace('""', '"'))
            if t.subtype == Token.LOGICAL:
                return ("b", t.value.upper() == "TRUE")
            if t.subtype == Token.ERROR:
                return ("e", t.value.upper())
            if t.subtype == Token.RANGE:
                r = analizar_ref(t.value)
                if r is None:
                    raise NoSoportado(f"referencia {t.value}")
                if isinstance(r, str):
                    return ("nom", r)
                return ("ref", r)
            raise NoSoportado("operando")
        if t.type == Token.FUNC and t.subtype == Token.OPEN:
            nombre = t.value[:-1].upper()
            if nombre.startswith("_XLFN."):
                nombre = nombre[6:]
            args: list[tuple | None] = []
            if (s := self._ver()) is not None and s.type == Token.FUNC and s.subtype == Token.CLOSE:
                self._tomar()
                return ("f", nombre, args)
            while True:
                s = self._ver()
                if s is not None and (
                    (s.type == Token.SEP and s.subtype == Token.ARG)
                    or (s.type == Token.FUNC and s.subtype == Token.CLOSE)
                ):
                    args.append(None)
                else:
                    args.append(self._expr(0))
                s = self._tomar()
                if s.type == Token.FUNC and s.subtype == Token.CLOSE:
                    return ("f", nombre, args)
                if not (s.type == Token.SEP and s.subtype == Token.ARG):
                    raise NoSoportado("argumentos")
        if t.type == Token.PAREN and t.subtype == Token.OPEN:
            x = self._expr(0)
            c = self._tomar()
            if c.type != Token.PAREN:
                raise NoSoportado("paréntesis")
            return x
        raise NoSoportado(f"token {t.value}")


# --- Evaluador -----------------------------------------------------------------------------------


def _clave_nombre(nombre: str) -> str:
    """''CONTROL DE GASTOS'!PRECIOS' y 'CONTROL DE GASTOS!PRECIOS' → la misma clave."""
    if "!" in nombre:
        hoja, _, local = nombre.rpartition("!")
        if hoja.startswith("'") and hoja.endswith("'"):
            hoja = hoja[1:-1].replace("''", "'")
        return f"{hoja}!{local}".upper()
    return nombre.upper()


class Evaluador:
    """Evalúa celdas del `LibroSalida` con memoria. `nombres`: nombre → texto ('=HOJA!$A$1')."""

    def __init__(self, libro: LibroSalida, nombres: dict[str, str]) -> None:
        self.libro = libro
        self.nombres = {_clave_nombre(k): v for k, v in nombres.items()}
        self._memo: dict[tuple[str, int, int], object] = {}
        self._curso: set[tuple[str, int, int]] = set()
        self._ast: dict[str, tuple] = {}
        self._ctx: list[tuple[str, int, int]] = []
        self.rota_blanca = False
        self.respaldos: list[tuple[str, int, int, str]] = []
        self._max: dict[str, tuple[int, int, int]] = {}
        # Presupuesto de todo el libro: `olvidar` no lo repone.
        self._visitas = 0
        self._inicio: float | None = None
        self._agotado: str | None = None

    def olvidar(self) -> None:
        self._memo.clear()
        self._max.clear()

    # -- celdas --

    def _gastar(self) -> None:
        """Cuenta una visita; al agotarse el presupuesto, corta la fórmula en curso.

        Solo corta si hay una fórmula en curso (`_ctx`): la celda más externa nunca lanza, toma su
        valor guardado. El reloj se mira cada 1 024 visitas para que medir no cueste.
        """
        self._visitas += 1
        if self._agotado is None:
            if self._inicio is None:
                self._inicio = time.monotonic()
            if self._visitas > MAX_VISITAS:
                self._agotado = (
                    f"se agotó el presupuesto de cálculo ({MAX_VISITAS:,} celdas visitadas)"
                ).replace(",", ".")
            elif not self._visitas & 0x3FF and time.monotonic() - self._inicio > MAX_SEGUNDOS:
                self._agotado = f"se agotó el tiempo de cálculo ({MAX_SEGUNDOS:g} s por libro)"
        if self._agotado is not None and self._ctx:
            raise _Corte(self._agotado)

    def _conservar(self, hoja: str, f: int, c: int, respaldo: object, motivo: str) -> object:
        self.respaldos.append((hoja, f, c, motivo))
        return respaldo

    def celda(self, hoja: str, f: int, c: int) -> object:
        clave = (hoja, f, c)
        self._gastar()
        if clave in self._memo:
            return self._memo[clave]
        h = self.libro.hojas.get(hoja)
        cel = h.celdas.get((f, c)) if h is not None else None
        if cel is None:
            return None
        if cel.fijo is not NADA:
            v = cel.fijo
        elif cel.formula:
            if clave in self._curso:
                return Err("#CIRC")
            if self._agotado is not None:  # solo llega aquí la celda más externa
                v = self._conservar(hoja, f, c, cel.respaldo, self._agotado)
            elif len(self._curso) >= MAX_PROFUNDIDAD:
                raise _Corte(_MOTIVO_PROFUNDO)  # hay celdas en curso: alguna la contiene
            else:
                self._curso.add(clave)
                try:
                    v = self.formula(cel.formula, hoja, f, c)
                except _Corte as exc:
                    if self._ctx:  # una fórmula contiene a esta: el corte sube entero
                        raise
                    v = self._conservar(hoja, f, c, cel.respaldo, str(exc))
                except RecursionError:
                    if self._ctx:
                        raise _Corte(_MOTIVO_PROFUNDO) from None
                    v = self._conservar(hoja, f, c, cel.respaldo, _MOTIVO_PROFUNDO)
                except NoSoportado as exc:
                    v = self._conservar(hoja, f, c, cel.respaldo, str(exc) or type(exc).__name__)
                except ArithmeticError:  # desborde de Decimal que escapó: Excel da #NUM!
                    v = _NUM
                finally:
                    self._curso.discard(clave)
        else:
            v = cel.valor
            if isinstance(v, int | float) and not isinstance(v, bool):
                v = Decimal(str(v))
        self._memo[clave] = v
        return v

    def formula(self, formula: str, hoja: str, f: int = 0, c: int = 0) -> object:
        """Valor escalar de una fórmula evaluada en la celda (hoja, f, c)."""
        ast = self._ast.get(formula)
        if ast is None:
            ast = _Analizador(formula).analizar()
            self._ast[formula] = ast
        self._ctx.append((hoja, f, c))
        try:
            try:
                v = self._ev(ast)
                v = self._escalar(v)
            except _Propaga as p:
                v = p.err
            except ArithmeticError:  # decimal.Overflow, InvalidOperation...: como Excel, #NUM!
                v = _NUM
        finally:
            self._ctx.pop()
        if v is None:
            return _CERO
        return v

    # -- núcleo --

    @property
    def _hoja(self) -> str:
        return self._ctx[-1][0]

    def _maximo(self, hoja: str) -> tuple[int, int]:
        """Última fila y columna usadas de la hoja, en memoria mientras no cambie su número de
        celdas: de ellas depende qué parte de cada rango se recorre (`_usado`), así que una celda
        añadida después de calcularlas no puede quedar fuera."""
        h = self.libro.hojas.get(hoja)
        if h is None:
            return 0, 0
        m = self._max.get(hoja)
        if m is None or m[0] != len(h.celdas):
            m = (len(h.celdas), h.max_fila, h.max_col)
            self._max[hoja] = m
        return m[1], m[2]

    def _usado(self, r: Rango) -> tuple[int, int]:
        """Filas y columnas del rango, desde su esquina, que caen dentro de lo usado de su hoja.

        Más allá todas las celdas están vacías: recorrer solo esto da el mismo resultado y acota el
        trabajo de `=COUNTIF(A1:XFC1000000;">0")` a lo que la hoja tiene.
        """
        mf, mc = self._maximo(r.hoja)
        return max(0, min(r.f2, mf) - r.f1 + 1), max(0, min(r.c2, mc) - r.c1 + 1)

    def _rango_de_ref(self, r: Ref) -> Rango | Err:
        if r.externa:
            return _REF
        if r.rota:
            return _REF
        hoja = r.hoja if r.hoja is not None else self._hoja
        if hoja not in self.libro.hojas:
            return _REF
        f2, c2 = r.f2, r.c2
        if f2 == MAX_FILA or c2 == MAX_COL:
            mf, mc = self._maximo(hoja)
            f2 = min(f2, max(mf, r.f1))
            c2 = min(c2, max(mc, r.c1))
        return Rango(hoja, r.f1, r.c1, f2, c2)

    def _nombre(self, nombre: str) -> object:
        texto = self.nombres.get(f"{self._hoja}!{nombre}".upper()) or self.nombres.get(
            nombre.upper()
        )
        if texto is None:
            return _NOMBRE
        texto = texto.lstrip("=")
        r = analizar_ref(texto)
        if isinstance(r, Ref):
            return self._rango_de_ref(r)
        return self._ev(_Analizador("=" + texto).analizar())

    def _escalar(self, v: object) -> object:
        if isinstance(v, Rango):
            if v.filas == 1 and v.cols == 1:
                return self.celda(v.hoja, v.f1, v.c1)
            _, f, c = self._ctx[-1]
            if v.cols == 1 and v.f1 <= f <= v.f2:
                return self.celda(v.hoja, f, v.c1)
            if v.filas == 1 and v.c1 <= c <= v.c2:
                return self.celda(v.hoja, v.f1, c)
            return _VALOR
        return v

    def _val(self, nodo: tuple | None) -> object:
        """Evalúa y reduce a escalar; los errores se devuelven (no se propagan)."""
        if nodo is None:
            return None
        return self._escalar(self._ev(nodo))

    def _ev(self, nodo: tuple) -> object:
        tipo = nodo[0]
        if tipo == "n" or tipo == "s" or tipo == "b":
            return nodo[1]
        if tipo == "e":
            if nodo[1] == "#REF!" and self.rota_blanca:
                return None
            return Err(nodo[1])
        if tipo == "ref":
            r: Ref = nodo[1]
            if r.rota and self.rota_blanca:
                return None
            return self._rango_de_ref(r)
        if tipo == "nom":
            return self._nombre(nodo[1])
        if tipo == "u":
            v = self._val(nodo[2])
            if nodo[1] == "+":
                if isinstance(v, Err):
                    raise _Propaga(v)
                return v  # el + unario de Excel no convierte: =+A1 con texto da el texto
            return _acotar(-a_numero(v))
        if tipo == "pct":
            return _acotar(a_numero(self._val(nodo[1])) / 100)
        if tipo == "bin":
            return self._binario(nodo[1], self._val(nodo[2]), self._val(nodo[3]))
        if tipo == "f":
            v = self._funcion(nodo[1], nodo[2])
            if isinstance(v, Decimal):
                return _acotar(v)
            if isinstance(v, str):
                return _texto_acotado(v)
            return v
        raise NoSoportado(tipo)

    def _binario(self, op: str, a: object, b: object) -> object:
        if op == "&":
            ta, tb = _a_texto(a), _a_texto(b)
            if len(ta) + len(tb) > _MAX_TEXTO:
                raise _Propaga(_VALOR)
            return ta + tb
        if op in ("=", "<>", "<", ">", "<=", ">="):
            k = _comparar(a, b)
            return {
                "=": k == 0,
                "<>": k != 0,
                "<": k < 0,
                ">": k > 0,
                "<=": k <= 0,
                ">=": k >= 0,
            }[op]
        x, y = a_numero(a), a_numero(b)
        try:
            if op == "+":
                return _acotar(x + y)
            if op == "-":
                return _acotar(x - y)
            if op == "*":
                return _acotar(x * y)
            if op == "/":
                if y == 0:
                    raise _Propaga(_DIV0)
                return _acotar(x / y)
            if op == "^":
                if y == y.to_integral_value() and abs(y) < 1000:
                    return _acotar(x ** int(y))
                return _acotar(Decimal(str(math.pow(float(x), float(y)))))
        except (ArithmeticError, ValueError) as exc:  # Overflow, InvalidOperation, dominio de pow
            raise _Propaga(_NUM) from exc
        raise NoSoportado(op)

    # -- rangos --

    def _celdas(self, v: object) -> Iterator[object]:
        """Valores de un argumento: las celdas de un rango, o el escalar mismo.

        De un rango salen solo las celdas de la parte usada (`_usado`): las demás están vacías y
        ninguna función que llama a `_celdas` las cuenta (COUNTIF suma las vacías aparte).
        """
        if isinstance(v, Rango):
            nf, nc = self._usado(v)
            for f in range(v.f1, v.f1 + nf):
                for c in range(v.c1, v.c1 + nc):
                    yield self.celda(v.hoja, f, c)
        else:
            yield v

    # -- funciones --

    def _funcion(self, nombre: str, args: list[tuple | None]) -> object:
        perezosa = _PEREZOSAS.get(nombre)
        if perezosa is not None:
            return perezosa(self, args)
        f = _FUNCIONES.get(nombre)
        if f is None:
            raise NoSoportado(f"función {nombre}")
        valores = [self._ev(a) if a is not None else None for a in args]
        return f(self, valores)


# --- Funciones perezosas -------------------------------------------------------------------------


def _f_if(ev: Evaluador, a: list[tuple | None]) -> object:
    cond = ev._val(a[0])
    if _a_bool(cond):
        return ev._ev(a[1]) if len(a) > 1 and a[1] is not None else (True if len(a) < 2 else _CERO)
    if len(a) > 2:
        return ev._ev(a[2]) if a[2] is not None else _CERO
    return False


def _f_iferror(ev: Evaluador, a: list[tuple | None]) -> object:
    try:
        v = ev._val(a[0])
    except _Propaga as p:
        v = p.err
    except ArithmeticError:
        v = _NUM
    if isinstance(v, Err):
        return ev._ev(a[1]) if len(a) > 1 and a[1] is not None else _CERO
    return v


def _f_iserror(ev: Evaluador, a: list[tuple | None]) -> object:
    try:
        v = ev._val(a[0])
    except (_Propaga, ArithmeticError):
        return True
    return isinstance(v, Err)


def _logicos(ev: Evaluador, a: list[tuple | None]) -> list[bool]:
    """Los valores lógicos de AND/OR: en un rango se ignoran textos y vacíos."""
    out: list[bool] = []
    for x in a:
        v = ev._ev(x) if x is not None else None
        if isinstance(v, Rango):
            out.extend(
                _a_bool(c) for c in ev._celdas(v) if c is not None and not isinstance(c, str)
            )
        else:
            out.append(_a_bool(v))
    return out


def _f_and(ev: Evaluador, a: list[tuple | None]) -> object:
    return all(_logicos(ev, a))


def _f_or(ev: Evaluador, a: list[tuple | None]) -> object:
    return any(_logicos(ev, a))


_PEREZOSAS: dict[str, Callable[[Evaluador, list[tuple | None]], object]] = {
    "IF": _f_if,
    "IFERROR": _f_iferror,
    "ISERROR": _f_iserror,
    "AND": _f_and,
    "OR": _f_or,
}


# --- Funciones con argumentos evaluados ----------------------------------------------------------


def _esc(ev: Evaluador, v: object) -> object:
    return ev._escalar(v)


def _num_arg(ev: Evaluador, v: object) -> Decimal:
    return a_numero(_esc(ev, v))


def _numeros(ev: Evaluador, args: list[object]) -> list[Decimal]:
    """Números para SUM/MIN/MAX: en rangos solo cuentan los números; los escalares se convierten."""
    out: list[Decimal] = []
    for v in args:
        if isinstance(v, Rango):
            for x in ev._celdas(v):
                if isinstance(x, Err):
                    raise _Propaga(x)
                if isinstance(x, Decimal) and not isinstance(x, bool):
                    out.append(x)
        elif v is not None:
            out.append(a_numero(v))
    return out


def _f_sum(ev: Evaluador, a: list[object]) -> object:
    return sum(_numeros(ev, a), _CERO)


def _f_min(ev: Evaluador, a: list[object]) -> object:
    n = _numeros(ev, a)
    return min(n) if n else _CERO


def _f_max(ev: Evaluador, a: list[object]) -> object:
    n = _numeros(ev, a)
    return max(n) if n else _CERO


def _f_average(ev: Evaluador, a: list[object]) -> object:
    n = _numeros(ev, a)
    if not n:
        raise _Propaga(_DIV0)
    return sum(n, _CERO) / len(n)


def _f_count(ev: Evaluador, a: list[object]) -> object:
    return Decimal(
        sum(
            1
            for v in a
            for x in ev._celdas(v)
            if isinstance(x, Decimal) and not isinstance(x, bool)
        )
    )


def _f_counta(ev: Evaluador, a: list[object]) -> object:
    return Decimal(sum(1 for v in a for x in ev._celdas(v) if x is not None and x != ""))


def _f_n(ev: Evaluador, a: list[object]) -> object:
    v = a[0]
    if isinstance(v, Rango):
        v = ev.celda(v.hoja, v.f1, v.c1)
    if isinstance(v, Err):
        raise _Propaga(v)
    if isinstance(v, bool):
        return _UNO if v else _CERO
    if isinstance(v, Decimal):
        return v
    if isinstance(v, datetime | date):
        return _serial(v)
    return _CERO


def _f_round(ev: Evaluador, a: list[object]) -> object:
    return _redondear(
        _num_arg(ev, a[0]), int(_num_arg(ev, a[1]) if len(a) > 1 else 0), ROUND_HALF_UP
    )


def _f_roundup(ev: Evaluador, a: list[object]) -> object:
    return _redondear(_num_arg(ev, a[0]), int(_num_arg(ev, a[1]) if len(a) > 1 else 0), ROUND_UP)


def _f_rounddown(ev: Evaluador, a: list[object]) -> object:
    return _redondear(_num_arg(ev, a[0]), int(_num_arg(ev, a[1]) if len(a) > 1 else 0), ROUND_DOWN)


def _f_int(ev: Evaluador, a: list[object]) -> object:
    from decimal import ROUND_FLOOR

    return _num_arg(ev, a[0]).quantize(_UNO, rounding=ROUND_FLOOR)


def _f_abs(ev: Evaluador, a: list[object]) -> object:
    return abs(_num_arg(ev, a[0]))


def _f_mod(ev: Evaluador, a: list[object]) -> object:
    x, y = _num_arg(ev, a[0]), _num_arg(ev, a[1])
    if y == 0:
        raise _Propaga(_DIV0)
    r = x % y
    if r != 0 and (r < 0) != (y < 0):
        r += y
    return r


def _f_pi(ev: Evaluador, a: list[object]) -> object:
    return Decimal(str(math.pi))


def _f_not(ev: Evaluador, a: list[object]) -> object:
    return not _a_bool(_esc(ev, a[0]))


def _f_true(ev: Evaluador, a: list[object]) -> object:
    return True


def _f_false(ev: Evaluador, a: list[object]) -> object:
    return False


def _f_isblank(ev: Evaluador, a: list[object]) -> object:
    return _esc(ev, a[0]) is None


def _f_isnumber(ev: Evaluador, a: list[object]) -> object:
    v = _esc(ev, a[0])
    return isinstance(v, Decimal) and not isinstance(v, bool)


def _f_istext(ev: Evaluador, a: list[object]) -> object:
    return isinstance(_esc(ev, a[0]), str)


def _f_value(ev: Evaluador, a: list[object]) -> object:
    v = _esc(ev, a[0])
    if isinstance(v, Err):
        raise _Propaga(v)
    if isinstance(v, Decimal):
        return v
    if v is None:
        return _CERO
    n = _texto_a_numero(str(v))
    if n is None:
        raise _Propaga(_VALOR)
    return n


def _f_text(ev: Evaluador, a: list[object]) -> object:
    v = _esc(ev, a[0])
    fmt = _a_texto(_esc(ev, a[1]))
    if isinstance(v, Err):
        raise _Propaga(v)
    if not isinstance(v, Decimal | bool) and not (isinstance(v, str) and _texto_a_numero(v)):
        return _a_texto(v)
    n = a_numero(v)
    return _formatear(n, fmt)


def _formatear(n: Decimal, fmt: str) -> str:
    pct = fmt.endswith("%")
    f = fmt[:-1] if pct else fmt
    if pct:
        n = n * 100
    if not re.fullmatch(r"[#0,]*0(\.0+)?", f):
        raise NoSoportado(f"formato TEXT {fmt}")
    entero, _, dec = f.partition(".")
    nd = len(dec)
    r = _redondear(n, nd, ROUND_HALF_UP)
    signo = "-" if r < 0 else ""
    r = abs(r)
    cuerpo = f"{r:,.{nd}f}" if "," in entero else f"{r:.{nd}f}"
    ceros = entero.count("0")
    parte_entera, _, parte_dec = cuerpo.partition(".")
    digitos = parte_entera.replace(",", "")
    if len(digitos) < ceros:
        digitos = digitos.zfill(ceros)
        parte_entera = f"{int(digitos):,}".zfill(ceros) if "," in entero else digitos
    out = parte_entera + ("." + parte_dec if nd else "")
    return signo + out + ("%" if pct else "")


def _f_left(ev: Evaluador, a: list[object]) -> object:
    t = _a_texto(_esc(ev, a[0]))
    n = int(_num_arg(ev, a[1])) if len(a) > 1 and a[1] is not None else 1
    return t[: max(n, 0)]


def _f_right(ev: Evaluador, a: list[object]) -> object:
    t = _a_texto(_esc(ev, a[0]))
    n = int(_num_arg(ev, a[1])) if len(a) > 1 and a[1] is not None else 1
    return t[-n:] if n > 0 else ""


def _f_mid(ev: Evaluador, a: list[object]) -> object:
    t = _a_texto(_esc(ev, a[0]))
    i = int(_num_arg(ev, a[1]))
    n = int(_num_arg(ev, a[2]))
    if i < 1 or n < 0:
        raise _Propaga(_VALOR)
    return t[i - 1 : i - 1 + n]


def _f_len(ev: Evaluador, a: list[object]) -> object:
    return Decimal(len(_a_texto(_esc(ev, a[0]))))


def _f_trim(ev: Evaluador, a: list[object]) -> object:
    return " ".join(x for x in _a_texto(_esc(ev, a[0])).split(" ") if x)


def _f_upper(ev: Evaluador, a: list[object]) -> object:
    return _a_texto(_esc(ev, a[0])).upper()


def _f_lower(ev: Evaluador, a: list[object]) -> object:
    return _a_texto(_esc(ev, a[0])).lower()


def _f_find(ev: Evaluador, a: list[object]) -> object:
    sub = _a_texto(_esc(ev, a[0]))
    t = _a_texto(_esc(ev, a[1]))
    inicio = int(_num_arg(ev, a[2])) if len(a) > 2 and a[2] is not None else 1
    i = t.find(sub, inicio - 1)
    if i < 0:
        raise _Propaga(_VALOR)
    return Decimal(i + 1)


def _f_concat(ev: Evaluador, a: list[object]) -> object:
    return "".join(_a_texto(_esc(ev, x)) for x in a)


def _criterio(ev: Evaluador, crit: object) -> Callable[[object], bool]:
    crit = _esc(ev, crit)
    if isinstance(crit, Err):
        raise _Propaga(crit)
    if isinstance(crit, Decimal | bool) or crit is None:
        objetivo = crit if crit is not None else _CERO

        def igual(v: object) -> bool:
            if isinstance(v, str):
                n = _texto_a_numero(v)
                return n is not None and isinstance(objetivo, Decimal) and n == objetivo
            return isinstance(v, Decimal | bool) and _comparar(v, objetivo) == 0

        return igual
    s = str(crit)
    op = "="
    for p in ("<=", ">=", "<>", "<", ">", "="):
        if s.startswith(p):
            op, s = p, s[len(p) :]
            break
    n = _texto_a_numero(s)
    if n is not None:

        def num(v: object) -> bool:
            if not isinstance(v, Decimal) or isinstance(v, bool):
                return op == "<>"
            k = _comparar(v, n)
            return {"=": k == 0, "<>": k != 0, "<": k < 0, ">": k > 0, "<=": k <= 0, ">=": k >= 0}[
                op
            ]

        return num
    patron = s.casefold()

    def texto(v: object) -> bool:
        if op in ("=", "<>"):
            if s == "" and op == "=":
                return v is None or v == ""
            ok = isinstance(v, str) and _coincide(v.casefold(), patron)
            return ok if op == "=" else not ok
        if not isinstance(v, str):
            return False
        k = _comparar(v, s)
        return {"<": k < 0, ">": k > 0, "<=": k <= 0, ">=": k >= 0}[op]

    return texto


def _como_rango(v: object) -> Rango:
    if not isinstance(v, Rango):
        raise NoSoportado("se esperaba un rango")
    return v


def _f_sumif(ev: Evaluador, a: list[object]) -> object:
    r = _como_rango(a[0])
    ok = _criterio(ev, a[1])
    s = _como_rango(a[2]) if len(a) > 2 and a[2] is not None else r
    # Solo la parte usada: una fila vacía del criterio cuenta solo si el criterio acepta el vacío,
    # y entonces suma lo que haya en la parte usada del rango de suma.
    nf, nc = ev._usado(r)
    if ok(None):
        sf, sc = ev._usado(s)
        nf, nc = max(nf, min(sf, r.filas)), max(nc, min(sc, r.cols))
    total = _CERO
    for i in range(nf):
        for j in range(nc):
            if ok(ev.celda(r.hoja, r.f1 + i, r.c1 + j)):
                v = ev.celda(s.hoja, s.f1 + i, s.c1 + j)
                if isinstance(v, Err):
                    raise _Propaga(v)
                if isinstance(v, Decimal) and not isinstance(v, bool):
                    total += v
    return total


def _f_countif(ev: Evaluador, a: list[object]) -> object:
    r = _como_rango(a[0])
    ok = _criterio(ev, a[1])
    n = sum(1 for v in ev._celdas(r) if ok(v))
    nf, nc = ev._usado(r)
    vacias = r.filas * r.cols - nf * nc  # las celdas fuera de lo usado, sin visitarlas
    if vacias and ok(None):
        n += vacias
    return Decimal(n)


def _f_sumproduct(ev: Evaluador, a: list[object]) -> object:
    if not a:
        return _CERO
    formas = [(x.filas, x.cols) if isinstance(x, Rango) else (1, 1) for x in a]
    if any(fc != formas[0] for fc in formas):
        raise _Propaga(_VALOR)
    filas, cols = formas[0]
    # Fuera de la parte usada de TODOS los rangos cada producto tiene un factor vacío (0) y no hay
    # errores que propagar: basta recorrer hasta la mayor parte usada.
    usadas = [ev._usado(x) for x in a if isinstance(x, Rango)]
    if usadas:
        filas = min(filas, max(nf for nf, _ in usadas))
        cols = min(cols, max(nc for _, nc in usadas))
    total = _CERO
    for i in range(filas):
        for j in range(cols):
            prod = _UNO
            for x in a:
                v = ev.celda(x.hoja, x.f1 + i, x.c1 + j) if isinstance(x, Rango) else x
                if isinstance(v, Err):
                    raise _Propaga(v)
                prod *= v if isinstance(v, Decimal) and not isinstance(v, bool) else _CERO
            total += prod
    return total


def _buscar_exacto(ev: Evaluador, x: object, valores: list[object]) -> int | None:
    if isinstance(x, str) and ("*" in x or "?" in x):
        patron = x.casefold()
        for i, v in enumerate(valores):
            if isinstance(v, str) and _coincide(v.casefold(), patron):
                return i
        return None
    for i, v in enumerate(valores):
        if v is None:
            continue
        if _rango_tipo(v) == _rango_tipo(x) and _comparar(v, x) == 0:
            return i
    return None


def _buscar_aprox(ev: Evaluador, x: object, valores: list[object], tipo: int) -> int | None:
    mejor = None
    for i, v in enumerate(valores):
        if v is None or isinstance(v, Err) or _rango_tipo(v) != _rango_tipo(x):
            continue
        k = _comparar(v, x)
        if (tipo > 0 and k <= 0) or (tipo < 0 and k >= 0):
            mejor = i
        elif tipo > 0:
            break
    return mejor


def _f_vlookup(ev: Evaluador, a: list[object]) -> object:
    x = _esc(ev, a[0])
    if isinstance(x, Err):
        raise _Propaga(x)
    r = _como_rango(a[1])
    col = int(_num_arg(ev, a[2]))
    exacto = len(a) > 3 and a[3] is not None and not _a_bool(_esc(ev, a[3]))
    if col < 1 or col > r.cols:
        raise _Propaga(_REF)
    filas, _ = ev._usado(r)  # más abajo todo está vacío y nunca coincide
    primera = [ev.celda(r.hoja, f, r.c1) for f in range(r.f1, r.f1 + filas)]
    i = _buscar_exacto(ev, x, primera) if exacto else _buscar_aprox(ev, x, primera, 1)
    if i is None:
        raise _Propaga(_NA)
    return ev.celda(r.hoja, r.f1 + i, r.c1 + col - 1)


def _f_match(ev: Evaluador, a: list[object]) -> object:
    x = _esc(ev, a[0])
    if isinstance(x, Err):
        raise _Propaga(x)
    r = _como_rango(a[1])
    tipo = int(_num_arg(ev, a[2])) if len(a) > 2 and a[2] is not None else 1
    valores = list(ev._celdas(r))
    i = _buscar_exacto(ev, x, valores) if tipo == 0 else _buscar_aprox(ev, x, valores, tipo)
    if i is None:
        raise _Propaga(_NA)
    return Decimal(i + 1)


def _f_index(ev: Evaluador, a: list[object]) -> object:
    r = a[0]
    if not isinstance(r, Rango):
        return r
    i = int(_num_arg(ev, a[1])) if len(a) > 1 and a[1] is not None else 0
    j = int(_num_arg(ev, a[2])) if len(a) > 2 and a[2] is not None else 0
    if len(a) <= 2 and r.filas == 1:
        i, j = 1, i
    if i == 0 and j == 0:
        return r
    if i < 0 or j < 0 or i > r.filas or j > r.cols:
        raise _Propaga(_REF)
    if i == 0:
        return Rango(r.hoja, r.f1, r.c1 + j - 1, r.f2, r.c1 + j - 1)
    if j == 0:
        if r.cols == 1:
            j = 1
        else:
            return Rango(r.hoja, r.f1 + i - 1, r.c1, r.f1 + i - 1, r.c2)
    return Rango(r.hoja, r.f1 + i - 1, r.c1 + j - 1, r.f1 + i - 1, r.c1 + j - 1)


def _f_indirect(ev: Evaluador, a: list[object]) -> object:
    texto = _a_texto(_esc(ev, a[0]))
    r = analizar_ref(texto)
    if isinstance(r, Ref):
        return ev._rango_de_ref(r)
    if isinstance(r, str):
        return ev._nombre(r)
    raise _Propaga(_REF)


_FUNCIONES: dict[str, Callable[[Evaluador, list[object]], object]] = {
    "SUM": _f_sum,
    "MIN": _f_min,
    "MAX": _f_max,
    "AVERAGE": _f_average,
    "COUNT": _f_count,
    "COUNTA": _f_counta,
    "N": _f_n,
    "ROUND": _f_round,
    "ROUNDUP": _f_roundup,
    "ROUNDDOWN": _f_rounddown,
    "INT": _f_int,
    "ABS": _f_abs,
    "MOD": _f_mod,
    "PI": _f_pi,
    "NOT": _f_not,
    "TRUE": _f_true,
    "FALSE": _f_false,
    "ISBLANK": _f_isblank,
    "ISNUMBER": _f_isnumber,
    "ISTEXT": _f_istext,
    "VALUE": _f_value,
    "TEXT": _f_text,
    "LEFT": _f_left,
    "RIGHT": _f_right,
    "MID": _f_mid,
    "LEN": _f_len,
    "TRIM": _f_trim,
    "UPPER": _f_upper,
    "LOWER": _f_lower,
    "FIND": _f_find,
    "CONCATENATE": _f_concat,
    "SUMIF": _f_sumif,
    "COUNTIF": _f_countif,
    "SUMPRODUCT": _f_sumproduct,
    "VLOOKUP": _f_vlookup,
    "MATCH": _f_match,
    "INDEX": _f_index,
    "INDIRECT": _f_indirect,
}


def es_error(v: Any) -> bool:
    return isinstance(v, Err)
