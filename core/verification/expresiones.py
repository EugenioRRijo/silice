"""Evaluador seguro de las expresiones trazables que acompañan a una cantidad de obra.

`ItemComputo.regla` guarda como texto la expresión que produjo la cantidad (por ejemplo
``"n * (a**2 - (a - 2*e)**2) * h"``) y `ItemComputo.parametros` los valores con los que se evaluó.
La regla R1 la vuelve a evaluar y compara; la regla R5 hace lo mismo con el balance volumétrico.
El núcleo no puede reutilizar el evaluador de `adapters/civil/` (importaría un adaptador, CLAUDE.md
§2), así que tiene el suyo: la duplicación es un hallazgo registrado en la bitácora de la Sesión I4,
no un descuido.

Se acepta únicamente el subconjunto aritmético: suma, resta, multiplicación, división, potencia,
negación unaria, nombres de parámetro y constantes numéricas. Cualquier otro nodo del árbol
sintáctico (llamadas, atributos, índices, condicionales, comparaciones, cadenas) se rechaza. Las
constantes se leen del texto fuente y se convierten con `Decimal(str)`: pasar por `float` perdería
precisión y contradiría CLAUDE.md §2.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

__all__ = [
    "ExpresionInvalida",
    "ParametroFaltante",
    "codigos_de",
    "evaluar",
    "nombres_de",
    "sustituir_codigos",
]


class ExpresionInvalida(ValueError):  # noqa: N818
    """La expresión no es analizable o usa una construcción que no es aritmética pura.

    El nombre no lleva el sufijo `Error` que pide la convención inglesa de N818: el proyecto
    escribe sus identificadores en español (CLAUDE.md §3) y "Invalida" ya nombra la falla.
    """


class ParametroFaltante(KeyError):  # noqa: N818
    """La expresión referencia un nombre (o un código de partida) que no se le proporcionó."""


_MARCADOR_CODIGO = re.compile(r"\{([^{}]*)\}")

_BINARIOS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_UNARIOS = (ast.UAdd, ast.USub)


def evaluar(expresion: str, valores: Mapping[str, Decimal]) -> Decimal:
    """Evalúa `expresion` con `valores` y devuelve un `Decimal` exacto.

    Lanza `ExpresionInvalida` ante cualquier construcción no aritmética o si un parámetro usado no
    es `Decimal`, y `ParametroFaltante` si la expresión usa un nombre que no está en `valores`.
    """
    return _evaluar_nodo(_analizar(expresion).body, expresion, valores)


def nombres_de(expresion: str) -> frozenset[str]:
    """Nombres de parámetro que aparecen en la expresión."""
    return frozenset(
        nodo.id for nodo in ast.walk(_analizar(expresion)) if isinstance(nodo, ast.Name)
    )


def codigos_de(expresion: str) -> tuple[str, ...]:
    """Códigos de partida referenciados entre llaves, en orden de aparición y sin repetir."""
    vistos: dict[str, None] = {}
    for coincidencia in _MARCADOR_CODIGO.finditer(expresion):
        codigo = coincidencia.group(1).strip()
        if codigo:
            vistos.setdefault(codigo, None)
    return tuple(vistos)


def sustituir_codigos(expresion: str, cantidades: Mapping[str, Decimal]) -> str:
    """Reemplaza cada `{codigo}` por la cantidad de esa partida y devuelve la expresión resultante.

    Los códigos de partida no son identificadores de Python (`LB-01-EXC` se analizaría como una
    resta), por eso van entre llaves y se sustituyen antes de analizar el texto.
    """

    def _reemplazar(coincidencia: re.Match[str]) -> str:
        codigo = coincidencia.group(1).strip()
        if codigo not in cantidades:
            raise ParametroFaltante(codigo)
        return str(cantidades[codigo])

    return _MARCADOR_CODIGO.sub(_reemplazar, expresion)


# ---------------------------------------------------------------------------------------------
# Recorrido del árbol
# ---------------------------------------------------------------------------------------------


def _analizar(expresion: str) -> ast.Expression:
    try:
        return ast.parse(expresion, mode="eval")
    except SyntaxError as error:
        raise ExpresionInvalida(f"expresion no analizable: {expresion!r}") from error


def _evaluar_nodo(nodo: ast.AST, fuente: str, valores: Mapping[str, Decimal]) -> Decimal:
    if isinstance(nodo, ast.BinOp):
        return _evaluar_binario(nodo, fuente, valores)
    if isinstance(nodo, ast.UnaryOp):
        return _evaluar_unario(nodo, fuente, valores)
    if isinstance(nodo, ast.Name):
        if nodo.id not in valores:
            raise ParametroFaltante(nodo.id)
        valor = valores[nodo.id]
        if not isinstance(valor, Decimal):
            # Un `float` en los parámetros haría fallar la aritmética (o la comparación posterior
            # de R1) con `TypeError`, fuera del alcance de las reglas: el informe no se emitiría
            # (principio 7 de CLAUDE.md §2). Aquí se convierte en un dato inválido reportable.
            raise ExpresionInvalida(
                f"el parametro {nodo.id!r} no es Decimal sino {type(valor).__name__}"
            )
        return valor
    if isinstance(nodo, ast.Constant):
        return _evaluar_constante(nodo, fuente)
    raise ExpresionInvalida(f"nodo no permitido en una expresion trazable: {type(nodo).__name__}")


def _evaluar_binario(nodo: ast.BinOp, fuente: str, valores: Mapping[str, Decimal]) -> Decimal:
    if not isinstance(nodo.op, _BINARIOS):
        raise ExpresionInvalida(f"operador binario no permitido: {type(nodo.op).__name__}")
    izquierda = _evaluar_nodo(nodo.left, fuente, valores)
    derecha = _evaluar_nodo(nodo.right, fuente, valores)
    try:
        if isinstance(nodo.op, ast.Add):
            return izquierda + derecha
        if isinstance(nodo.op, ast.Sub):
            return izquierda - derecha
        if isinstance(nodo.op, ast.Mult):
            return izquierda * derecha
        if isinstance(nodo.op, ast.Div):
            return izquierda / derecha
        return izquierda**derecha  # ast.Pow: no queda otro operador posible
    except ArithmeticError as error:
        # desbordamiento, division entre cero, potencia no representable: cualquier operador
        # aritmetico puede fallar con un Decimal suficientemente extremo, no solo Div y Pow.
        raise ExpresionInvalida(f"operacion aritmetica imposible: {error}") from error


def _evaluar_unario(nodo: ast.UnaryOp, fuente: str, valores: Mapping[str, Decimal]) -> Decimal:
    if not isinstance(nodo.op, _UNARIOS):
        raise ExpresionInvalida(f"operador unario no permitido: {type(nodo.op).__name__}")
    operando = _evaluar_nodo(nodo.operand, fuente, valores)
    return -operando if isinstance(nodo.op, ast.USub) else operando


def _evaluar_constante(nodo: ast.Constant, fuente: str) -> Decimal:
    valor = nodo.value
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        raise ExpresionInvalida(f"constante no numerica en una expresion trazable: {valor!r}")
    segmento = ast.get_source_segment(fuente, nodo)
    texto = segmento.replace("_", "") if segmento else str(valor)
    try:
        return Decimal(texto)
    except InvalidOperation as error:
        raise ExpresionInvalida(
            f"constante numerica no convertible a Decimal: {texto!r}"
        ) from error
