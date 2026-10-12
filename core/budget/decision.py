# core/budget/decision.py
"""SL-E6: la decisión de recuperación crea una versión nueva (spec S2 §5.3, RF-79).

Elegir una opción (`core.budget.recuperacion`) crea, en **una transacción**, una versión nueva de
motivo `recuperacion` con el plan de la opción, su curva y su informe (R1-R7 de nuevo sobre la curva
nueva), un `RegistroCambio` por cada fracción del plan que cambió y una `DecisionRecuperacion` con
la foto de lo que el usuario vio. La versión nace en el embudo `guardar_presupuesto` (RV-7) por
`guardar_edicion(motivo="recuperacion")`: este módulo no agrega otro camino que cree versiones.

La **línea base de control no cambia** (S2-R3): el SPI al mismo corte sigue siendo el mismo después
de decidir. Sin fuente o sin responsable se rechaza. No confirma la transacción.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _parametros_de
from core.budget.calendario import dia_habil
from core.budget.control import ResultadoControl
from core.budget.curva import PeriodoPlan, con_curva, generar_curva
from core.budget.edicion import (
    CambioEditado,
    _exigir_respaldo,
    guardar_edicion,
    siguiente_codigo,
    version_vigente,
)
from core.budget.instantanea import plan_de_version
from core.budget.persistencia import (
    _cargar_externos,
    cargar_elaboracion,
)
from core.budget.presupuesto import ResultadoElaboracion, _declarar_externos, _declarar_pendientes
from core.budget.recuperacion import Opcion
from core.catalog import Catalogo
from core.verification import REGLAS, auditar

__all__ = ["Decision", "aplicar_decision", "cambios_de_plan", "decisiones"]

CERO = Decimal(0)
OBJETO_PLAN = "plan"


def _texto(valor: Decimal) -> str:
    """Una fracción como texto estable (sin ceros de relleno ni notación científica)."""
    return format(valor.normalize(), "f")


def cambios_de_plan(
    anterior: list[PeriodoPlan] | tuple[PeriodoPlan, ...] | None,
    nuevo: list[PeriodoPlan] | tuple[PeriodoPlan, ...],
) -> list[CambioEditado]:
    """Un cambio (objeto `plan`) por cada (período, partida) cuya fracción cambió: la fracción
    anterior (0 si la celda no existía) y la nueva. La clave es `<período>|<partida>`, con el
    período por su etiqueta: primero los del plan nuevo y luego los que solo tenía el anterior."""

    def celdas(plan) -> dict[tuple[str, str], Decimal]:
        valores: dict[tuple[str, str], Decimal] = {}
        for etiqueta, reparto in plan or ():
            for codigo, fraccion in reparto:
                clave = (etiqueta, codigo)
                valores[clave] = valores.get(clave, CERO) + fraccion
        return valores

    antes, despues = celdas(anterior), celdas(nuevo)
    claves = [*despues, *(clave for clave in antes if clave not in despues)]
    return [
        CambioEditado(
            OBJETO_PLAN,
            f"{etiqueta}|{codigo}",
            "fraccion",
            _texto(antes.get((etiqueta, codigo), CERO)),
            _texto(despues.get((etiqueta, codigo), CERO)),
        )
        for etiqueta, codigo in claves
        if antes.get((etiqueta, codigo), CERO) != despues.get((etiqueta, codigo), CERO)
    ]


def aplicar_decision(
    session: Session,
    resultado: ResultadoControl,
    opcion: Opcion,
    *,
    catalogo: Catalogo,
    fuente: str,
    responsable: str,
    declaracion_independencia: str = "",
    ahora: datetime | None = None,
) -> models.DecisionRecuperacion:
    """Crea la versión de la opción elegida y guarda la decisión (RF-79).

    `ValueError` si falta la fuente o el responsable, si la opción no aplica, si es «partidas en
    paralelo» sin la declaración de independencia o si el plan de la opción no cambia nada."""
    fuente, responsable = _exigir_respaldo(fuente, responsable)
    if not opcion.aplica:
        raise ValueError(f"la opcion {opcion.nombre!r} no aplica: {opcion.motivo}")
    if opcion.requiere_declaracion and not declaracion_independencia.strip():
        raise ValueError(
            "las partidas en paralelo exigen declarar, con su fuente, que no dependen de las "
            "que estan en curso (S2-R4)"
        )
    instantanea = resultado.instantanea
    proyecto = instantanea.proyecto
    origen = version_vigente(session, proyecto)
    if origen is None:
        raise ValueError("el proyecto no tiene version guardada")
    guardada = cargar_elaboracion(session, proyecto, origen.codigo, catalogo)
    codigo = siguiente_codigo(session, proyecto)
    presupuesto = replace(guardada.presupuesto, codigo=codigo)
    presupuesto = con_curva(presupuesto, generar_curva(presupuesto, opcion.plan))
    informe = _declarar_pendientes(auditar(presupuesto, REGLAS), guardada.pendientes)
    informe = _declarar_externos(informe, _cargar_externos(session, origen, REGLAS))
    cambios = cambios_de_plan(plan_de_version(session, origen), opcion.plan)
    calendario = instantanea.calendario
    termino: date = dia_habil(
        calendario.fecha_inicio, opcion.termino, frozenset(calendario.feriados)
    )
    indicadores = resultado.indicadores
    guardadas: list[models.DecisionRecuperacion] = []

    def registrar(sesion: Session, version: models.Presupuesto) -> None:
        fila = models.DecisionRecuperacion(
            proyecto_id=version.proyecto_id,
            linea_base_id=instantanea.linea_base.id,
            version_resultante_id=version.id,
            fecha_corte=instantanea.corte,
            opcion=opcion.nombre,
            detalle=json.dumps(
                {
                    "detalle": opcion.detalle,
                    "declaracion_independencia": declaracion_independencia.strip(),
                    "requisitos": list(opcion.requisitos),
                    "plan": [
                        [etiqueta, [[c, _texto(f)] for c, f in reparto]]
                        for etiqueta, reparto in opcion.plan
                    ],
                },
                ensure_ascii=False,
                default=str,
            ),
            costo_directo_adicional=opcion.costo_directo_adicional,
            costo_indirecto=opcion.costo_indirecto,
            penalizacion=opcion.penalizacion,
            termino=termino,
            spi=indicadores.spi,
            cpi=indicadores.cpi,
            eac=opcion.eac,
            pe=None if opcion.equilibrio is None else opcion.equilibrio.punto,
            supuestos=json.dumps(
                [
                    {
                        "nombre": s.nombre,
                        "valor": s.valor,
                        "naturaleza": s.naturaleza,
                        "fuente": s.fuente,
                    }
                    for s in opcion.supuestos
                ],
                ensure_ascii=False,
            ),
            fuente=fuente,
            responsable=responsable,
            fecha_hora=ahora or datetime.now(),
        )
        sesion.add(fila)
        sesion.flush()
        guardadas.append(fila)

    nueva = guardar_edicion(
        session,
        proyecto,
        origen.codigo,
        ResultadoElaboracion(presupuesto, informe, guardada.pendientes),
        _parametros_de(origen),
        cambios,
        fuente=fuente,
        responsable=responsable,
        plan=list(opcion.plan),
        ahora=ahora,
        gancho=registrar,
        motivo="recuperacion",
    )
    if nueva is None:
        raise ValueError("la opcion no cambia el plan de la version vigente: no hay nada que crear")
    return guardadas[0]


@dataclass(frozen=True, slots=True)
class Decision:
    """Una decisión recargada: lo que el usuario vio al elegir y la versión que resultó."""

    id: int
    version: str
    fecha_corte: date
    opcion: str
    detalle: dict
    costo_directo_adicional: Decimal
    costo_indirecto: Decimal
    penalizacion: Decimal
    termino: date
    spi: Decimal | None
    cpi: Decimal | None
    eac: Decimal | None
    pe: Decimal | None
    supuestos: tuple[dict, ...]
    fuente: str
    responsable: str
    fecha_hora: datetime


def decisiones(session: Session, proyecto_nombre: str) -> list[Decision]:
    """Las decisiones de recuperación del proyecto, de la más antigua a la más reciente."""
    filas = session.execute(
        select(models.DecisionRecuperacion, models.Presupuesto.codigo)
        .join(
            models.Presupuesto,
            models.Presupuesto.id == models.DecisionRecuperacion.version_resultante_id,
        )
        .join(models.Proyecto, models.Proyecto.id == models.DecisionRecuperacion.proyecto_id)
        .where(models.Proyecto.nombre == proyecto_nombre)
        .order_by(models.DecisionRecuperacion.id)
    )
    return [
        Decision(
            id=fila.id,
            version=codigo,
            fecha_corte=fila.fecha_corte,
            opcion=fila.opcion,
            detalle=json.loads(fila.detalle),
            costo_directo_adicional=fila.costo_directo_adicional,
            costo_indirecto=fila.costo_indirecto,
            penalizacion=fila.penalizacion,
            termino=fila.termino,
            spi=fila.spi,
            cpi=fila.cpi,
            eac=fila.eac,
            pe=fila.pe,
            supuestos=tuple(json.loads(fila.supuestos)),
            fuente=fila.fuente,
            responsable=fila.responsable,
            fecha_hora=fila.fecha_hora,
        )
        for fila, codigo in filas
    ]
