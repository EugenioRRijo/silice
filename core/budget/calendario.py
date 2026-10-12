# core/budget/calendario.py
"""SL-E4: el calendario de la obra (spec S2 §4.1). Funciones puras, sin base de datos.

Los días hábiles son lunes a viernes menos los feriados declarados (S2-R9, SUPUESTO_DECLARADO: la
LOTTT, art. 173, limita la jornada del trabajador a cinco días por semana, no la de la obra). El
**día hábil 1** es el primer día hábil que cae en la fecha de inicio o después. El período *n*
abarca los días hábiles `(n-1)·L + 1 ... n·L` desde el inicio, con `L` los días por período.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import date, timedelta

__all__ = ["dia_habil", "dias_habiles", "es_habil", "numero_de_dia", "periodo_de"]

DIAS_DE_LA_SEMANA_HABILES = 5  # lunes (0) a viernes (4)


def es_habil(dia: date, feriados: Collection[date] = ()) -> bool:
    """True si `dia` es de lunes a viernes y no es feriado."""
    return dia.weekday() < DIAS_DE_LA_SEMANA_HABILES and dia not in feriados


def dias_habiles(desde: date, hasta: date, feriados: Collection[date] = ()) -> int:
    """Cuántos días hábiles hay en [desde, hasta], ambos incluidos; 0 si `desde` > `hasta`."""
    cuenta = 0
    dia = desde
    while dia <= hasta:
        if es_habil(dia, feriados):
            cuenta += 1
        dia += timedelta(days=1)
    return cuenta


def numero_de_dia(inicio: date, fecha: date, feriados: Collection[date] = ()) -> int:
    """El número de día hábil de `fecha`: los días hábiles de [inicio, fecha]. Antes de que
    empiece la obra (o de su primer día hábil) es 0; un sábado cuenta lo ya transcurrido."""
    return dias_habiles(inicio, fecha, feriados)


def dia_habil(inicio: date, numero: int, feriados: Collection[date] = ()) -> date:
    """La fecha del día hábil número `numero` (1 es el primer día hábil desde `inicio`).
    `ValueError` si `numero` es menor que 1."""
    if numero < 1:
        raise ValueError(f"el numero de dia habil debe ser 1 o mayor, no {numero}")
    dia = inicio
    cuenta = 0
    while True:
        if es_habil(dia, feriados):
            cuenta += 1
            if cuenta == numero:
                return dia
        dia += timedelta(days=1)


def periodo_de(
    inicio: date, dias_por_periodo: int, fecha: date, feriados: Collection[date] = ()
) -> int:
    """El período (1, 2, ...) que contiene `fecha`; 0 si la obra aún no empieza. Un fin de semana
    o un feriado pertenece al período del último día hábil que lo precede."""
    if dias_por_periodo < 1:
        raise ValueError(f"los dias por periodo deben ser 1 o mas, no {dias_por_periodo}")
    numero = numero_de_dia(inicio, fecha, feriados)
    return -(-numero // dias_por_periodo)
