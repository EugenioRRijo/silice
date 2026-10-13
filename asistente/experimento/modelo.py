"""La referencia de una tarea del experimento (S4 §9.2, §9.5): lo que el borrador DEBIA decir.

Dos tipos compartidos por el banco (que los construye de una ficha), el comparador y las mutaciones.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from adapters.espacio import Espacio
from core.contracts.item_computo import ItemComputo

#: El protocolo versionado del experimento (S4 §9.1): una sola fuente de sus parametros.
RUTA_PROTOCOLO = Path(__file__).with_name("protocolo.json")


@functools.cache
def protocolo() -> dict[str, Any]:
    """`protocolo.json` leido una vez: tolerancias, fecha de R12, semilla... (M2)."""
    return json.loads(RUTA_PROTOCOLO.read_text(encoding="utf-8"))


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
