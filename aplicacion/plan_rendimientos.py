"""El plan de trabajo desde los rendimientos (MP-7, Tarea 21; diseño §11, meta 1).

La duración de cada partida es su cantidad entre el rendimiento de su APU (unidades por día de una
cuadrilla) y las cuadrillas que se le asignan, redondeada hacia arriba al medio día. Las partidas se
encadenan en el orden del presupuesto: cada una empieza en el mayor fin alcanzado, salvo las
marcadas en paralelo, que empiezan donde empezó la anterior. El plan sale en días hábiles («Dia n»,
`FORMATO_PERIODO` del núcleo) o en semanas de 5 días hábiles («Semana n»), y entra al núcleo como
dato (`PeriodoPlan`), igual que un plan editado a mano (choque 1 del plan): el núcleo no se toca.

Así la curva, el punto de equilibrio y la detección de retrasos parten del tiempo que de verdad
toma cada partida, no de «una partida por día» (`core.budget.plan_secuencial`), que hacía decir
«adelantada» a una obra atrasada.

Puro: sin base, sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Literal

from core.budget import PeriodoPlan
from core.budget.curva import FORMATO_PERIODO
from core.contracts.apu import ComposicionAPU
from core.contracts.item_computo import ItemComputo

__all__ = [
    "DIAS_POR_SEMANA",
    "MAXIMO_DE_PERIODOS",
    "CuadrillasInvalidas",
    "Duracion",
    "PlanDemasiadoLargo",
    "Unidad",
    "cuadrillas_escritas",
    "duraciones",
    "paralelas_del_plan",
    "plan_del_borrador",
    "plan_por_rendimientos",
]

Unidad = Literal["dia", "semana"]

#: Días hábiles de un período «Semana n».
DIAS_POR_SEMANA = 5
#: Los períodos que admite la matriz del plan (`api.esquemas_hoja.EdicionPlan`): un plan más largo
#: no se podría ajustar a mano.
MAXIMO_DE_PERIODOS = 500
#: Las fracciones de un período se escriben a seis decimales (el último período de cada partida
#: absorbe el residuo, de modo que la partida suma exactamente 1).
PASO_DE_FRACCION = Decimal("0.000001")
MAXIMO_DE_CUADRILLAS = 99
FORMATO_SEMANA = "Semana {n}"

CERO = Decimal(0)
UNO = Decimal(1)
MEDIO = Decimal("0.5")
_ENTERO = re.compile(r"[1-9][0-9]*")


class CuadrillasInvalidas(ValueError):  # noqa: N818
    """Las cuadrillas tecleadas de una partida no son un entero de 1 a 99."""


class PlanDemasiadoLargo(ValueError):  # noqa: N818
    """El plan tendría más períodos de los que admite la matriz del editor."""


@dataclass(frozen=True)
class Duracion:
    """Los días hábiles de una partida y el aviso que la persona debe ver (vacío si no hay)."""

    codigo: str
    dias: Decimal
    aviso: str


def _al_medio_dia(dias: Decimal) -> Decimal:
    """`dias` redondeado hacia arriba al medio día: 3,8 → 4; 23,33… → 23,5; 8,75 → 9."""
    return (dias * 2).to_integral_value(rounding=ROUND_CEILING) / 2


def duraciones(
    items: Sequence[ItemComputo],
    composiciones: Mapping[str, ComposicionAPU],
    cuadrillas: Mapping[str, int],
) -> list[Duracion]:
    """La duración de cada partida, en el orden de su primera aparición en `items`.

    Los renglones del mismo código suman su cantidad (el plan identifica la partida por su código,
    como `core.budget.plan_secuencial`). Duración = cantidad ÷ rendimiento ÷ cuadrillas (1 si la
    partida no tiene cuadrillas declaradas), hacia arriba al medio día. Con cantidad 0 la duración
    es 0 (la partida no entra al plan); sin composición (y por tanto sin rendimiento), 1 día; las
    dos con su aviso.
    """
    cantidades: dict[str, Decimal] = {}
    for item in items:
        cantidades[item.codigo_partida] = cantidades.get(item.codigo_partida, CERO) + item.cantidad
    resultado = []
    for codigo, cantidad in cantidades.items():
        composicion = composiciones.get(codigo)
        if cantidad == CERO:
            resultado.append(Duracion(codigo, CERO, f"{codigo} tiene cantidad 0."))
        elif composicion is None:
            resultado.append(
                Duracion(codigo, UNO, f"{codigo} no tiene rendimiento: se le asignó 1 día.")
            )
        else:
            por_dia = composicion.rendimiento * cuadrillas.get(codigo, 1)
            resultado.append(Duracion(codigo, _al_medio_dia(cantidad / por_dia), ""))
    return resultado


def _etiqueta(numero: int, unidad: Unidad) -> str:
    formato = FORMATO_SEMANA if unidad == "semana" else FORMATO_PERIODO
    return formato.format(n=numero)


def _entero_con_miles(numero: int) -> str:
    return f"{numero:,}".replace(",", ".")


def plan_por_rendimientos(
    duraciones: Sequence[Duracion],
    *,
    paralelas: Collection[str] = (),
    unidad: Unidad = "dia",
) -> list[PeriodoPlan]:
    """El plan encadenado de las partidas con duración mayor que 0, en el orden dado.

    Cada partida empieza en el mayor fin alcanzado; una de `paralelas` empieza donde empezó la
    anterior que entró al plan (la primera, en 0). La fracción de un período es el tiempo de la
    partida dentro del período entre su duración, a 0,000001 (`ROUND_HALF_UP`); el último período
    de la partida absorbe el residuo para que sume exactamente 1. `PlanDemasiadoLargo` si pasa de
    `MAXIMO_DE_PERIODOS`.
    """
    por_periodo = Decimal(DIAS_POR_SEMANA if unidad == "semana" else 1)
    tramos: list[tuple[str, Decimal, Decimal]] = []
    mayor_fin = CERO
    inicio_anterior: Decimal | None = None
    for duracion in duraciones:
        if duracion.dias <= CERO:
            continue
        if duracion.codigo in paralelas and inicio_anterior is not None:
            inicio = inicio_anterior
        else:
            inicio = mayor_fin
        fin = inicio + duracion.dias
        tramos.append((duracion.codigo, inicio, fin))
        mayor_fin = max(mayor_fin, fin)
        inicio_anterior = inicio
    total = int((mayor_fin / por_periodo).to_integral_value(rounding=ROUND_CEILING))
    if total > MAXIMO_DE_PERIODOS:
        raise PlanDemasiadoLargo(
            f"El plan desde los rendimientos tendría {_entero_con_miles(total)} períodos y la "
            f"matriz admite {MAXIMO_DE_PERIODOS}: elija semanas o más cuadrillas."
        )
    repartos: list[list[tuple[str, Decimal]]] = [[] for _ in range(total)]
    for codigo, inicio, fin in tramos:
        duracion = fin - inicio
        primero = int((inicio / por_periodo).to_integral_value(rounding=ROUND_FLOOR))
        ultimo = int((fin / por_periodo).to_integral_value(rounding=ROUND_CEILING)) - 1
        repartido = CERO
        for indice in range(primero, ultimo + 1):
            if indice == ultimo:
                fraccion = UNO - repartido
            else:
                desde = max(inicio, indice * por_periodo)
                hasta = min(fin, (indice + 1) * por_periodo)
                fraccion = ((hasta - desde) / duracion).quantize(
                    PASO_DE_FRACCION, rounding=ROUND_HALF_UP
                )
            repartido += fraccion
            repartos[indice].append((codigo, fraccion))
    return [(_etiqueta(n, unidad), tuple(reparto)) for n, reparto in enumerate(repartos, start=1)]


def paralelas_del_plan(plan: Sequence[PeriodoPlan]) -> frozenset[str]:
    """Las partidas cuyo primer período activo es el mismo que el de una partida anterior.

    Con días hábiles es lo que marca `plan_por_rendimientos` con `paralelas`, salvo que la
    anterior dure medio día o menos de su primer período: dos partidas encadenadas que empiezan en
    el mismo período también cuentan (y en semanas es lo común). Lo usa la recuperación (Tarea 27).
    """
    primeros: dict[str, int] = {}
    for indice, (_, reparto) in enumerate(plan):
        for codigo, fraccion in reparto:
            if fraccion > CERO and codigo not in primeros:
                primeros[codigo] = indice
    vistos: set[int] = set()
    paralelas = set()
    for codigo, indice in primeros.items():
        if indice in vistos:
            paralelas.add(codigo)
        vistos.add(indice)
    return frozenset(paralelas)


def cuadrillas_escritas(textos: Mapping[str, str]) -> dict[str, int]:
    """Las cuadrillas tecleadas por partida, como enteros de 1 a `MAXIMO_DE_CUADRILLAS`.

    Solo cifras, sin signo, sin separadores y sin ceros a la izquierda (blancos en los bordes, sí);
    si no, `CuadrillasInvalidas` con el código de la partida.
    """
    cuadrillas = {}
    for codigo, texto in textos.items():
        limpio = texto.strip()
        if not _ENTERO.fullmatch(limpio) or int(limpio) > MAXIMO_DE_CUADRILLAS:
            raise CuadrillasInvalidas(
                f"Las cuadrillas de {codigo} deben ser un número entero de 1 a "
                f"{MAXIMO_DE_CUADRILLAS}."
            )
        cuadrillas[codigo] = int(limpio)
    return cuadrillas


def plan_del_borrador(
    items: Sequence[ItemComputo],
    composiciones: Mapping[str, ComposicionAPU],
    *,
    cuadrillas: Mapping[str, int] | None = None,
    paralelas: Collection[str] = (),
    unidad: Unidad = "dia",
) -> tuple[list[PeriodoPlan], list[str]]:
    """El plan por rendimientos de los renglones de la Hoja y sus avisos, en orden.

    La curva exige que cada partida valorada sume 1 (`core.budget.curva`): las que se quedaron
    fuera del plan por tener cantidad 0 (monto 0) van enteras al último período, sin alargar el
    plan. Sin ningún período, van a un primer período.
    """
    lista = duraciones(items, composiciones, cuadrillas or {})
    plan = plan_por_rendimientos(lista, paralelas=paralelas, unidad=unidad)
    en_el_plan = {codigo for _, reparto in plan for codigo, _ in reparto}
    fuera = tuple(
        (d.codigo, UNO) for d in lista if d.codigo in composiciones and d.codigo not in en_el_plan
    )
    if fuera:
        if plan:
            etiqueta, reparto = plan[-1]
            plan[-1] = (etiqueta, (*reparto, *fuera))
        else:
            plan.append((_etiqueta(1, unidad), fuera))
    return plan, [d.aviso for d in lista if d.aviso]
