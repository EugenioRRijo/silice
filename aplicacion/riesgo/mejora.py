"""Informe de mejora de la estimación (plan vial, Tarea 15; especificación §5.2).

Cuando la obra termina se compara lo que se estimó con lo que costó de verdad: el presupuesto
original (el de antes de Sílice) y la estimación de Sílice, cada uno contra el costo final real.

- **Error** de una estimación = |estimado − real| ÷ real × 100, con dos decimales, `ROUND_HALF_UP`.
- **Mejora** en puntos porcentuales = error del original − error de Sílice, **calculada con los dos
  errores ya redondeados**: lo que la persona ve en la pantalla suma exacto (23,08 − 3,85 = 19,23).
  Positiva si Sílice acertó más; **negativa si acertó menos: no se esconde**.

Aquí no hay reloj, ni base, ni IA: tres montos entran y salen tres porcentajes. Las tres cifras
deben estar en la misma moneda y a la misma fecha de precios (quien llama lo garantiza).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

__all__ = ["Mejora", "mejora_de_estimacion"]

_CENTESIMA = Decimal("0.01")


@dataclass(frozen=True)
class Mejora:
    """Los dos errores y cuánto mejoró (o empeoró, si es negativa) Sílice sobre el original."""

    error_original_pct: Decimal
    error_silice_pct: Decimal
    mejora_pp: Decimal


def _error_pct(estimado: Decimal, real: Decimal) -> Decimal:
    return (abs(estimado - real) / real * 100).quantize(_CENTESIMA, rounding=ROUND_HALF_UP)


def mejora_de_estimacion(
    costo_final_real: Decimal, presupuesto_original: Decimal, estimacion_silice: Decimal
) -> Mejora:
    """El error de cada estimación contra el costo final real y la mejora en puntos porcentuales.

    `ValueError` (con un mensaje llano) si el costo final real no es positivo, pues no hay contra
    qué medir, o si alguna estimación es negativa.
    """
    for valor in (costo_final_real, presupuesto_original, estimacion_silice):
        if not valor.is_finite():
            raise ValueError("las cifras deben ser números finitos")
    if costo_final_real <= 0:
        raise ValueError("el costo final real debe ser mayor que cero")
    if presupuesto_original < 0:
        raise ValueError("el presupuesto original no puede ser negativo")
    if estimacion_silice < 0:
        raise ValueError("la estimación de Sílice no puede ser negativa")
    original = _error_pct(presupuesto_original, costo_final_real)
    silice = _error_pct(estimacion_silice, costo_final_real)
    return Mejora(original, silice, original - silice)
