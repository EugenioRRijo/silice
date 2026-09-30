"""Evaluador seguro de expresiones aritméticas trazables del dominio industrial.

La regla de cómputo de este adaptador (`frecuencia_anual * horizonte_anios`,
`adapters/industrial/adaptador.py`) se declara como texto para que el informe de auditoría pueda
mostrar la expresión exacta que produjo cada cantidad (regla R1, NORMAS.md §7). Este módulo la
evalúa sin usar `eval()`: solo permite el subconjunto aritmético necesario (suma, resta,
multiplicación, división, potencia, negación unaria, nombres de parámetro, constantes numéricas y
paréntesis, que el AST ya resuelve como precedencia). Cualquier otro nodo del árbol sintáctico
(llamadas, atributos, índices, comparaciones, comprensiones, etc.) se rechaza.

Es una implementación propia e independiente de `adapters/civil/evaluador.py`: cada adaptador es
autónomo (NORMAS.md §2), así que no se importa entre dominios aunque el subconjunto de aritmética
permitido sea, por ahora, el mismo.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from decimal import Decimal

_OPERADORES_BINARIOS_PERMITIDOS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)


def evaluar_regla(expresion: str, parametros: Mapping[str, Decimal]) -> Decimal:
    """Evalua `expresion` con los valores de `parametros` y devuelve un `Decimal`.

    Lanza `ValueError` si la expresión contiene un nodo no permitido (por ejemplo una llamada o un
    acceso a atributo) y `KeyError` si referencia un nombre que no está en `parametros`.
    """
    arbol = ast.parse(expresion, mode="eval")
    return _evaluar_nodo(arbol.body, parametros)


def _evaluar_nodo(nodo: ast.AST, parametros: Mapping[str, Decimal]) -> Decimal:
    if isinstance(nodo, ast.BinOp):
        return _evaluar_binop(nodo, parametros)
    if isinstance(nodo, ast.UnaryOp):
        return _evaluar_unaryop(nodo, parametros)
    if isinstance(nodo, ast.Name):
        return _evaluar_nombre(nodo, parametros)
    if isinstance(nodo, ast.Constant):
        return _evaluar_constante(nodo)
    raise ValueError(f"nodo no permitido en una regla parametrica: {type(nodo).__name__}")


def _evaluar_binop(nodo: ast.BinOp, parametros: Mapping[str, Decimal]) -> Decimal:
    if not isinstance(nodo.op, _OPERADORES_BINARIOS_PERMITIDOS):
        raise ValueError(f"operador binario no permitido: {type(nodo.op).__name__}")
    izquierda = _evaluar_nodo(nodo.left, parametros)
    derecha = _evaluar_nodo(nodo.right, parametros)
    if isinstance(nodo.op, ast.Add):
        return izquierda + derecha
    if isinstance(nodo.op, ast.Sub):
        return izquierda - derecha
    if isinstance(nodo.op, ast.Mult):
        return izquierda * derecha
    if isinstance(nodo.op, ast.Div):
        return izquierda / derecha
    return izquierda**derecha  # ast.Pow: ya se valido que no hay otro operador posible


def _evaluar_unaryop(nodo: ast.UnaryOp, parametros: Mapping[str, Decimal]) -> Decimal:
    if not isinstance(nodo.op, ast.USub):
        raise ValueError(f"operador unario no permitido: {type(nodo.op).__name__}")
    return -_evaluar_nodo(nodo.operand, parametros)


def _evaluar_nombre(nodo: ast.Name, parametros: Mapping[str, Decimal]) -> Decimal:
    if nodo.id not in parametros:
        raise KeyError(f"parametro no definido para la regla: {nodo.id!r}")
    return parametros[nodo.id]


def _evaluar_constante(nodo: ast.Constant) -> Decimal:
    valor = nodo.value
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        raise ValueError(f"constante no numerica en una regla parametrica: {valor!r}")
    return Decimal(str(valor))
