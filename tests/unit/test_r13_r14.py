# tests/unit/test_r13_r14.py
"""SL-E4: R13 y R14 (spec S2 §3.4, RF-74). Conjunto exacto de la valuación sembrada V-S de la
memoria `control_ob_s2.md`, cada frontera de §7.3 y R13 sobre SIS-001 (ARQ-H3). Puras: sin base."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.contracts.verificacion import Severidad
from core.verification import auditar
from core.verification.valuaciones import (
    InstantaneaDeControl,
    LineaValuacion,
    PartidaBase,
    Valuacion,
    reglas_de_control,
)
from tests.fixtures import control_ob_s2 as ob

D = Decimal
INICIO = date(2026, 11, 2)  # lunes
CORTE = date(2026, 11, 20)


def _habiles(a: date, b: date) -> int:
    dias = (a + timedelta(days=n) for n in range((b - a).days + 1))
    return sum(1 for dia in dias if dia.weekday() < 5)


def _hallazgos(valuaciones, *, corte=CORTE, partidas=None):
    instantanea = InstantaneaDeControl(
        corte=corte,
        inicio=INICIO,
        partidas=partidas or _partidas_de_ob_s2(),
        valuaciones=tuple(valuaciones),
        habiles_entre=_habiles,
    )
    informe = auditar(ob.elaborar_ob_s2().presupuesto, reglas_de_control(instantanea))
    return informe.hallazgos


def _partidas_de_ob_s2():
    presupuesto = ob.elaborar_ob_s2().presupuesto
    return tuple(
        PartidaBase(
            p.item.codigo_partida,
            p.item.cantidad,
            p.resultado.costo_directo,
            p.item.origen_id,
            True,
        )
        for p in presupuesto.partidas
    )


def _v(numero, desde, hasta, *, fecha=None, inspector="Ing. Ficticio", lineas=None, id=1):
    return Valuacion(
        id=id,
        numero=numero,
        desde=desde,
        hasta=hasta,
        fecha=hasta if fecha is None else fecha,
        inspector=inspector,
        lineas=tuple(lineas or [LineaValuacion("OB-A", D(1))]),
    )


def _de(regla, hallazgos):
    return [h for h in hallazgos if h.regla == regla]


def test_la_valuacion_sembrada_da_exactamente_los_seis_hallazgos_de_la_memoria():
    valuaciones = [ob.valuacion(ob.V01, 1), ob.valuacion(ob.V02, 2), ob.valuacion(ob.VS, 3)]
    hallazgos = _hallazgos(valuaciones)
    resumen = sorted((h.regla, h.severidad.name, h.origen_ids[0], h.impacto) for h in hallazgos)
    assert resumen == [
        ("R13", "ERROR", "valuacion:V-03:OB-B", D("50.00")),
        ("R13", "ERROR", "valuacion:V-03:OB-D", None),
        ("R14", "ERROR", "valuacion:V-03", None),
        ("R14", "ERROR", "valuacion:V-03", None),
        ("R14", "ERROR", "valuacion:V-03", None),
        ("R14", "ERROR", "valuacion:V-03:OB-C", None),
    ]
    textos = " | ".join(h.descripcion for h in _de("R14", hallazgos))
    for fragmento in (
        "no tiene inspector",
        "anterior a su fin",
        "se solapa",
        "fuera de su periodo",
    ):
        assert fragmento in textos
    exceso = _de("R13", hallazgos)[0]
    assert (exceso.valor_observado, exceso.valor_esperado) == (D(210), D(200))
    assert "memoria-ob-s2:OB-B" in exceso.origen_ids  # atribuye la partida (C5.1)


def test_las_dos_valuaciones_de_la_memoria_no_dan_hallazgos():
    assert _hallazgos(ob.v01_v02(), corte=ob.CORTE) == ()


def test_r13_el_acumulado_igual_a_lo_presupuestado_pasa_y_un_milesimo_mas_falla():
    pasa = _v("V-01", INICIO, date(2026, 11, 6), lineas=[LineaValuacion("OB-A", D(100))])
    falla = _v("V-01", INICIO, date(2026, 11, 6), lineas=[LineaValuacion("OB-A", D("100.001"))])
    assert _de("R13", _hallazgos([pasa])) == []
    (hallazgo,) = _de("R13", _hallazgos([falla]))
    assert hallazgo.impacto == D("0.001") * D(10)


def test_r13_el_exceso_se_suma_entre_valuaciones_y_el_impacto_es_el_total():
    primera = _v("V-01", INICIO, date(2026, 11, 6), lineas=[LineaValuacion("OB-A", D(80))])
    segunda = _v(
        "V-02", date(2026, 11, 9), date(2026, 11, 13), lineas=[LineaValuacion("OB-A", D(30))], id=2
    )
    tercera = _v(
        "V-03", date(2026, 11, 16), date(2026, 11, 20), lineas=[LineaValuacion("OB-A", D(5))], id=3
    )
    (hallazgo,) = _de("R13", _hallazgos([primera, segunda, tercera]))
    assert hallazgo.impacto == D(15) * D(10)  # 115 - 100, a 10,00 de costo directo
    assert hallazgo.origen_ids[0] == "valuacion:V-02:OB-A"  # la que cruza el limite


def test_r13_una_partida_presupuestada_que_el_plan_no_programa_es_advertencia():
    partidas = tuple(
        PartidaBase(p.codigo, p.cantidad, p.unitario, p.origen_id, p.codigo != "OB-C")
        for p in _partidas_de_ob_s2()
    )
    (hallazgo,) = _de("R13", _hallazgos([], partidas=partidas))
    assert hallazgo.severidad is Severidad.ADVERTENCIA
    assert "no la programa" in hallazgo.descripcion


@pytest.mark.parametrize(
    ("fecha", "falla"),
    [(date(2026, 11, 6), False), (date(2026, 11, 5), True)],
    ids=["fecha igual a hasta pasa", "un dia antes falla"],
)
def test_r14_la_fecha_de_la_valuacion_no_es_anterior_a_su_fin(fecha, falla):
    valuacion = _v("V-01", INICIO, date(2026, 11, 6), fecha=fecha)
    hallazgos = [h for h in _de("R14", _hallazgos([valuacion])) if "anterior" in h.descripcion]
    assert bool(hallazgos) is falla


@pytest.mark.parametrize(
    ("campo", "texto"),
    [("numero", "no tiene numero"), ("inspector", "no tiene inspector")],
)
def test_r14_sin_numero_o_sin_inspector_es_error(campo, texto):
    valuacion = _v("" if campo == "numero" else "V-01", INICIO, date(2026, 11, 6))
    if campo == "inspector":
        valuacion = _v("V-01", INICIO, date(2026, 11, 6), inspector="  ")
    (hallazgo,) = _de("R14", _hallazgos([valuacion]))
    assert hallazgo.severidad is Severidad.ERROR and texto in hallazgo.descripcion


def test_r14_sin_fecha_es_error_y_sin_numero_la_clave_es_el_id():
    sin_fecha = Valuacion(7, "", INICIO, date(2026, 11, 6), None, "Ing. Ficticio",
                          (LineaValuacion("OB-A", D(1)),))  # fmt: skip
    hallazgos = _de("R14", _hallazgos([sin_fecha]))
    assert sorted(h.descripcion.split(" no tiene ")[1] for h in hallazgos) == ["fecha", "numero"]
    assert all(h.origen_ids == ("valuacion:#7",) for h in hallazgos)


@pytest.mark.parametrize(
    ("hasta", "falla"),
    [(CORTE, False), (CORTE + timedelta(days=1), True)],
    ids=["hasta igual al corte pasa", "corte mas un dia falla"],
)
def test_r14_la_valuacion_no_termina_despues_del_corte(hasta, falla):
    valuacion = _v("V-01", date(2026, 11, 16), hasta)
    hallazgos = [
        h for h in _de("R14", _hallazgos([valuacion])) if "despues del corte" in h.descripcion
    ]
    assert bool(hallazgos) is falla


@pytest.mark.parametrize(
    ("desde", "falla"),
    [(INICIO, False), (INICIO - timedelta(days=1), True)],
    ids=["desde igual al inicio pasa", "inicio menos un dia falla"],
)
def test_r14_la_valuacion_no_empieza_antes_del_calendario(desde, falla):
    valuacion = _v("V-01", desde, date(2026, 11, 6))
    hallazgos = [
        h for h in _de("R14", _hallazgos([valuacion])) if "antes del inicio" in h.descripcion
    ]
    assert bool(hallazgos) is falla


def test_r14_desde_posterior_a_hasta_es_error():
    (hallazgo,) = [
        h
        for h in _de("R14", _hallazgos([_v("V-01", date(2026, 11, 9), date(2026, 11, 6))]))
        if "despues de su fin" in h.descripcion
    ]
    assert hallazgo.severidad is Severidad.ERROR


@pytest.mark.parametrize(
    ("desde_de_la_segunda", "solapa"),
    [(date(2026, 11, 7), False), (date(2026, 11, 6), True)],
    ids=["periodos contiguos pasan", "un dia de solape falla"],
)
def test_r14_periodos_solapados(desde_de_la_segunda, solapa):
    primera = _v("V-01", INICIO, date(2026, 11, 6))
    segunda = _v("V-02", desde_de_la_segunda, date(2026, 11, 13), id=2)
    hallazgos = [h for h in _de("R14", _hallazgos([primera, segunda])) if "solapa" in h.descripcion]
    assert bool(hallazgos) is solapa


def test_r14_numero_repetido_es_error():
    primera = _v("V-01", INICIO, date(2026, 11, 6))
    segunda = _v("V-01", date(2026, 11, 9), date(2026, 11, 13), id=2)
    (hallazgo,) = [
        h for h in _de("R14", _hallazgos([primera, segunda])) if "repetido" in h.descripcion
    ]
    assert hallazgo.severidad is Severidad.ERROR


@pytest.mark.parametrize(
    ("fecha_de_medicion", "falla"),
    [(date(2026, 11, 6), False), (date(2026, 11, 2), False), (date(2026, 11, 7), True)],
    ids=["en hasta pasa", "en desde pasa", "un dia despues falla"],
)
def test_r14_la_medicion_cae_dentro_del_periodo(fecha_de_medicion, falla):
    valuacion = _v(
        "V-01", INICIO, date(2026, 11, 6), lineas=[LineaValuacion("OB-A", D(1), fecha_de_medicion)]
    )
    hallazgos = [h for h in _de("R14", _hallazgos([valuacion])) if "medicion" in h.descripcion]
    assert bool(hallazgos) is falla


@pytest.mark.parametrize(
    ("segundo_numero", "advierte"),
    [("V-02", False), ("V-03", True)],
    ids=["V-01 y V-02 pasa", "V-01 y V-03 advierte"],
)
def test_r14_numeros_consecutivos_con_prefijo(segundo_numero, advierte):
    primera = _v("V-01", INICIO, date(2026, 11, 6))
    segunda = _v(segundo_numero, date(2026, 11, 9), date(2026, 11, 13), id=2)
    hallazgos = [
        h for h in _de("R14", _hallazgos([primera, segunda])) if "consecutivas" in h.descripcion
    ]
    assert bool(hallazgos) is advierte
    assert all(h.severidad is Severidad.ADVERTENCIA for h in hallazgos)


@pytest.mark.parametrize(
    ("desde_de_la_segunda", "hueco"),
    [(date(2026, 11, 9), False), (date(2026, 11, 10), True)],
    ids=["viernes a lunes no hay hueco", "martes deja un dia habil sin cubrir"],
)
def test_r14_hueco_de_dias_habiles_entre_valuaciones_consecutivas(desde_de_la_segunda, hueco):
    primera = _v("V-01", INICIO, date(2026, 11, 6))
    segunda = _v("V-02", desde_de_la_segunda, date(2026, 11, 13), id=2)
    hallazgos = [
        h for h in _de("R14", _hallazgos([primera, segunda])) if "sin cubrir" in h.descripcion
    ]
    assert bool(hallazgos) is hueco
    assert all(h.severidad is Severidad.INFO for h in hallazgos)


def test_r13_sirve_a_un_presupuesto_de_otro_dominio_sis_001():
    """ARQ-H3: R13 no conoce dominios; sobre SIS-001 da su conjunto exacto."""
    from core.budget import generar_presupuesto
    from scripts import seed_sistemas as sis

    presupuesto = generar_presupuesto(
        sis.items_sistemas(),
        sis.composiciones_sistemas(),
        sis.sis.PARAMETROS_SISTEMAS,
        codigo="SIS-001",
        fecha=sis.FECHA_TABULADOR,
        moneda="USD",
    )
    partidas = tuple(
        PartidaBase(
            p.item.codigo_partida, p.item.cantidad, p.resultado.costo_directo, p.item.origen_id
        )
        for p in presupuesto.partidas
    )
    primera = presupuesto.partidas[0]
    codigo, cantidad = primera.item.codigo_partida, primera.item.cantidad
    valuacion = _v(
        "V-01",
        INICIO,
        date(2026, 11, 6),
        lineas=[LineaValuacion(codigo, cantidad + D(1)), LineaValuacion("SIS-NO-EXISTE", D(1))],
    )
    instantanea = InstantaneaDeControl(CORTE, INICIO, partidas, (valuacion,), _habiles)
    hallazgos = auditar(presupuesto, reglas_de_control(instantanea)).hallazgos
    por_origen = {h.origen_ids[0]: h for h in hallazgos}
    assert sorted(por_origen) == sorted(
        [f"valuacion:V-01:{codigo}", "valuacion:V-01:SIS-NO-EXISTE"]
    )
    assert {(h.regla, h.severidad.name) for h in hallazgos} == {("R13", "ERROR")}
    assert por_origen[f"valuacion:V-01:{codigo}"].impacto == primera.resultado.costo_directo
    assert por_origen["valuacion:V-01:SIS-NO-EXISTE"].impacto is None
