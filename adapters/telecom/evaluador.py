"""Evaluador seguro de expresiones aritmeticas trazables del dominio telecom.

Evalua unicamente la regla que necesita este adaptador: la longitud de un enlace de cable con su
reserva de instalacion, `longitud_m * (1 + reserva)`. Es una implementacion propia y minima, NO
la de `adapters/civil/evaluador.py`: cada adaptador es autonomo (NORMAS.md, seccion 2) y no
comparte codigo con otro adaptador, solo con `core.contracts`. La duplicacion conceptual entre
ambos evaluadores es deliberada y se registra como hallazgo en
`docs/bitacora/2026-08-29-I5-telecom.md`.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from decimal import Decimal

_OPERADORES_PERMITIDOS = (ast.Add, ast.Sub, ast.Mult, ast.Div)


def evaluar_regla(expresion: str, parametros: Mapping[str, Decimal]) -> Decimal:
    """Evalua `expresion` con los valores de `parametros` y devuelve un `Decimal`.

    Solo admite suma, resta, multiplicacion, division, nombres de parametro, constantes numericas
    y parentesis (que el AST ya resuelve como precedencia). Cualquier otro nodo (llamadas,
    atributos, comparaciones, potencias...) lanza `ValueError`; un nombre no declarado en
    `parametros` lanza `KeyError`.
    """
    arbol = ast.parse(expresion, mode="eval")
    return _evaluar_nodo(arbol.body, parametros)


def _evaluar_nodo(nodo: ast.AST, parametros: Mapping[str, Decimal]) -> Decimal:
    if isinstance(nodo, ast.BinOp):
        return _evaluar_binop(nodo, parametros)
    if isinstance(nodo, ast.Name):
        return _evaluar_nombre(nodo, parametros)
    if isinstance(nodo, ast.Constant):
        return _evaluar_constante(nodo)
    raise ValueError(f"nodo no permitido en una regla telecom: {type(nodo).__name__}")


def _evaluar_binop(nodo: ast.BinOp, parametros: Mapping[str, Decimal]) -> Decimal:
    if not isinstance(nodo.op, _OPERADORES_PERMITIDOS):
        raise ValueError(f"operador no permitido en una regla telecom: {type(nodo.op).__name__}")
    izquierda = _evaluar_nodo(nodo.left, parametros)
    derecha = _evaluar_nodo(nodo.right, parametros)
    if isinstance(nodo.op, ast.Add):
        return izquierda + derecha
    if isinstance(nodo.op, ast.Sub):
        return izquierda - derecha
    if isinstance(nodo.op, ast.Mult):
        return izquierda * derecha
    return izquierda / derecha  # ast.Div: unico operador restante ya validado arriba


def _evaluar_nombre(nodo: ast.Name, parametros: Mapping[str, Decimal]) -> Decimal:
    if nodo.id not in parametros:
        raise KeyError(f"parametro no definido para la regla telecom: {nodo.id!r}")
    return parametros[nodo.id]


def _evaluar_constante(nodo: ast.Constant) -> Decimal:
    valor = nodo.value
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        raise ValueError(f"constante no numerica en una regla telecom: {valor!r}")
    return Decimal(str(valor))
