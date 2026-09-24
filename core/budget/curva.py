"""Curva de inversión: reparte el presupuesto en períodos y cierra exactamente en su total.

El presupuesto auditado del caso repartía 1 575,50 de los 1 586,61 USD y cerraba en 99,30 %
(hallazgo 3 de `docs/linea_base.md`). Aquí ese error es imposible por construcción: el monto del
último período **no se calcula sumando fracciones**, sino restando del total del presupuesto lo ya
repartido, de modo que su acumulado es el total literal aunque los montos anteriores se redondeen a
dos decimales. La regla R2 comprueba esa identidad; este módulo la garantiza.

`PuntoCurva` no lleva código de partida (insuficiencia del contrato registrada en la bitácora de la
Sesión I4), así que el enlace período-partida viaja en la etiqueta, entre corchetes, con la
convención única de `core.verification.directivas`: `"Dia 1 [LB-01-EXC]"`. La regla R7 la lee.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from core.contracts.presupuesto import Presupuesto, PuntoCurva
from core.verification.directivas import etiqueta_con_codigos

__all__ = ["PeriodoPlan", "PlanInvalido", "con_curva", "generar_curva", "plan_secuencial"]

#: Un período del plan de trabajo: su etiqueta y la fracción de cada partida que ejecuta.
PeriodoPlan = tuple[str, Sequence[tuple[str, Decimal]]]

CERO = Decimal(0)
FRACCION_COMPLETA = Decimal(1)
FORMATO_PERIODO = "Dia {n}"


# El sufijo `Error` (N818) se omite a propósito, igual que en `core.catalog.errores`: los
# identificadores del proyecto van en español y «PlanInvalidoError» mezcla los dos idiomas.
class PlanInvalido(ValueError):  # noqa: N818
    """El plan de trabajo no reparte exactamente una vez cada partida del presupuesto."""


def generar_curva(
    presupuesto: Presupuesto,
    plan: Sequence[PeriodoPlan],
    cuantizar: Decimal | None = None,
) -> tuple[PuntoCurva, ...]:
    """Curva de inversión del presupuesto según el plan de trabajo.

    El monto de cada período es la suma de `fraccion × total de la partida`; con `cuantizar` (por
    ejemplo `Decimal("0.01")`) se redondea a ese paso. El último período absorbe el residuo: vale
    `presupuesto.total` menos lo repartido antes, y su acumulado es el total exacto.

    Lanza `PlanInvalido` si el plan menciona un código que el presupuesto no tiene o si las
    fracciones de alguna partida presupuestada no suman exactamente uno.
    """
    totales = _totales_por_codigo(presupuesto)
    _validar(plan, totales)
    if not plan:
        return ()

    puntos: list[PuntoCurva] = []
    acumulado = CERO
    ultimo = len(plan) - 1
    for indice, (etiqueta, reparto) in enumerate(plan):
        if indice == ultimo:
            monto = presupuesto.total - acumulado
        else:
            monto = _monto(reparto, totales, cuantizar)
        acumulado += monto
        puntos.append(
            PuntoCurva(
                periodo=etiqueta_con_codigos(etiqueta, [codigo for codigo, _ in reparto]),
                monto=monto,
                acumulado=acumulado,
            )
        )
    return tuple(puntos)


def con_curva(presupuesto: Presupuesto, curva: Sequence[PuntoCurva]) -> Presupuesto:
    """El mismo presupuesto con la curva dada.

    No modifica el original: `Presupuesto` es inmutable.
    """
    return replace(presupuesto, curva=tuple(curva))


def plan_secuencial(presupuesto: Presupuesto, formato: str = FORMATO_PERIODO) -> list[PeriodoPlan]:
    """Plan trivial: una partida por período, ejecutada al 100 %, en el orden del presupuesto.

    Un período por **código** de partida, en el orden de su primera aparición: varios renglones del
    mismo código se ejecutan juntos, igual que `_totales_por_codigo` los acumula (INV‑071).
    """
    codigos = dict.fromkeys(partida.item.codigo_partida for partida in presupuesto.partidas)
    return [
        (formato.format(n=numero), ((codigo, FRACCION_COMPLETA),))
        for numero, codigo in enumerate(codigos, start=1)
    ]


def _totales_por_codigo(presupuesto: Presupuesto) -> dict[str, Decimal]:
    """Monto por código de partida.

    Varios renglones del mismo código se acumulan: el plan los reparte juntos porque `PeriodoPlan`
    identifica la partida por su código, no por su posición.
    """
    totales: dict[str, Decimal] = {}
    for partida in presupuesto.partidas:
        codigo = partida.item.codigo_partida
        totales[codigo] = totales.get(codigo, CERO) + partida.total
    return totales


def _monto(
    reparto: Sequence[tuple[str, Decimal]],
    totales: dict[str, Decimal],
    cuantizar: Decimal | None,
) -> Decimal:
    monto = sum((fraccion * totales[codigo] for codigo, fraccion in reparto), CERO)
    if cuantizar is None:
        return monto
    return monto.quantize(cuantizar, rounding=ROUND_HALF_UP)


def _validar(plan: Sequence[PeriodoPlan], totales: dict[str, Decimal]) -> None:
    repartido: dict[str, Decimal] = dict.fromkeys(totales, CERO)
    desconocidos: list[str] = []
    for _, reparto in plan:
        for codigo, fraccion in reparto:
            if codigo not in repartido:
                if codigo not in desconocidos:
                    desconocidos.append(codigo)
                continue
            repartido[codigo] += fraccion
    if desconocidos:
        raise PlanInvalido(
            "el plan de trabajo reparte partidas que el presupuesto no tiene: "
            + ", ".join(desconocidos)
        )

    incompletas = [
        f"{codigo} suma {suma}" for codigo, suma in repartido.items() if suma != FRACCION_COMPLETA
    ]
    if incompletas:
        raise PlanInvalido(
            "las fracciones del plan de trabajo deben sumar exactamente 1 por partida: "
            + "; ".join(incompletas)
        )
