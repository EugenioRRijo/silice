"""Base de la linea base con una partida sin rendimiento estimado vigente (UC-01 3b, INV-088).

Caso de prueba, no ejecucion real (CLAUDE.md §1): la tuberia `LB-02-TUB` pierde su rendimiento
ESTIMADO y su historico queda con dos MEDIDOS de una obra de prueba, 90 y 100 piezas por dia. El
catalogo propone el MEDIDO mas reciente (100, el mismo valor del APU de la linea base), asi que,
declarado como estimado, el presupuesto vuelve a sumar exactamente el de la linea base: ese es el
oraculo, y un 90 lo romperia.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core import models
from core.catalog import registrar_ejecucion, registrar_rendimiento
from core.contracts.apu import TipoRendimiento

CODIGO_SIN_ESTIMADO = "LB-02-TUB"
REFERENCIA_OBRA = "OBRA-PRUEBA-3B"
#: Los dos rendimientos medidos del historico, del mas antiguo al mas reciente.
MEDIDOS = ((date(2026, 5, 1), Decimal("90")), (date(2026, 5, 10), Decimal("100")))
#: Fecha del presupuesto de las pruebas: posterior a los medidos y a la lista de la linea base.
FECHA_PRESUPUESTO = date(2026, 6, 1)


def dejar_sin_estimado(sesion: Session) -> None:
    """Borra los rendimientos ESTIMADOS de `LB-02-TUB` y registra los dos MEDIDOS. No confirma."""
    partida_id = sesion.scalars(
        select(models.Partida.id).where(models.Partida.codigo == CODIGO_SIN_ESTIMADO)
    ).one()
    sesion.execute(
        delete(models.Rendimiento).where(
            models.Rendimiento.partida_id == partida_id,
            models.Rendimiento.tipo == TipoRendimiento.ESTIMADO.value,
        )
    )
    registrar_ejecucion(sesion, REFERENCIA_OBRA, fecha_inicio=MEDIDOS[0][0])
    for fecha, valor in MEDIDOS:
        registrar_rendimiento(
            sesion,
            CODIGO_SIN_ESTIMADO,
            valor,
            TipoRendimiento.MEDIDO,
            fecha,
            condiciones="obra de prueba de UC-01 3b: no es una medicion real",
            referencia_ejecucion=REFERENCIA_OBRA,
        )
