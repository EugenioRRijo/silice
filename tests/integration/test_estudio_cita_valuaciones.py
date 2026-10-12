# tests/integration/test_estudio_cita_valuaciones.py
"""SL-E4, puente a S1 (RV-11; S1 §8.6, criterio de RF-71): el estudio de reajuste cita las
valuaciones registradas y no anuladas por su fecha *hasta*.

Es la prueba que S1 deja a S2 (`test_estudio_cita_valuaciones_por_fecha_hasta`): se escribe en la
fase que entrega `ejecutado_por_periodo`. Usa la revaloración `OB-R01` y la cláusula de
`tests/fixtures/reajuste_ob_s2.py`; el monto reconocido de noviembre es 75,90 (memoria OB-S2).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from core import models
from core.budget.puente import estudio_con_valuaciones, valuaciones_citadas
from core.budget.reajuste import cargar_estudio
from core.budget.valuaciones import anular_valuacion
from core.verification.valuaciones import LineaValuacion
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz

D = Decimal


@pytest.fixture
def con_revaloracion(obra):
    rz.sembrar_revaloracion(obra)
    return obra


def _estudio(sesion, periodos, fecha_calculo=date(2026, 11, 13), **extra):
    return estudio_con_valuaciones(
        sesion,
        ob.NOMBRE,
        ob.CODIGO,
        rz.CLAUSULA,
        periodos,
        fecha_calculo=fecha_calculo,
        fuente="estudio ficticio",
        responsable="Ing.",
        **extra,
    )


def _valuar(sesion, numero, desde, hasta, **cantidades):
    return ob.registrar(
        sesion,
        dict(
            numero=numero,
            desde=desde,
            hasta=hasta,
            fecha=hasta,
            inspector=ob.INSPECTOR,
            lineas=[LineaValuacion(codigo, D(c)) for codigo, c in cantidades.items()],
        ),
    )


def test_el_estudio_usa_lo_ejecutado_de_las_valuaciones_y_cita_cada_una(con_revaloracion):
    ob.registrar_v01_y_v02(con_revaloracion)
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE])
    cargado = cargar_estudio(con_revaloracion, estudio.id)
    periodo = cargado.resultado.periodos[0]
    assert dict(periodo.reajustables) == {"OB-A": D(90), "OB-B": D(60)}
    assert periodo.reconocido == D("75.90")  # A 90 x 0,00 + B 60 x (7,59 - 6,325)
    assert [e.fuente for e in cargado.periodos[0].ejecutado] == [
        "valuaciones V-01, V-02",
        "valuaciones V-02",
    ]
    assert valuaciones_citadas(con_revaloracion, estudio.id) == {0: ["V-01", "V-02"]}


def test_estudio_cita_valuaciones_por_fecha_hasta(con_revaloracion):
    """El criterio del puente: *hasta* = último día del mes cae en ese período y *hasta* = primer
    día del siguiente cae en el siguiente; una anulada no cuenta; una registrada cuenta sin otro
    paso; el estudio cita el número de cada valuación usada."""
    _valuar(con_revaloracion, "V-01", date(2026, 11, 23), date(2026, 11, 30), **{"OB-A": "10"})
    _valuar(con_revaloracion, "V-02", date(2026, 12, 1), date(2026, 12, 4), **{"OB-A": "7"})
    anulada = _valuar(
        con_revaloracion, "V-03", date(2026, 12, 7), date(2026, 12, 11), **{"OB-A": "50"}
    )
    anular_valuacion(con_revaloracion, anulada.id, motivo="no aprobada", responsable="Ing.")
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE, rz.DICIEMBRE], date(2026, 12, 31))
    cargado = cargar_estudio(con_revaloracion, estudio.id)
    assert [dict(p.reajustables) for p in cargado.resultado.periodos] == [
        {"OB-A": D(10)},
        {"OB-A": D(7)},
    ]
    assert valuaciones_citadas(con_revaloracion, estudio.id) == {0: ["V-01"], 1: ["V-02"]}


def test_lo_ejecutado_sobre_lo_presupuestado_se_guarda_y_se_reajusta_hasta_el_tope(
    con_revaloracion,
):
    ob.registrar_v01_y_v02(con_revaloracion)
    ob.registrar(con_revaloracion, ob.VS)  # B 150 mas: 210 contra 200
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE], date(2026, 11, 30))
    cargado = cargar_estudio(con_revaloracion, estudio.id)
    periodo = cargado.resultado.periodos[0]
    assert dict(periodo.reajustables)["OB-B"] == D(200)
    assert periodo.excesos  # S1 lo declara: no se reajusta lo que excede lo presupuestado
    assert "OB-D" not in dict(periodo.reajustables)  # no presupuestada: no se entrega a S1
    assert cargado.estado.value == "cerrado"


def test_el_estudio_recargado_es_identico_aunque_se_anule_una_valuacion_despues(
    con_revaloracion,
):
    primera, _ = ob.registrar_v01_y_v02(con_revaloracion)
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE])
    antes = cargar_estudio(con_revaloracion, estudio.id).resultado.periodos[0]
    anular_valuacion(con_revaloracion, primera.id, motivo="error", responsable="Ing.")
    despues = cargar_estudio(con_revaloracion, estudio.id).resultado.periodos[0]
    assert (despues.reconocido, dict(despues.reajustables)) == (
        antes.reconocido,
        dict(antes.reajustables),
    )


def test_un_periodo_sin_valuaciones_queda_con_cero_y_sin_citas(con_revaloracion):
    ob.registrar_v01_y_v02(con_revaloracion)
    estudio = _estudio(con_revaloracion, [rz.NOVIEMBRE, rz.DICIEMBRE], date(2026, 12, 31))
    assert valuaciones_citadas(con_revaloracion, estudio.id) == {0: ["V-01", "V-02"]}
    filas = con_revaloracion.scalars(
        select(models.CitaValuacion).join(
            models.PeriodoReajuste, models.PeriodoReajuste.id == models.CitaValuacion.periodo_id
        )
    ).all()
    assert len(filas) == 2
