"""FCAS por componentes con su base legal (plan vial, Tarea 17).

Fuentes: `docs/fuentes/2026-10-30-fuentes-plan-vial.md` §1. El método es el que documentan Dodi y
Salas (2019, `docs/fuentes/Dodi_Salas_2019_FCAS_UJAP.pdf`, §4.2):

    días_pagados   = días calendario + Σ bonificaciones expresadas en días de salario
    fcas_por_días  = (días_pagados − días_trabajados) ÷ días_trabajados
    fcas           = (días_pagados ÷ días_trabajados) × (1 + Σ aportes patronales) − 1

Los aportes patronales son un porcentaje del salario **pagado**, así que se llevan a días
trabajados multiplicando por `días_pagados ÷ días_trabajados`. El motor de Sílice aplica
`sueldo × (1 + fcas)` (`core/costing/motor.py`): `fcas` es una fracción (0,7863 = 78,63 %,
multiplicador × 1,7863).

El bono de alimentación NO es un componente: Sílice ya lo lleva aparte en `bono_alimentacion`, y
contarlo aquí lo contaría dos veces. Un porcentaje se escribe en por ciento (2 = 2 %).

Esta cuenta no toca la base ni el núcleo: el 6,00 por defecto de `ParametrosCosto` queda como está
y lo que se calcula aquí no se aplica solo; se aplica con la edición de parámetros de la Hoja.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

__all__ = [
    "BASES",
    "COMPONENTES_FCAS",
    "DESGLOSE_DIAS_NO_TRABAJADOS",
    "DIAS_CALENDARIO",
    "ComponenteFCAS",
    "ResultadoFCAS",
    "calcular_fcas",
]

#: Las dos bases de un componente: días de salario (bonificaciones) o por ciento del salario pagado.
BASES = ("dias", "porcentaje")
#: Año de 365 días: el período con el que se publican los casos de Dodi y Salas.
DIAS_CALENDARIO = Decimal("365")
#: Lo que se pide a la fuente para marcar un componente como pendiente de cotejo.
_MARCA_A_COTEJAR = "a cotejar"
#: Identificador del primer renglón del desglose: los días pagados que no se trabajan.
DESGLOSE_DIAS_NO_TRABAJADOS = "dias_no_trabajados"
_NO_ADMITIDOS = frozenset({"bono_alimentacion", "cestaticket"})
_CIEN = Decimal(100)


@dataclass(frozen=True)
class ComponenteFCAS:
    """Un componente del FCAS con su valor y su fuente (artículo, cláusula o «a cotejar»)."""

    id: str
    nombre: str
    base: str  # "dias" o "porcentaje"
    valor: Decimal  # días de salario, o por ciento del salario pagado
    fuente: str

    def __post_init__(self) -> None:
        if self.id in _NO_ADMITIDOS:
            raise ValueError(
                "el bono de alimentación no es un componente del FCAS: Sílice ya lo lleva aparte "
                "(bono_alimentacion) y contarlo aquí lo contaría dos veces."
            )
        if self.base not in BASES:
            raise ValueError(
                f"{self.id}: la base debe ser «dias» o «porcentaje», no «{self.base}»."
            )
        if not self.valor.is_finite() or self.valor < 0:
            raise ValueError(f"{self.id}: el valor no puede ser negativo ni infinito.")
        if not self.fuente.strip():
            raise ValueError(f"{self.id}: todo componente exige su fuente (o «a cotejar»).")

    @property
    def a_cotejar(self) -> bool:
        return _MARCA_A_COTEJAR in self.fuente.lower()


@dataclass(frozen=True)
class ResultadoFCAS:
    """`fcas` y `fcas_por_dias` son fracciones sin redondear; el desglose suma `fcas`."""

    fcas: Decimal
    fcas_por_dias: Decimal
    dias_pagados: Decimal
    desglose: tuple[tuple[str, Decimal], ...]  # (id del renglón, su parte del fcas)
    a_cotejar: tuple[str, ...]  # ids de los componentes que piden cotejo


#: Los componentes por defecto (fuentes §1.2 y §1.3). Decisión de Eugenio, 2026-10-31: las pensiones
#: (9 %) van activadas y, junto con el IVSS (11 %, el más alto de los que se citan), «a cotejar».
COMPONENTES_FCAS: tuple[ComponenteFCAS, ...] = (
    ComponenteFCAS(
        "vacaciones_bono",
        "Vacaciones y bono vacacional",
        "dias",
        Decimal("80"),
        "CCT de la construcción 2023, cláusula 47: 80 días de salario básico "
        "(mínimo legal: LOTTT arts. 190 y 192, 15 + 15 días)",
    ),
    ComponenteFCAS(
        "utilidades",
        "Utilidades (de los trabajadores)",
        "dias",
        Decimal("100"),
        "CCT de la construcción 2023, cláusula 48: mínimo 100 días de salario por año "
        "(mínimo legal: LOTTT arts. 131 y 132, 30 días)",
    ),
    ComponenteFCAS(
        "asistencia_puntual",
        "Asistencia puntual y perfecta",
        "dias",
        Decimal("36"),
        "CCT de la construcción 2023, cláusula 41: 6 días por mes (72 al año) por una "
        "probabilidad de asistencia perfecta de 50 % — supuesto declarado",
    ),
    ComponenteFCAS(
        "garantia_prestaciones",
        "Garantía de prestaciones sociales",
        "dias",
        Decimal("72"),
        "CCT de la construcción 2023, cláusula 50: 6 días por mes, 72 el primer año "
        "(mínimo legal: LOTTT art. 142, 15 días por trimestre + 2 por año)",
    ),
    ComponenteFCAS(
        "paro_forzoso",
        "Paro forzoso (Régimen Prestacional de Empleo)",
        "porcentaje",
        Decimal("2"),
        "Ley del Régimen Prestacional de Empleo, art. 46, citado por Dodi y Salas (2019): "
        "cotización de 2,50 % del salario normal, el patrono paga el 80 % (2 %)",
    ),
    ComponenteFCAS(
        "faov",
        "Ahorro habitacional (FAOV)",
        "porcentaje",
        Decimal("2"),
        "Ley del Régimen Prestacional de Vivienda y Hábitat, art. 30, citado por Dodi y Salas "
        "(2019): aporte de 3 % del salario integral, 2/3 el patrono (2 %)",
    ),
    ComponenteFCAS(
        "inces",
        "INCES",
        "porcentaje",
        Decimal("2"),
        "Ley del INCES, citada por Dodi y Salas (2019): 2 % del salario normal "
        "(empresas de 5 o más trabajadores)",
    ),
    ComponenteFCAS(
        "ivss",
        "Seguro social (IVSS)",
        "porcentaje",
        Decimal("11"),
        "Reglamento de la Ley del Seguro Social, art. 109, citado por Dodi y Salas (2019) sin "
        "los porcentajes; 9 %, 10 % u 11 % según el riesgo de la empresa, por defecto el más "
        "alto — a cotejar",
    ),
    ComponenteFCAS(
        "pensiones",
        "Contribución especial para pensiones",
        "porcentaje",
        Decimal("9"),
        "Ley de Protección de las Pensiones de Seguridad Social (G.O. 6.806 Ext., mayo de "
        "2024) y Decreto 4.952: 9 % del total de pagos a los trabajadores — a cotejar la base "
        "exacta y la exoneración temporal",
    ),
)


def calcular_fcas(
    componentes: Sequence[ComponenteFCAS], dias_calendario: Decimal, dias_trabajados: Decimal
) -> ResultadoFCAS:
    """El FCAS de `componentes` en un período; `ValueError` con el motivo si algo no cuadra."""
    if not dias_calendario.is_finite() or dias_calendario <= 0:
        raise ValueError("los días calendario del período deben ser mayores que cero.")
    if not dias_trabajados.is_finite() or dias_trabajados <= 0:
        raise ValueError("los días trabajados deben ser mayores que cero.")
    if dias_trabajados > dias_calendario:
        raise ValueError("los días trabajados no pueden pasar de los días calendario.")
    identificadores = [c.id for c in componentes]
    repetidos = sorted({i for i in identificadores if identificadores.count(i) > 1})
    if repetidos:
        raise ValueError(f"componente repetido: {', '.join(repetidos)}.")

    bonificacion = sum((c.valor for c in componentes if c.base == "dias"), Decimal(0))
    aportes = sum((c.valor for c in componentes if c.base == "porcentaje"), Decimal(0)) / _CIEN
    dias_pagados = dias_calendario + bonificacion
    pagados_por_trabajado = dias_pagados / dias_trabajados

    desglose: list[tuple[str, Decimal]] = [
        (DESGLOSE_DIAS_NO_TRABAJADOS, (dias_calendario - dias_trabajados) / dias_trabajados)
    ]
    for c in componentes:
        if c.base == "dias":
            desglose.append((c.id, c.valor / dias_trabajados))
        else:
            desglose.append((c.id, pagados_por_trabajado * c.valor / _CIEN))
    fcas_por_dias = (dias_pagados - dias_trabajados) / dias_trabajados
    return ResultadoFCAS(
        # (pagados ÷ trabajados) × (1 + aportes) − 1, escrito como días más aportes: sin
        # aportes es exactamente el de días
        fcas=fcas_por_dias + pagados_por_trabajado * aportes,
        fcas_por_dias=fcas_por_dias,
        dias_pagados=dias_pagados,
        desglose=tuple(desglose),
        a_cotejar=tuple(c.id for c in componentes if c.a_cotejar),
    )
