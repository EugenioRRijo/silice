"""IVA sobre el total del presupuesto y de cada valuación (plan vial, Tarea 18).

El IVA se calcula **sobre el total**, nunca dentro del APU: el precio unitario no lo lleva. La
alícuota es una `Constante` con su fuente y la marca «a cotejar con la Gaceta vigente». Montos a dos
decimales con `ROUND_HALF_UP` (NORMAS.md §2).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from adapters.espacio.especialidades import Constante

_CENTIMO = Decimal("0.01")

ALICUOTA_IVA = Constante(
    "iva_general",
    "Alícuota general del IVA",
    Decimal("0.16"),
    "Ley del IVA, alícuota general: Decreto 3.584, G.O. 6.395 Ext., 17-08-2018 (16 %) "
    "— a cotejar con la Gaceta vigente",
)


@dataclass(frozen=True)
class ResumenImpuestos:
    """Subtotal sin IVA, el IVA y el total con IVA, los tres a dos decimales."""

    subtotal: Decimal
    iva: Decimal
    total: Decimal


def _centimos(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTIMO, rounding=ROUND_HALF_UP)


def con_iva(
    subtotal: Decimal, alicuota: Decimal = Decimal(str(ALICUOTA_IVA.valor))
) -> ResumenImpuestos:
    """El IVA de `subtotal` a `alicuota` (fracción: 0,16 es 16 %). El total suma las cifras ya
    redondeadas, así lo que se lee en pantalla cuadra."""
    base = _centimos(subtotal)
    iva = _centimos(subtotal * alicuota)
    return ResumenImpuestos(base, iva, base + iva)
