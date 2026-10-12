# core/budget/control.py
"""SL-E5: el control de la obra al corte, de la base de datos al resultado (spec S2 §4, §5.3).

`calcular_control` lee la instantánea de control (`core.budget.valuaciones`), convierte los costos
reales con la tasa de su fecha (S1), toma los precios del corte y el reajuste ya reconocido y
llama a las funciones puras de `core.budget.valor_ganado`. **Nada derivado se guarda**: los
indicadores, las alertas, los hallazgos de R13-R14 y la reproyección se recalculan cada vez, sin
reescribir filas (S2-R13, RV-9). Los parámetros de control sí se guardan, con su `RegistroCambio`.

Un costo real sin tasa aplicable (más de 7 días sin tasa, S1-R2) deja el AC «no disponible» con la
lista de esos costos; PV, EV, SPI, el precio y el término se calculan igual (S2-R17, REQ-25).
"""

from __future__ import annotations

from decimal import Decimal

from core.budget.calendario import numero_de_dia, periodo_de
from core.budget.valor_ganado import (
    EstadoObra,
    PreciosDelCorte,
    partidas_de_plan,
)
from core.budget.valuaciones import InstantaneaControl

__all__ = [
    "construir_estado",
]

CERO = Decimal(0)


def construir_estado(
    instantanea: InstantaneaControl,
    *,
    costo_real: Decimal | None,
    motivo_costo: str = "",
    precios: PreciosDelCorte | None = None,
) -> EstadoObra:
    """El `EstadoObra` puro al corte: partidas con su plan, el día hábil del corte y lo ejecutado
    por partida y por período del *hasta* (valuaciones con *hasta* menor o igual al corte)."""
    calendario = instantanea.calendario
    feriados = frozenset(calendario.feriados)
    largo = calendario.dias_por_periodo
    ejecutado: dict[str, Decimal] = {}
    por_periodo: dict[tuple[str, int], Decimal] = {}
    ultima = 0
    for valuacion in instantanea.para_el_valor_ganado():
        # Una valuacion que termina antes del primer dia habil cae en el periodo 1.
        periodo = max(1, periodo_de(calendario.fecha_inicio, largo, valuacion.hasta, feriados))
        ultima = max(ultima, numero_de_dia(calendario.fecha_inicio, valuacion.hasta, feriados))
        for linea in valuacion.lineas:
            ejecutado[linea.codigo_partida] = (
                ejecutado.get(linea.codigo_partida, CERO) + linea.cantidad
            )
            clave = (linea.codigo_partida, periodo)
            por_periodo[clave] = por_periodo.get(clave, CERO) + linea.cantidad
    return EstadoObra(
        partidas=partidas_de_plan(
            instantanea.presupuesto, instantanea.plan, instantanea.linea_base.perspectiva
        ),
        etiquetas=tuple(etiqueta for etiqueta, _ in instantanea.plan),
        dias_por_periodo=largo,
        dia=numero_de_dia(calendario.fecha_inicio, instantanea.corte, feriados),
        ejecutado=ejecutado,
        por_periodo=por_periodo,
        perspectiva=instantanea.linea_base.perspectiva,
        costo_real=costo_real,
        motivo_costo=motivo_costo,
        precios=precios,
        dia_ultima_valuacion=ultima,
    )


# ---------------------------------------------------------------------------------------------
# Parámetros de control (S2 §4.5, §4.6)
# ---------------------------------------------------------------------------------------------
