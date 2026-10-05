"""Interfaz de derivación de cantidades: `derivar(espacio, especialidad) -> list[ItemComputo]`.

Despacha por especialidad. Las partidas llegan en las tareas 1.5 (agua), 2.1 y 2.2; hasta
entonces el despacho devuelve lista vacía. Un espacio vacío no deriva nada (FR-1).
"""

from __future__ import annotations

from collections.abc import Callable

from adapters.espacio.modelo import Espacio
from core.contracts.item_computo import ItemComputo


def _sin_partidas(_espacio: Espacio) -> list[ItemComputo]:
    return []


_DERIVADORES: dict[str, Callable[[Espacio], list[ItemComputo]]] = {
    "agua": _sin_partidas,
    "datos": _sin_partidas,
    "electricidad": _sin_partidas,
}

ESPECIALIDADES: tuple[str, ...] = tuple(_DERIVADORES)


def derivar(espacio: Espacio, especialidad: str) -> list[ItemComputo]:
    try:
        derivador = _DERIVADORES[str(especialidad)]
    except KeyError:
        raise ValueError(
            f"especialidad desconocida: {especialidad!r}; las conocidas son {ESPECIALIDADES}"
        ) from None
    if espacio.vacio:
        return []
    return derivador(espacio)
