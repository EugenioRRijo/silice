# tests/integration/test_ejecutado_por_periodo.py
"""SL-E4: lo ejecutado por período que S2 entrega a S1 (spec S2 RF-72, S2-R16; S1 §8.6).

Las valuaciones registradas y no anuladas, cada una entera en el período mensual que contiene su
fecha *hasta*, con la cantidad del período y la cantidad reajustable `min(Q al cierre, q) -
min(Q al cierre anterior, q)`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from core import models
from core.budget.valuaciones import (
    LineaBaseInvalidada,
    anular_valuacion,
    ejecutado_por_periodo,
)
from core.verification.valuaciones import LineaValuacion
from tests.fixtures import control_ob_s2 as ob

D = Decimal
NOVIEMBRE = (date(2026, 11, 1), date(2026, 11, 30))
DICIEMBRE = (date(2026, 12, 1), date(2026, 12, 31))


def _lineas(periodo):
    return {linea.codigo: (linea.cantidad, linea.reajustable) for linea in periodo.lineas}


def _valuar(sesion, numero, desde, hasta, **cantidades):
    """Una valuación breve (la fecha es el hasta, como exige R14) con las partidas dadas."""
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


def test_ob_s2_entrega_a_noviembre_a_90_y_b_60(obra):
    ob.registrar_v01_y_v02(obra)
    (noviembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert _lineas(noviembre) == {"OB-A": (D(90), D(90)), "OB-B": (D(60), D(60))}
    assert [v.numero for v in noviembre.valuaciones] == ["V-01", "V-02"]
    assert noviembre.avisos == ()
    assert [linea.valuaciones for linea in noviembre.lineas] == [("V-01", "V-02"), ("V-02",)]


def test_una_valuacion_anulada_no_entra(obra):
    _, segunda = ob.registrar_v01_y_v02(obra)
    anular_valuacion(obra, segunda.id, motivo="no aprobada", responsable="Ing.")
    (noviembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert _lineas(noviembre) == {"OB-A": (D(40), D(40))}


def test_lo_valuado_sobre_lo_presupuestado_entrega_el_total_y_reajusta_el_tope_con_aviso(obra):
    ob.registrar_v01_y_v02(obra)
    ob.registrar(obra, ob.VS)  # B 150 mas: acumulado 210 contra 200 presupuestados
    (noviembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    lineas = _lineas(noviembre)
    assert lineas["OB-B"] == (D(210), D(200))
    assert lineas["OB-D"] == (D(5), D(0))  # no presupuestada: nada reajustable
    assert lineas["OB-C"] == (D(10), D(10))
    avisos = " | ".join(noviembre.avisos)
    assert (
        "OB-B: ejecutado 210 en el periodo y solo 200 es reajustable (presupuestado 200" in avisos
    )
    assert "OB-D" in avisos


def test_una_valuacion_que_cruza_el_mes_va_entera_al_periodo_de_su_hasta(obra):
    _valuar(obra, "V-01", date(2026, 11, 30), date(2026, 12, 4), **{"OB-A": "25"})
    noviembre, diciembre = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE, DICIEMBRE])
    assert noviembre.lineas == ()
    assert _lineas(diciembre) == {"OB-A": (D(25), D(25))}


@pytest.mark.parametrize(
    ("hasta", "periodo"),
    [(date(2026, 11, 30), "noviembre"), (date(2026, 12, 1), "diciembre")],
    ids=[
        "hasta el ultimo dia del mes va a ese mes",
        "hasta el primero del siguiente va al siguiente",
    ],
)
def test_frontera_del_mes(obra, hasta, periodo):
    _valuar(obra, "V-01", date(2026, 11, 23), hasta, **{"OB-A": "10"})
    resultado = dict(
        zip(
            ("noviembre", "diciembre"),
            ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE, DICIEMBRE]),
            strict=True,
        )
    )
    assert _lineas(resultado[periodo]) == {"OB-A": (D(10), D(10))}
    otro = "diciembre" if periodo == "noviembre" else "noviembre"
    assert resultado[otro].lineas == ()


def test_lo_acumulado_de_periodos_anteriores_cuenta_para_el_tope(obra):
    _valuar(obra, "V-01", date(2026, 11, 2), date(2026, 11, 27), **{"OB-A": "95"})
    _valuar(obra, "V-02", date(2026, 12, 1), date(2026, 12, 4), **{"OB-A": "20"})
    noviembre, diciembre = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE, DICIEMBRE])
    assert _lineas(noviembre) == {"OB-A": (D(95), D(95))}
    assert _lineas(diciembre) == {"OB-A": (D(20), D(5))}  # 95 + 20 = 115: solo 5 caben en 100
    # Pedir solo diciembre cuenta igual lo de noviembre como ya ejecutado.
    (solo_diciembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [DICIEMBRE])
    assert _lineas(solo_diciembre) == {"OB-A": (D(20), D(5))}


def test_el_acumulado_igual_al_presupuestado_no_avisa_y_un_milesimo_mas_si(obra):
    _valuar(obra, "V-01", date(2026, 11, 2), date(2026, 11, 6), **{"OB-A": "100"})
    (justo,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert justo.avisos == ()
    _valuar(obra, "V-02", date(2026, 11, 9), date(2026, 11, 13), **{"OB-A": "0.001"})
    (pasado,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert _lineas(pasado)["OB-A"] == (D("100.001"), D(100))
    assert pasado.avisos


def test_lo_ejecutado_fuera_de_los_periodos_pedidos_no_se_entrega(obra):
    _valuar(obra, "V-01", date(2026, 10, 5), date(2026, 10, 9), **{"OB-A": "5"})
    (noviembre,) = ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
    assert noviembre.lineas == () and noviembre.valuaciones == ()


def test_pide_al_menos_un_periodo_y_necesita_linea_base(obra, obra_sin_linea_base):
    with pytest.raises(ValueError, match="al menos un periodo"):
        ejecutado_por_periodo(obra, ob.NOMBRE, [])


def test_tras_un_cambio_de_moneda_la_linea_base_invalidada_se_rechaza(obra):
    ob.registrar_v01_y_v02(obra)
    proyecto = obra.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == ob.NOMBRE)
    ).one()
    obra.add(
        models.MonedaProyecto(
            proyecto_id=proyecto.id,
            moneda="Bs",
            desde=datetime(2026, 11, 14),
            version_id=None,
            responsable="Ing.",
            fuente="conversion ficticia",
        )
    )
    obra.flush()
    with pytest.raises(LineaBaseInvalidada, match="declarela de nuevo"):
        ejecutado_por_periodo(obra, ob.NOMBRE, [NOVIEMBRE])
