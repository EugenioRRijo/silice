"""Tolerancias compartidas por el lector, las reglas del libro y el cotejo del PDF (spec 1.5).

Una sola fuente para el mismo número: antes cada módulo declaraba su copia de 0,005.
"""

from __future__ import annotations

from decimal import Decimal

__all__ = ["MEDIO_CENTAVO"]

#: Medio centavo (USD): la mitad de la unidad que imprime el libro o el PDF. Por debajo, una
#: diferencia de montos es redondeo de presentación, no un error del documento. Lo usan la pasada
#: final de `lector._unir` (F-D6), el cuadre de las reglas L4/L9 y el cotejo del PDF (L10).
MEDIO_CENTAVO = Decimal("0.005")
