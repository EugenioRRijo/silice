"""Base de la linea base con una partida sin rendimiento estimado vigente (UC-01 3b, INV-088).

Caso de prueba, no ejecucion real (CLAUDE.md §1): la tuberia `LB-02-TUB` pierde su rendimiento
ESTIMADO y su historico queda con dos MEDIDOS de una obra de prueba, 90 y 100 piezas por dia. El
catalogo propone el MEDIDO mas reciente (100, el mismo valor del APU de la linea base), asi que,
declarado como estimado, el presupuesto vuelve a sumar exactamente el de la linea base: ese es el
oraculo, y un 90 lo romperia.

`quitar_precio` es el contraste de U-3 (revision de C5): un `CatalogoIncompleto` que no es de
rendimiento (un insumo sin precio en la lista vigente) no debe ofrecer 3b.
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
#: El insumo al que `quitar_precio` le borra el precio (lo usa el concreto, LB-04-CON).
INSUMO_SIN_PRECIO = "Cemento Portland"
#: Fecha del presupuesto de las pruebas: posterior a los medidos y a la lista de la linea base.
FECHA_PRESUPUESTO = date(2026, 6, 1)


def dejar_sin_estimado(
    sesion: Session,
    codigo: str = CODIGO_SIN_ESTIMADO,
    medidos: tuple[tuple[date, Decimal], ...] = MEDIDOS,
) -> None:
    """Borra los rendimientos ESTIMADOS de `codigo` y registra sus `medidos` sobre la obra de
    prueba (que se registra la primera vez). No confirma."""
    _borrar_rendimientos(sesion, codigo, solo_estimados=True)
    ya_registrada = sesion.scalars(
        select(models.Ejecucion.id).where(models.Ejecucion.referencia == REFERENCIA_OBRA)
    ).one_or_none()
    if ya_registrada is None:
        registrar_ejecucion(sesion, REFERENCIA_OBRA, fecha_inicio=MEDIDOS[0][0])
    for fecha, valor in medidos:
        registrar_rendimiento(
            sesion,
            codigo,
            valor,
            TipoRendimiento.MEDIDO,
            fecha,
            condiciones="obra de prueba de UC-01 3b: no es una medicion real",
            referencia_ejecucion=REFERENCIA_OBRA,
        )


def dejar_sin_historico(sesion: Session, codigo: str) -> None:
    """Borra todos los rendimientos de `codigo`: no hay nada que proponer. No confirma."""
    _borrar_rendimientos(sesion, codigo, solo_estimados=False)


def _borrar_rendimientos(sesion: Session, codigo: str, *, solo_estimados: bool) -> None:
    partida_id = sesion.scalars(
        select(models.Partida.id).where(models.Partida.codigo == codigo)
    ).one()
    condicion = [models.Rendimiento.partida_id == partida_id]
    if solo_estimados:
        condicion.append(models.Rendimiento.tipo == TipoRendimiento.ESTIMADO.value)
    sesion.execute(delete(models.Rendimiento).where(*condicion))


def quitar_precio(sesion: Session) -> None:
    """Borra de toda lista el precio de `INSUMO_SIN_PRECIO`. No confirma."""
    insumos = select(models.Insumo.id).where(models.Insumo.descripcion == INSUMO_SIN_PRECIO)
    borrados = sesion.execute(
        delete(models.PrecioInsumo).where(models.PrecioInsumo.insumo_id.in_(insumos))
    )
    assert borrados.rowcount > 0, f"la linea base no tiene precio de {INSUMO_SIN_PRECIO!r}"
