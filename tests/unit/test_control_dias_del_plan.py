"""Los días hábiles por período de Control salen del plan de la versión (ola 2 del 2026-11-13).

Control convierte cada período del plan en `dias_por_periodo` días hábiles (`core.budget.calendario`).
Se pedían a mano con 5 por omisión: un plan por días («Dia n», el de la primera versión) quedaba
cinco veces más largo en Control. Ahora se proponen desde las etiquetas del plan («Dia n» 1,
«Semana n» 5, «Mes n» 20, las de `aplicacion.plan_rendimientos`) y, si el plan no dice su unidad,
20 (un mes) con un aviso. Oráculo: la tabla de la simulación de la bitácora
`docs/bitacora/2026-11-13-ola2-recongelado-y-plan.md`. Datos FICTICIOS.
"""

from __future__ import annotations

import pytest

from aplicacion.control import DIAS_POR_OMISION, dias_de_las_etiquetas

NO_DICE = (
    "El plan de la versión no dice su unidad (sus períodos no son «Dia n», «Semana n» ni "
    "«Mes n»): se proponen 20 días hábiles, un mes. Cámbielo si sus períodos duran otra cosa."
)
SIN_PLAN = "La versión no tiene plan de trabajo: se proponen 20 días hábiles, un mes."


@pytest.mark.parametrize(
    ("etiquetas", "dias", "unidad"),
    [
        (["Dia 1", "Dia 2", "Dia 3"], 1, "dia"),
        (["Día 1", "Día 2"], 1, "dia"),
        (["Semana 1", "Semana 2"], 5, "semana"),
        (["Mes 1", "Mes 2", "Mes 3"], 20, "mes"),
        (["Dia 1", "Dia 2 (2)"], 1, "dia"),  # la matriz desduplica etiquetas repetidas
    ],
)
def test_la_unidad_del_plan_da_sus_dias(etiquetas, dias, unidad):
    propuesta = dias_de_las_etiquetas(etiquetas)
    assert (propuesta.dias, propuesta.unidad, propuesta.aviso) == (dias, unidad, "")


@pytest.mark.parametrize("etiquetas", [["M1", "M2"], ["Dia 1", "Semana 2"], ["Fase 1"]])
def test_si_el_plan_no_dice_su_unidad_se_proponen_20_con_aviso(etiquetas):
    propuesta = dias_de_las_etiquetas(etiquetas)
    assert (propuesta.dias, propuesta.unidad, propuesta.aviso) == (20, "", NO_DICE)
    assert DIAS_POR_OMISION == 20


def test_sin_plan_tambien_20_con_su_aviso():
    propuesta = dias_de_las_etiquetas([])
    assert (propuesta.dias, propuesta.unidad, propuesta.aviso) == (20, "", SIN_PLAN)
