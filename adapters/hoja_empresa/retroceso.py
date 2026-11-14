"""¿Puede una expresión regular hacer que `re` retroceda sin fin? Lo usa `patron_banda` del perfil
con un APU por hoja (`perfil_apu_por_hoja.py`), que se pone desde la interfaz y se busca en cada
auditoría del libro (AH9) y en cada recálculo de la Hoja (VR4).

`re` no tiene tiempo máximo y el módulo `regex` no es dependencia de Sílice, así que se juzga la
forma de la expresión, por su árbol (`re._parser`), sin medirla. Es una heurística, no una prueba:
ataja las formas que cuelgan (exponenciales y polinómicas de grado alto) y acepta las bandas
bien escritas. Simulación con el banco de patrones en `docs/bitacora/arbitrajes/ola2-claude-
xhigh.md`, «Ronda 2: correcciones» (R2-1).

Las tres reglas:

1. **Sin referencias hacia atrás** («(?P=minimo)», «\\1»).
2. **Repetición dentro de otra, solo con separador.** El cuerpo de una repetición que se repite
   (más de una vez, también «{28}») solo puede llevar átomos de un carácter («a», «[0-9]», «\\d»),
   repeticiones de cuenta fija de un átomo («\\d{3}») y a lo sumo una repetición variable de un
   átomo («\\d+», «a?»), que tiene que ir seguida, en ronda, de un átomo obligatorio que no
   comparte ningún carácter con ella: el «.» de «(?:\\.\\d{3})*» o el espacio de «(?:\\w+ )*»
   marcan dónde acaba cada vuelta, así que hay un solo modo de repartir el texto. Sin alternativas
   dentro («(a|aa)+»). «(a+)+», «(?:a?a)+», «(?:a?){28}» y «(?:\\d+\\.?)+» no tienen separador.
3. **A lo sumo una parte variable abierta.** Una parte variable está cerrada si lo que puede venir
   justo después (hasta el primer átomo obligatorio) no comparte caracteres con ella: solo uno de
   sus finales sigue adelante («\\d+ km»). Las abiertas multiplican los caminos: «.*de.*» tiene
   dos y quince «[0-9]*» seguidos tienen catorce. Con una sola, lo peor que se acepta es cúbico en
   el largo del texto (simulación: 0,1 s con 300 caracteres iguales).
"""

from __future__ import annotations

import functools
import re
import re._parser as _sre
from collections.abc import Iterator
from typing import Any

__all__ = ["MAX_ABIERTAS", "retroceso_peligroso"]

#: Cuántas partes variables abiertas admite un patrón (regla 3).
MAX_ABIERTAS = 1

_REPETICIONES = {_sre.MAX_REPEAT, _sre.MIN_REPEAT, getattr(_sre, "POSSESSIVE_REPEAT", None)}
_REFERENCIAS = {_sre.GROUPREF, _sre.GROUPREF_EXISTS}
_MIRADAS = {_sre.ASSERT, _sre.ASSERT_NOT}
_GRUPOS = {_sre.SUBPATTERN, getattr(_sre, "ATOMIC_GROUP", None)}
#: Los caracteres con que se comparan los conjuntos (latín con tildes y la ñ caben de sobra).
_TODOS = frozenset(chr(i) for i in range(0x250))
_CATEGORIAS = {
    _sre.CATEGORY_DIGIT: r"\d",
    _sre.CATEGORY_NOT_DIGIT: r"\D",
    _sre.CATEGORY_SPACE: r"\s",
    _sre.CATEGORY_NOT_SPACE: r"\S",
    _sre.CATEGORY_WORD: r"\w",
    _sre.CATEGORY_NOT_WORD: r"\W",
}

_Nodos = Any  # la lista de (operación, argumento) de `re._parser`


@functools.lru_cache(maxsize=64)
def retroceso_peligroso(patron: str) -> str | None:
    """Qué del patrón puede colgar a `re` (las tres reglas del módulo), o `None`. `re.error` si
    no compila."""
    arbol = _sre.parse(patron)
    hallado = _anidadas(arbol)
    if hallado is not None:
        return hallado
    abiertas = _abiertas(arbol)
    if abiertas > MAX_ABIERTAS:
        return (
            f"{abiertas} partes variables abiertas, que pueden quedarse con los mismos "
            f"caracteres (como en «.*de.*km» o «\\d*\\d*\\d*»; se admite {MAX_ABIERTAS})"
        )
    return None


@functools.cache
def _clase(expresion: str) -> frozenset[str]:
    return frozenset(c for c in _TODOS if re.fullmatch(expresion, c))


def _con_mayusculas(c: str) -> set[str]:
    """`leer_banda` busca sin distinguir mayúsculas."""
    return {x for x in (c, c.lower(), c.upper()) if len(x) == 1}


def _conjunto(op: Any, av: Any) -> frozenset[str] | None:
    """Los caracteres que casa un átomo de un carácter, o `None` si no es uno."""
    if op is _sre.LITERAL:
        return frozenset(_con_mayusculas(chr(av)))
    if op is _sre.NOT_LITERAL:
        return _TODOS - _con_mayusculas(chr(av))
    if op is _sre.ANY:
        return _TODOS - {"\n"}
    if op is not _sre.IN:
        return None
    negado, dentro = False, set()
    for o, a in av:
        if o is _sre.NEGATE:
            negado = True
        elif o is _sre.LITERAL:
            dentro |= _con_mayusculas(chr(a))
        elif o is _sre.RANGE:
            for i in range(a[0], min(a[1], 0x24F) + 1):
                dentro |= _con_mayusculas(chr(i))
        elif o is _sre.CATEGORY and a in _CATEGORIAS:
            dentro |= _clase(_CATEGORIAS[a])
        else:
            return None
    return _TODOS - dentro if negado else frozenset(dentro)


def _aplanar(nodos: _Nodos) -> Iterator[tuple[Any, Any]]:
    """Los nodos de la secuencia con los grupos abiertos (un grupo no cambia lo que se casa)."""
    for op, av in nodos:
        if op is _sre.SUBPATTERN:
            yield from _aplanar(av[-1])
        elif op in _GRUPOS:
            yield from _aplanar(av)
        else:
            yield op, av


def _de_un_atomo(av: Any) -> frozenset[str] | None:
    """El conjunto del átomo si la repetición es de un solo átomo de un carácter."""
    cuerpo = list(_aplanar(av[2]))
    return _conjunto(*cuerpo[0]) if len(cuerpo) == 1 else None


def _fijo(nodos: _Nodos) -> bool:
    for op, av in _aplanar(nodos):
        if _conjunto(op, av) is not None or op is _sre.AT:
            continue
        if op in _REPETICIONES and av[0] == av[1] and _fijo(av[2]):
            continue
        return False
    return True


# --- reglas 1 y 2 --------------------------------------------------------------------------------


def _anidadas(nodos: _Nodos) -> str | None:
    for op, av in nodos:
        if op in _REFERENCIAS:
            return "una referencia hacia atrás"
        hallado = None
        if op in _REPETICIONES:
            hallado = _cuerpo_repetido(av[2]) if av[1] > 1 else _anidadas(av[2])
        elif op is _sre.SUBPATTERN:
            hallado = _anidadas(av[-1])
        elif op in _GRUPOS:
            hallado = _anidadas(av)
        elif op is _sre.BRANCH:
            hallado = next((h for rama in av[1] if (h := _anidadas(rama)) is not None), None)
        elif op in _MIRADAS:
            hallado = _anidadas(av[1])
        if hallado is not None:
            return hallado
    return None


def _cuerpo_repetido(sub: _Nodos) -> str | None:
    cuerpo = list(_aplanar(sub))
    variables = []
    for i, (op, av) in enumerate(cuerpo):
        if op in _REFERENCIAS:
            return "una referencia hacia atrás"
        if op is _sre.BRANCH:
            return "una alternativa dentro de una repetición"
        if op in _MIRADAS:
            hallado = _anidadas(av[1])
            if hallado is not None:
                return hallado
            continue
        if op is _sre.AT or _conjunto(op, av) is not None:
            continue
        if op in _REPETICIONES and _de_un_atomo(av) is not None:
            if av[0] != av[1]:
                variables.append(i)
            continue
        if op in _REPETICIONES and av[0] == av[1] and _fijo(av[2]):
            continue
        return "una repetición dentro de otra"
    if not variables:
        return None
    if len(variables) > 1:
        return "una repetición dentro de otra con más de una parte variable"
    i = variables[0]
    siguiente = cuerpo[(i + 1) % len(cuerpo)]
    separador = None if len(cuerpo) == 1 else _obligatorio(*siguiente)
    if separador is None or separador & _de_un_atomo(cuerpo[i][1]):  # type: ignore[operator]
        return "una repetición dentro de otra sin un separador fijo detrás"
    return None


def _obligatorio(op: Any, av: Any) -> frozenset[str] | None:
    """El conjunto de un átomo que tiene que estar (solo o repetido al menos una vez)."""
    conjunto = _conjunto(op, av)
    if conjunto is not None:
        return conjunto
    if op in _REPETICIONES and av[0] >= 1:
        return _de_un_atomo(av)
    return None


# --- regla 3 -------------------------------------------------------------------------------------


def _caracteres(nodos: _Nodos) -> frozenset[str]:
    """Todos los caracteres que puede casar la secuencia."""
    acc: set[str] = set()
    for op, av in _aplanar(nodos):
        conjunto = _conjunto(op, av)
        if conjunto is not None:
            acc |= conjunto
        elif op in _REPETICIONES:
            acc |= _caracteres(av[2])
        elif op is _sre.BRANCH:
            for rama in av[1]:
                acc |= _caracteres(rama)
    return frozenset(acc)


def _primeros(nodos: _Nodos) -> tuple[frozenset[str], bool]:
    """Con qué caracteres puede empezar la secuencia, y si puede casar vacía."""
    acc: set[str] = set()
    for op, av in _aplanar(nodos):
        conjunto = _conjunto(op, av)
        if conjunto is not None:
            return frozenset(acc | conjunto), False
        if op in _REPETICIONES:
            primeros, vacia = _primeros(av[2])
            acc |= primeros
            if av[0] >= 1 and not vacia:
                return frozenset(acc), False
        elif op is _sre.BRANCH:
            vacia = False
            for rama in av[1]:
                primeros, v = _primeros(rama)
                acc |= primeros
                vacia |= v
            if not vacia:
                return frozenset(acc), False
    return frozenset(acc), True


def _abiertas(nodos: _Nodos, despues: frozenset[str] = frozenset()) -> int:
    """Las partes variables abiertas de un mismo camino (regla 3). `despues` es lo que puede venir
    detrás de la secuencia; el final del patrón (vacío) cierra."""
    lista = list(_aplanar(nodos))
    total = 0
    for i, (op, av) in enumerate(lista):
        sigue, vacio = _primeros(lista[i + 1 :])
        if vacio:
            sigue = sigue | despues
        if op in _REPETICIONES:
            variable = _caracteres(av[2]) if av[0] != av[1] else frozenset()
            total += bool(variable & sigue) + _abiertas(av[2], sigue)
        elif op is _sre.BRANCH:
            total += max(_abiertas(rama, sigue) for rama in av[1])
        elif op in _MIRADAS:
            total += _abiertas(av[1])
    return total
