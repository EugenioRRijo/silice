"""La referencia de una tarea del experimento (S4 §9.2, §9.5): lo que el borrador DEBIA decir.

Dos tipos compartidos por el banco (que los construye de una ficha), el comparador y las mutaciones.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from adapters.espacio import Espacio
from core.contracts.item_computo import ItemComputo


@dataclass(frozen=True, slots=True)
class Sembrado:
    """Un dato sembrado en el pedido de una tarea con errores: el elemento de la REFERENCIA, el
    campo y el valor equivocado (p. ej. un punto a 3,00 m en un ambiente de 2,40 m)."""

    clase: str
    id_referencia: str
    campo: str
    valor: Decimal


@dataclass(frozen=True, slots=True)
class Referencia:
    espacio: Espacio
    items: tuple[ItemComputo, ...] = ()
    posicion_libre: bool = False
    sembrados: tuple[Sembrado, ...] = ()
