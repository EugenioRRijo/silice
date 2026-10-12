# tests/unit/test_reajuste.py
"""Oráculos: memorias s1_reajuste.md y s1_reajuste_por_partida.md; fronteras de S1 §9.2."""

from datetime import date
from decimal import Decimal as D  # noqa: N817

import pytest

from core.budget.reajuste import (
    Clausula,
    Componente,
    Ejecutado,
    EstadoEstudio,
    Estructura,
    Mecanismo,
    PartidaContrato,
    PeriodoDeclarado,
    calcular_estudio,
    coeficiente_de_partida,
)
from core.catalog.indices import ValorFechado
from core.contracts.apu import ResultadoAPU

ENERO, FEBRERO = date(2026, 1, 1), date(2027, 2, 1)
SERIES = {"materiales": "FIC-MAT", "equipos": "FIC-EQU", "mano_obra": "FIC-MO"}
VALORES = {"FIC-MAT": ("200", "230"), "FIC-EQU": ("150", "165"), "FIC-MO": ("80", "100")}
C2 = D("0.01")


def _indices(provisional=False, sin=()):
    salida = {}
    for n, (serie, (i0, im)) in enumerate(VALORES.items()):
        salida[(serie, ENERO)] = ValorFechado(serie, ENERO, D(i0), False, n + 1)
        if serie not in sin:
            salida[(serie, FEBRERO)] = ValorFechado(serie, FEBRERO, D(im), provisional, n + 10)
    return salida


def _clausula(
    estructura=Estructura.DECLARADA,
    mecanismo=Mecanismo.AMBOS,
    pagadero=None,
    pesos=("0.5", "0.2", "0.3"),
    duracion=24,
    inicio=date(2026, 1, 15),
):
    componentes = tuple(
        Componente(c, s, D(p) if estructura is Estructura.DECLARADA else None)
        for (c, s), p in zip(SERIES.items(), pesos, strict=True)
    )
    return Clausula(
        inicio,
        duracion,
        inicio,
        "mensual",
        mecanismo,
        estructura,
        componentes,
        ENERO,
        D("0.10"),
        "memoria",
        "contrato ficticio",
        "Ing.",
        mecanismo_pagadero=pagadero,
        fuente_pagadero="contrato" if pagadero else "",
    )


def _r(m, e, o, factor=D(1)):
    cd = m + e + o
    return ResultadoAPU(m, e, o, cd, cd * factor, cd * factor)


DECLARADA = {"S1-R01": PartidaContrato("S1-R01", D(100), _r(D(100), D(0), D(0)), D(1000))}
POR_PARTIDA = {
    "A": PartidaContrato("A", D("97.50"), _r(D(45), D("7.50"), D("22.50"), D("1.30")), D(400)),
    "B": PartidaContrato("B", D("208.00"), _r(D(32), D(48), D(80), D("1.30")), D(120)),
}


def _periodo(ejecutado, desde=date(2027, 2, 1), hasta=date(2027, 2, 28), excepcion=""):
    return PeriodoDeclarado(
        desde, hasta, tuple(Ejecutado(c, D(q), "AV-01") for c, q in ejecutado), "002", excepcion
    )


def _calcular(
    clausula,
    contrato,
    periodo,
    comprobado,
    *,
    indices=None,
    fecha=date(2027, 3, 5),
    moneda="Bs",
    monto=D(100000),
    en_bs=frozenset(),
):
    return calcular_estudio(
        clausula,
        contrato,
        [periodo],
        indices or _indices(),
        moneda=moneda,
        tasas=[D(850)],
        pu_comprobados=[comprobado],
        monto_original=monto,
        fecha_calculo=fecha,
        series_en_bs=en_bs,
    )


def test_memoria_declarada():
    p = _calcular(
        _clausula(), DECLARADA, _periodo([("S1-R01", "1000")]), {"S1-R01": D(116)}
    ).periodos[0]
    assert (p.km, p.escalatoria, p.comprobacion) == (D("1.17"), D("15300"), D("16000"))
    c = p.comparacion
    assert c.diferencia == D("-700")
    assert [
        x.quantize(C2) for x in (c.escalatoria_otra, c.comprobacion_otra, c.diferencia_otra)
    ] == [D("18.00"), D("18.82"), D("-0.82")]


def test_memoria_por_partida():
    assert coeficiente_de_partida(POR_PARTIDA["A"].resultado, *_relativos()) == D("1.175")
    assert coeficiente_de_partida(POR_PARTIDA["B"].resultado, *_relativos()) == D("1.185")
    p = _calcular(
        _clausula(Estructura.POR_PARTIDA),
        POR_PARTIDA,
        _periodo([("A", "400"), ("B", "120")]),
        {"A": D("115.00"), "B": D("247.00")},
        monto=D("63960"),
    ).periodos[0]
    assert (p.escalatoria, p.comprobacion) == (D("10298.34"), D("11680.00"))
    assert p.comparacion.diferencia_otra.quantize(C2) == D("-1.63")  # una sola vez, no −1,62
    testigo = _calcular(
        _clausula(),
        {k: v for k, v in POR_PARTIDA.items()},
        _periodo([("A", "400"), ("B", "120")]),
        None,
    ).periodos[0]
    assert testigo.escalatoria == D("9785.88")


def _relativos():
    return (
        {c: D(VALORES[s][0]) for c, s in SERIES.items()},
        {c: D(VALORES[s][1]) for c, s in SERIES.items()},
    )


@pytest.mark.parametrize(
    "pagadero, esperado", [(Mecanismo.COMPROBACION, D(16000)), (None, D(15300))]
)
def test_monto_reconocido_con_ambos(pagadero, esperado):
    p = _calcular(
        _clausula(pagadero=pagadero), DECLARADA, _periodo([("S1-R01", "1000")]), {"S1-R01": D(116)}
    ).periodos[0]
    assert p.reconocido == esperado


def test_comprobacion_no_disponible_con_pagadero_comprobacion_no_reconoce_nada():
    p = _calcular(
        _clausula(pagadero=Mecanismo.COMPROBACION), DECLARADA, _periodo([("S1-R01", "1000")]), None
    ).periodos[0]
    assert p.comprobacion is None and p.reconocido is None


def test_primer_anio_aniversario_y_doce_meses():
    cl = _clausula(inicio=date(2026, 3, 1))  # aniversario 01/03/2027
    antes = _calcular(
        cl,
        DECLARADA,
        _periodo([("S1-R01", "1")], date(2027, 2, 1), date(2027, 2, 28)),
        {"S1-R01": D(116)},
    ).periodos[0]
    assert antes.escalatoria == 0 and any("primer año" in m for m in antes.marcas)
    with pytest.raises(ValueError, match="3b"):
        _calcular(
            cl, DECLARADA, _periodo([("S1-R01", "1")], date(2027, 2, 15), date(2027, 3, 14)), None
        )
    doce = _calcular(
        _clausula(inicio=date(2026, 3, 1), duracion=12),
        DECLARADA,
        _periodo([("S1-R01", "1")]),
        None,
    ).periodos[0]
    assert doce.escalatoria > 0
    excepcion = _calcular(
        cl, DECLARADA, _periodo([("S1-R01", "1")], excepcion="ruptura, acta 3"), None
    ).periodos[0]
    assert excepcion.escalatoria > 0 and any("excepción" in m for m in excepcion.marcas)


def test_pesos_que_no_suman_uno_indice_faltante_y_provisional():
    with pytest.raises(ValueError, match="0.9999"):
        _clausula(pesos=("0.5", "0.2", "0.2999"))
    falta = _calcular(
        _clausula(), DECLARADA, _periodo([("S1-R01", "1")]), None, indices=_indices(sin=("FIC-MO",))
    ).periodos[0]
    assert falta.escalatoria is None and any("faltante" in m for m in falta.marcas)
    prov = _calcular(
        _clausula(),
        DECLARADA,
        _periodo([("S1-R01", "1")]),
        None,
        indices=_indices(provisional=True),
    ).periodos[0]
    assert "provisional" in prov.marcas


def test_exceso_se_reajusta_hasta_q_con_aviso():
    exacto = _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1000")]), None).periodos[0]
    assert not exacto.excesos
    exceso = _calcular(_clausula(), DECLARADA, _periodo([("S1-R01", "1000.001")]), None).periodos[0]
    assert exceso.excesos == ("S1-R01",) and exceso.escalatoria == D("15300")


def test_avisos_usd_con_indice_bs_nota_10_y_parcial_al_corte():
    r = _calcular(
        _clausula(),
        DECLARADA,
        _periodo([("S1-R01", "1000")]),
        None,
        moneda="USD",
        en_bs=frozenset(SERIES.values()),
        fecha=date(2027, 2, 27),
    )
    assert any("S1-R11" in a for a in r.avisos) and any("INDICIO" in a for a in r.avisos)
    assert r.estado is EstadoEstudio.PARCIAL
    assert (
        _calcular(
            _clausula(), DECLARADA, _periodo([("S1-R01", "1")]), None, fecha=date(2027, 2, 28)
        ).estado
        is EstadoEstudio.CERRADO
    )
