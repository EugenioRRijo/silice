"""Dos defectos del nucleo hallados por la hoja de SF3 (expedientes SF-E8 y SF-E9).

SF-E8: `actualizar_precios` guardaba la version revalorada sin su reparto por partida.
SF-E9: `siguiente_codigo` ignoraba los codigos de version no numericos (`TI-001`).

Los oraculos son literales: el reparto 40/60 escrito a mano y los codigos esperados de cada caso.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from core.budget import actualizar_precios, cargar_elaboracion, crear_proyecto, plan_secuencial
from core.budget.edicion import siguiente_codigo
from core.budget.instantanea import plan_de_version
from core.budget.persistencia import _buscar
from core.catalog import Catalogo, crear_lista_desde_archivo
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.versiones import elaborar_001, guardar_001

D = Decimal
CODIGO = linea_base.CODIGO_PRESUPUESTO
PARTIDAS = linea_base.CODIGOS_LINEA_BASE


def _plan_partido():
    """Cada partida se reparte 40 % en el periodo 1 y 60 % en el 2: no es inferible de la curva."""
    return [
        ("Semana 1", tuple((codigo, D("0.4")) for codigo in PARTIDAS)),
        ("Semana 2", tuple((codigo, D("0.6")) for codigo in PARTIDAS)),
    ]


@pytest.fixture
def v001_partida(sesion):
    proyecto = sembrar(sesion)
    guardar_001(sesion, proyecto, elaborar_001(sesion, plan=_plan_partido()), plan=_plan_partido())
    sesion.commit()
    return proyecto


def _lista_nueva(sesion):
    muestra = Path(__file__).resolve().parents[2] / "data" / "samples" / "precios"
    return crear_lista_desde_archivo(
        sesion,
        muestra / "lista_2026-06-01.csv",
        nombre="Lista de precios 01/06/2026",
        moneda=linea_base.MONEDA,
        fecha_vigencia=date(2026, 6, 1),
        origen="lista_2026-06-01.csv",
    ).lista


# ---------------------------------------------------------------------------------------------
# SF-E8: revalorar conserva el plan que se le pasa
# ---------------------------------------------------------------------------------------------


def test_la_version_revalorada_guarda_el_plan_que_se_le_pasa(sesion, v001_partida):
    origen = _buscar(sesion, NOMBRE_PROYECTO, CODIGO)
    plan = plan_de_version(sesion, origen)
    assert plan == _plan_partido()  # el origen si lo tiene

    actualizar_precios(sesion, NOMBRE_PROYECTO, CODIGO, _lista_nueva(sesion), "002", plan=plan)
    sesion.commit()

    nueva = _buscar(sesion, NOMBRE_PROYECTO, "002")
    assert plan_de_version(sesion, nueva) == _plan_partido()
    curva = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "002", Catalogo(sesion)).presupuesto.curva
    assert [p.periodo for p in curva] == [1, 2]
    total = cargar_elaboracion(sesion, NOMBRE_PROYECTO, "002", Catalogo(sesion)).presupuesto.total
    assert abs(curva[0].monto - total * D("0.4")) <= D("0.01")
    assert abs(curva[-1].acumulado - total) <= D("0.01")


def test_el_plan_como_funcion_tambien_se_guarda(sesion):
    proyecto = sembrar(sesion)
    guardar_001(sesion, proyecto, elaborar_001(sesion))
    sesion.commit()

    actualizar_precios(
        sesion, NOMBRE_PROYECTO, CODIGO, _lista_nueva(sesion), "002", plan=plan_secuencial
    )
    sesion.commit()

    assert plan_de_version(sesion, _buscar(sesion, NOMBRE_PROYECTO, "002")) == plan_de_version(
        sesion, _buscar(sesion, NOMBRE_PROYECTO, CODIGO)
    )


def test_sin_plan_la_revaloracion_no_lo_conserva_ruling_sf3_r4(sesion, v001_partida):
    actualizar_precios(sesion, NOMBRE_PROYECTO, CODIGO, _lista_nueva(sesion), "002")
    sesion.commit()

    nueva = _buscar(sesion, NOMBRE_PROYECTO, "002")
    assert plan_de_version(sesion, nueva) is None


# ---------------------------------------------------------------------------------------------
# SF-E9: siguiente_codigo reconoce prefijo y numero
# ---------------------------------------------------------------------------------------------


def _con_versiones(sesion, *codigos):
    proyecto = sembrar(sesion)
    for codigo in codigos:
        guardar_001(sesion, proyecto, elaborar_001(sesion, codigo=codigo))
    sesion.commit()


@pytest.mark.parametrize(
    ("codigos", "esperado"),
    [
        (("TI-001",), "TI-002"),
        (("001",), "002"),
        (("001", "002"), "003"),
        (("TI-001", "TI-002"), "TI-003"),
        (("TI-001", "TI-003"), "TI-004"),  # huecos: sigue al mayor
        (("001", "003"), "004"),
        (("001", "TI-001"), "TI-002"),  # mezcla: manda la ultima version guardada
        (("TI-001", "002"), "003"),
        (("TI-001", "002", "TI-002"), "TI-003"),
        (("PRE",), "001"),  # sin numero: la convencion
        (("TI-009",), "TI-010"),
        (("TI-0999",), "TI-1000"),  # ancho del mayor
    ],
)
def test_siguiente_codigo_reconoce_prefijo_y_numero(sesion, codigos, esperado):
    _con_versiones(sesion, *codigos)

    assert siguiente_codigo(sesion, NOMBRE_PROYECTO) == esperado


def test_siguiente_codigo_sin_versiones_es_001(sesion):
    sembrar(sesion)
    crear_proyecto(sesion, "Vacio")

    assert siguiente_codigo(sesion, "Vacio") == "001"


def test_siguiente_codigo_nunca_repite_un_codigo_existente(sesion):
    # `001` no numerico del proyecto y un `TI-002` posterior: el siguiente del prefijo vigente
    # (TI-) es TI-003, y si ya existiera se saltaria.
    _con_versiones(sesion, "TI-001", "TI-002", "001")
    existentes = {"TI-001", "TI-002", "001"}

    codigo = siguiente_codigo(sesion, NOMBRE_PROYECTO)

    assert codigo not in existentes
    assert codigo == "002"
