# tests/integration/test_reajuste_reconocido.py
"""SL-E5: el reajuste ya reconocido que entra al punto de equilibrio proyectado (spec S2 §4.7,
S2-R15; RV-12; S1-R20 y S1-R21).

Es la suma de los montos reconocidos de los estudios de S1 **guardados** con fecha de cálculo menor
o igual al corte, sin los reemplazados: nunca un reajuste proyectado. El escenario «con reajuste»
de la memoria `control_ob_s2.md` es un estudio de noviembre «parcial al corte» de 75,90.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.budget.puente import estudio_con_valuaciones, reajuste_reconocido
from core.budget.reajuste import Mecanismo
from core.verification.valuaciones import LineaValuacion
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz

D = Decimal
CORTE = date(2026, 11, 13)


@pytest.fixture
def con_revaloracion(obra):
    ob.registrar_v01_y_v02(obra)
    rz.sembrar_revaloracion(obra)
    return obra


def _guardar(sesion, fecha_calculo, clausula=rz.CLAUSULA, **extra):
    return estudio_con_valuaciones(
        sesion, ob.NOMBRE, ob.CODIGO, clausula, [rz.NOVIEMBRE], fecha_calculo=fecha_calculo,
        fuente="estudio ficticio", responsable="Ing.", **extra,
    )  # fmt: skip


def test_sin_estudios_guardados_el_reajuste_reconocido_es_cero(con_revaloracion):
    reconocido = reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE)
    assert (reconocido.monto, reconocido.estudios, reconocido.moneda) == (D(0), (), "USD")


def test_el_estudio_parcial_de_la_memoria_suma_75_90(con_revaloracion):
    estudio = _guardar(con_revaloracion, CORTE)
    reconocido = reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE)
    assert reconocido.monto == D("75.90")
    (sumado,) = reconocido.estudios
    assert (sumado.id, sumado.estado, sumado.monto) == (estudio.id, "parcial al corte", D("75.90"))


def test_un_estudio_guardado_despues_del_corte_no_cuenta(con_revaloracion):
    _guardar(con_revaloracion, date(2026, 11, 14))
    assert reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE).monto == 0
    assert reajuste_reconocido(con_revaloracion, ob.NOMBRE, date(2026, 11, 14)).monto == D("75.90")


def test_de_un_parcial_y_su_cierre_cuenta_solo_el_mas_reciente(con_revaloracion):
    parcial = _guardar(con_revaloracion, CORTE)
    ob.registrar(
        con_revaloracion,
        dict(
            numero="V-03",
            desde=date(2026, 11, 23),
            hasta=date(2026, 11, 27),
            fecha=date(2026, 11, 30),
            inspector=ob.INSPECTOR,
            lineas=[LineaValuacion("OB-B", D(20))],
        ),
    )
    cierre = _guardar(con_revaloracion, date(2026, 11, 30), reemplaza_a=parcial.id)
    assert cierre.estado == "cerrado"
    entre = reajuste_reconocido(con_revaloracion, ob.NOMBRE, date(2026, 11, 20))
    assert entre.monto == D("75.90")  # el cierre se guarda despues: el parcial aun suma
    al_cierre = reajuste_reconocido(con_revaloracion, ob.NOMBRE, date(2026, 11, 30))
    assert al_cierre.monto == D("101.20")  # B 80 x (7,59 - 6,325): no 177,10
    assert [e.id for e in al_cierre.estudios] == [cierre.id]


def test_con_ambos_suma_el_monto_del_mecanismo_pagadero(con_revaloracion):
    ambos = replace(
        rz.CLAUSULA,
        mecanismo=Mecanismo.AMBOS,
        mecanismo_pagadero=Mecanismo.COMPROBACION,
        fuente_pagadero="clausula 12 del contrato ficticio",
    )
    _guardar(con_revaloracion, CORTE, clausula=ambos)
    assert reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE).monto == D("75.90")


def test_con_ambos_y_la_escalatoria_pagadera_los_indices_planos_dan_cero(con_revaloracion):
    escalatoria = replace(
        rz.CLAUSULA,
        mecanismo=Mecanismo.AMBOS,
        mecanismo_pagadero=Mecanismo.ESCALATORIA,
        fuente_pagadero="clausula 12 del contrato ficticio",
    )
    _guardar(con_revaloracion, CORTE, clausula=escalatoria)
    assert reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE).monto == 0


def test_un_estudio_en_otra_moneda_no_se_suma_en_silencio_se_declara_omitido(con_revaloracion):
    estudio = _guardar(con_revaloracion, CORTE)
    estudio.moneda = "Bs"  # lo que quedaria tras un cambio de moneda del proyecto
    con_revaloracion.flush()
    reconocido = reajuste_reconocido(con_revaloracion, ob.NOMBRE, CORTE)
    assert reconocido.monto == 0 and reconocido.estudios == ()
    assert [e.id for e in reconocido.omitidos] == [estudio.id]
