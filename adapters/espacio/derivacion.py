"""Interfaz de derivación de cantidades: `derivar(espacio, especialidad) -> list[ItemComputo]`.

Despacha por especialidad: agua (1.5), datos (2.1) y electricidad (2.2). Un espacio vacío no
deriva nada (FR-1).
"""

from __future__ import annotations

from collections.abc import Callable

from adapters.espacio.especialidades.agua import derivar_agua
from adapters.espacio.especialidades.datos import derivar_datos
from adapters.espacio.especialidades.electricidad import derivar_electricidad
from adapters.espacio.modelo import Espacio
from core.contracts.item_computo import ItemComputo

_DERIVADORES: dict[str, Callable[[Espacio], list[ItemComputo]]] = {
    "agua": derivar_agua,
    "datos": derivar_datos,
    "electricidad": derivar_electricidad,
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
