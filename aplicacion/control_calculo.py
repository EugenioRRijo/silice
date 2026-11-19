"""Cálculo del control (UC-20 1 a 3, siempre) y opciones de recuperación (UC-20 4 a 6, a pedido).

Los precios del corte se quedan en la fachada: leen `aplicacion.precios_declarados`, que está
en el ciclo de la mesa (ola 5).

Salió de `aplicacion/control.py` sin cambios (tarea 4.3 del plan de desenredo);
`aplicacion.control` lo reexporta.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from aplicacion.control_comun import (
    ControlInvalido,
    _decimal,
    _escribir,
)
from aplicacion.control_corte import ultimo_corte
from core import models
from core.budget.control import (
    ResultadoControl,
    calcular_control,
    composiciones_de_la_linea_base,
    contexto_de_recuperacion,
)
from core.budget.decision import aplicar_decision
from core.budget.recuperacion import Opcion, opciones
from core.budget.valor_ganado import PreciosDelCorte
from core.budget.valuaciones import LineaBaseInvalidada
from core.catalog import Catalogo


def calcular_el_control(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    *,
    corte: date | None = None,
    precios: PreciosDelCorte | None = None,
    hoy: date | None = None,
) -> ResultadoControl:
    """El control al corte (sin escribir). Sin `corte`, el de `ultimo_corte`: el *hasta* de la
    última valuación, nunca después de `hoy`. `ControlInvalido` si no hay línea base, si está
    invalidada por un cambio de moneda o si no hay valuaciones ni corte."""
    try:
        if corte is None:
            corte = ultimo_corte(sesion, proyecto, hoy)
        return calcular_control(sesion, proyecto, catalogo=catalogo, corte=corte, precios=precios)
    except LineaBaseInvalidada as error:
        raise ControlInvalido(str(error)) from error
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def calcular_las_opciones(
    resultado: ResultadoControl,
    *,
    objetivo: str = "",
    horas_previas: str = "0",
    independientes: str = "",
) -> tuple[Opcion, ...]:
    """Las cuatro opciones de recuperación a pedido (UC-20 4). `objetivo` es el día hábil objetivo
    (vacío = el fin del plan base). `ControlInvalido` si un límite legal se rompe o si el objetivo
    no es un entero (no se trunca)."""
    dia_objetivo = None
    if objetivo.strip():
        valor = _decimal(objetivo, "objetivo")
        if valor != valor.to_integral_value():
            raise ControlInvalido(f"objetivo: {objetivo!r} debe ser un entero")
        dia_objetivo = int(valor)
    try:
        contexto = contexto_de_recuperacion(
            resultado,
            composiciones_de_la_linea_base(resultado),
            objetivo=dia_objetivo,
            horas_previas=_decimal(horas_previas or "0", "horas extra previas"),
        )
        return opciones(contexto)
    except ValueError as error:
        raise ControlInvalido(str(error)) from None


def elegir_opcion(
    sesion: Session,
    resultado: ResultadoControl,
    opcion: Opcion,
    catalogo: Catalogo,
    *,
    fuente: str,
    responsable: str,
    declaracion_independencia: str = "",
) -> str:
    """UC-20 5 y 6: crea la versión de la opción elegida y guarda la decisión. Devuelve el código de
    la versión nueva."""
    decision = _escribir(
        sesion,
        lambda: aplicar_decision(
            sesion,
            resultado,
            opcion,
            catalogo=catalogo,
            fuente=fuente,
            responsable=responsable,
            declaracion_independencia=declaracion_independencia,
        ),
    )
    return sesion.get(models.Presupuesto, decision.version_resultante_id).codigo
