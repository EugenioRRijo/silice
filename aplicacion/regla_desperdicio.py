"""La regla del desperdicio dentro de la cantidad (F5 vial, tareas 3 y 4), en un solo lugar.

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §4 (opción B): la
`LineaMaterial` del núcleo lleva `neta × (1 + porcentaje / 100)` y la neta y el porcentaje quedan
en una traza aparte. La usan el lector de libros con un APU por hoja (`fusion.mapeo`) y Componer
(`aplicacion.desperdicio`, que la reexporta y guarda la traza): una sola fórmula (NORMAS §2.1).

Vivía en `fusion/desperdicio.py`; pasó aquí en la revisión de correcciones de F5/F7/F8 (N5) para
cortar el ciclo `fusion` ↔ `aplicacion`: es una regla pura (solo la biblioteca estándar), la única
clase de módulo de `aplicacion` que `fusion` puede importar, y `aplicacion` ya no importa `fusion`
(lo vigila `tests/unit/test_arquitectura.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ["TrazaDesperdicio", "cantidad_con_desperdicio"]

_CIEN = Decimal(100)


@dataclass(frozen=True, slots=True)
class TrazaDesperdicio:
    """Un material con desperdicio: lo tecleado (neta y porcentaje) y la cantidad que resultó."""

    descripcion: str
    unidad: str
    cantidad_neta: Decimal
    desperdicio_pct: Decimal
    cantidad: Decimal


def cantidad_con_desperdicio(neta: Decimal, porcentaje: Decimal) -> Decimal:
    """`neta × (1 + porcentaje / 100)`, exacta, sin redondear: «4» es 4 %."""
    return neta * (1 + porcentaje / _CIEN)
