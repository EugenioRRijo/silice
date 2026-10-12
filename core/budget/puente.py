# core/budget/puente.py
"""Puente entre S1 (reajuste) y S2 (valuaciones), en los dos sentidos (spec S2 §4.7, S1 §8.6).

* `estudio_con_valuaciones` (SL-E4, RF-72): guarda un estudio de reajuste de S1 cuyo ejecutado sale
  de las valuaciones registradas y no anuladas (`ejecutado_por_periodo`) y **cita** cada una en
  `cita_valuacion`. S1 sigue calculando y guardando el estudio con `guardar_estudio`.
* `reajuste_reconocido` (SL-E5, RF-77): la suma de los montos reconocidos de los estudios de S1
  **guardados** con fecha de cálculo menor o igual al corte, sin los reemplazados (S1-R21), en la
  moneda del proyecto. Nunca suma un reajuste proyectado sobre la obra pendiente (S2-R15, RV-12).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _buscar
from core.budget.reajuste import Clausula, Ejecutado, PeriodoDeclarado, guardar_estudio
from core.budget.valuaciones import EjecutadoDelPeriodo, ejecutado_por_periodo
from core.catalog.indices import LADO_POR_DEFECTO

__all__ = [
    "PeriodoDelEstudio",
    "estudio_con_valuaciones",
    "periodos_declarados",
]

CERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class PeriodoDelEstudio:
    """Un período del estudio: sus fechas y, opcionales, la versión revalorada para la comprobación
    directa y la excepción declarada (S1 §8.2)."""

    desde: date
    hasta: date
    version_comprobacion: str = ""
    excepcion: str = ""


def _declarar(
    session: Session, proyecto_nombre: str, periodos: Sequence[PeriodoDelEstudio]
) -> tuple[list[PeriodoDelEstudio], list[PeriodoDeclarado], list[EjecutadoDelPeriodo]]:
    ordenados = sorted(periodos, key=lambda p: (p.desde, p.hasta))
    ejecutados = ejecutado_por_periodo(
        session, proyecto_nombre, [(p.desde, p.hasta) for p in ordenados]
    )
    declarados = [
        PeriodoDeclarado(
            periodo.desde,
            periodo.hasta,
            tuple(
                Ejecutado(
                    linea.codigo, linea.cantidad, "valuaciones " + ", ".join(linea.valuaciones)
                )
                for linea in ejecutado.lineas
                if linea.en_linea_base
            ),
            periodo.version_comprobacion,
            periodo.excepcion,
        )
        for periodo, ejecutado in zip(ordenados, ejecutados, strict=True)
    ]
    return ordenados, declarados, ejecutados


def periodos_declarados(
    session: Session, proyecto_nombre: str, periodos: Sequence[PeriodoDelEstudio]
) -> list[PeriodoDeclarado]:
    """Los períodos de S1 con lo ejecutado de las valuaciones registradas y no anuladas, sin
    guardar nada: es lo que la pantalla de reajuste calcula en memoria (UC-18 paso 3)."""
    return _declarar(session, proyecto_nombre, periodos)[1]


def estudio_con_valuaciones(
    session: Session,
    proyecto_nombre: str,
    codigo_contrato: str,
    clausula: Clausula,
    periodos: Sequence[PeriodoDelEstudio],
    *,
    fecha_calculo: date,
    fuente: str,
    responsable: str,
    reemplaza_a: int | None = None,
    lado: str = LADO_POR_DEFECTO,
    ahora: datetime | None = None,
) -> models.EstudioReajuste:
    """Guarda el estudio de reajuste de la versión `codigo_contrato` con lo ejecutado de las
    valuaciones registradas y no anuladas, asignadas por su *hasta* al período que lo contiene.

    Cada cantidad ejecutada lleva como fuente el número de las valuaciones que la aportan, y cada
    período cita sus valuaciones en `cita_valuacion`. Lo ejecutado por encima de lo presupuestado
    se entrega completo: S1 lo guarda con aviso y reajusta solo `min(Q, q)` (S1-R17). Las partidas
    que la línea base no tiene no se entregan (S1 no tiene su PU del contrato; R13 las marca).
    Hace `flush`, no `commit`."""
    ordenados, declarados, ejecutados = _declarar(session, proyecto_nombre, periodos)
    estudio = guardar_estudio(
        session,
        _buscar(session, proyecto_nombre, codigo_contrato),
        clausula,
        declarados,
        fecha_calculo=fecha_calculo,
        fuente=fuente,
        responsable=responsable,
        reemplaza_a=reemplaza_a,
        lado=lado,
        ahora=ahora,
    )
    filas = session.scalars(
        select(models.PeriodoReajuste)
        .where(models.PeriodoReajuste.estudio_id == estudio.id)
        .order_by(models.PeriodoReajuste.orden)
    ).all()
    for fila, ejecutado in zip(filas, ejecutados, strict=True):
        session.add_all(
            models.CitaValuacion(periodo_id=fila.id, valuacion_id=valuacion.id)
            for valuacion in ejecutado.valuaciones
        )
    session.flush()
    return estudio


def valuaciones_citadas(session: Session, estudio_id: int) -> dict[int, list[str]]:
    """Por orden de período, el número de las valuaciones que el estudio citó."""
    filas = session.execute(
        select(models.PeriodoReajuste.orden, models.Valuacion.numero, models.Valuacion.id)
        .join(models.CitaValuacion, models.CitaValuacion.periodo_id == models.PeriodoReajuste.id)
        .join(models.Valuacion, models.Valuacion.id == models.CitaValuacion.valuacion_id)
        .where(models.PeriodoReajuste.estudio_id == estudio_id)
        .order_by(models.PeriodoReajuste.orden, models.Valuacion.id)
    )
    citadas: dict[int, list[str]] = {}
    for orden, numero, _ in filas:
        citadas.setdefault(orden, []).append(numero)
    return citadas
