"""SF‑E3: punto de equilibrio de un presupuesto (RF‑58, RS‑4, spec §9.4).

Función pura con `Decimal`, sin base de datos (NORMAS.md §2.4). Toma la definición del caso TI‑001:

- CV (costo variable) = Σ cantidad × costo directo de cada renglón;
- CF (costo fijo) = CV × administración de los parámetros de la versión;
- V (ventas) = total del presupuesto; m = (V − CV) / V; PE = CF / m;
- ubicación: el primer período de la curva cuyo acumulado alcanza el PE, y la fracción de ese
  período en que se alcanza.

Los casos límite son resultados tipados, no excepciones (`EstadoEquilibrio`): V = 0 no es aplicable;
m ≤ 0 no tiene punto de equilibrio; PE > V no se alcanza dentro del contrato (se informa el PE sin
ubicarlo); sin curva hay PE sin ubicación. El PE se deriva de los costos, los parámetros y el plan:
no se edita (RS‑4).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from core.contracts.apu import ParametrosCosto
from core.contracts.presupuesto import Presupuesto, PuntoCurva

__all__ = ["EstadoEquilibrio", "PuntoEquilibrio", "equilibrio", "punto_equilibrio"]

CERO = Decimal(0)
CIEN = Decimal(100)


class EstadoEquilibrio(StrEnum):
    """Qué se pudo decir del punto de equilibrio."""

    CALCULADO = "calculado"
    NO_APLICABLE = "no_aplicable"
    NO_EXISTE = "no_existe"
    NO_SE_ALCANZA = "no_se_alcanza"


@dataclass(frozen=True, slots=True)
class PuntoEquilibrio:
    """Resultado de `punto_equilibrio`. Los campos que el estado no permite calcular son `None`.

    `punto` es el PE en la moneda del presupuesto y `porcentaje` su proporción de las ventas;
    `periodo` (la etiqueta del período de la curva) y `fraccion_periodo` lo ubican en el plan.
    """

    estado: EstadoEquilibrio
    venta: Decimal
    costo_variable: Decimal
    costo_fijo: Decimal
    utilidad: Decimal
    margen: Decimal | None
    punto: Decimal | None
    porcentaje: Decimal | None
    periodo: str | None
    fraccion_periodo: Decimal | None
    mensaje: str


def punto_equilibrio(presupuesto: Presupuesto, parametros: ParametrosCosto) -> PuntoEquilibrio:
    """El punto de equilibrio del presupuesto y su ubicación en la curva (spec §9.4)."""
    costo_variable = sum(
        (p.item.cantidad * p.resultado.costo_directo for p in presupuesto.partidas), CERO
    )
    costo_fijo = costo_variable * parametros.administracion
    return equilibrio(presupuesto.total, costo_variable, costo_fijo, presupuesto.curva)


def equilibrio(
    venta: Decimal, costo_variable: Decimal, costo_fijo: Decimal, curva: Sequence[PuntoCurva]
) -> PuntoEquilibrio:
    """El punto de equilibrio de unas ventas, un costo variable y un costo fijo dados, ubicado en
    `curva` (SL-E5: se extrae de `punto_equilibrio` sin cambiar su resultado, para que el punto de
    equilibrio proyectado de S2 use la misma definición con otros montos)."""
    utilidad = venta - costo_variable - costo_fijo

    def resultado(
        estado, mensaje, margen=None, punto=None, porcentaje=None, ubicacion=(None, None)
    ):
        return PuntoEquilibrio(
            estado=estado,
            venta=venta,
            costo_variable=costo_variable,
            costo_fijo=costo_fijo,
            utilidad=utilidad,
            margen=margen,
            punto=punto,
            porcentaje=porcentaje,
            periodo=ubicacion[0],
            fraccion_periodo=ubicacion[1],
            mensaje=mensaje,
        )

    if venta == CERO:
        return resultado(
            EstadoEquilibrio.NO_APLICABLE, "el presupuesto no tiene ventas: no aplica"
        )
    margen = (venta - costo_variable) / venta
    if margen <= CERO:
        return resultado(
            EstadoEquilibrio.NO_EXISTE,
            "no existe punto de equilibrio: el margen de contribucion no es positivo",
            margen=margen,
        )
    # PE = CF / m, escrito como CF x V / (V - CV): la misma cifra con una sola division.
    punto = costo_fijo * venta / (venta - costo_variable)
    porcentaje = punto / venta * CIEN
    if punto > venta:
        return resultado(
            EstadoEquilibrio.NO_SE_ALCANZA,
            "el punto de equilibrio no se alcanza dentro del contrato",
            margen=margen,
            punto=punto,
            porcentaje=porcentaje,
        )
    ubicacion = _ubicar(curva, punto)
    mensaje = (
        f"se alcanza en {ubicacion[0]}"
        if ubicacion[0] is not None
        else "sin curva de inversion: el punto de equilibrio no se ubica en el plan"
    )
    return resultado(
        EstadoEquilibrio.CALCULADO,
        mensaje,
        margen=margen,
        punto=punto,
        porcentaje=porcentaje,
        ubicacion=ubicacion,
    )


def _ubicar(curva: Sequence[PuntoCurva], punto: Decimal) -> tuple[str | None, Decimal | None]:
    """El primer período cuyo acumulado alcanza `punto` y la fracción de su monto en que ocurre."""
    anterior = CERO
    for periodo in curva:
        if periodo.acumulado >= punto:
            fraccion = (punto - anterior) / periodo.monto if periodo.monto else CERO
            return periodo.periodo, fraccion
        anterior = periodo.acumulado
    return None, None
