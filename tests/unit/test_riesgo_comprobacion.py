"""Tarea 14 del plan vial: comprobación hacia atrás con cortes móviles.

Los oráculos están escritos a mano. Para que el valor real y el proyectado coincidan **exactos** en
las pruebas de crecimiento constante, la historia sube 50 % cada mes (1,5): las razones son exactas
en `Decimal` (con 22 meses el mayor valor tiene 26 cifras, bajo las 28 del cálculo). Con 1,5, los
multiplicadores del plazo de 6 meses son 1,5; 2,25; 3,375; 5,0625; 7,59375 y 11,390625, que suman
31,171875, y su promedio (gasto uniforme, D-V-3) es 5,1953125.

Con 22 meses de historia (índices 0 a 21, el último es el mes anterior a INICIO) y un plazo de 6, un
corte `c` necesita 12 meses completos antes (los meses 1 a c − 1, así que c ≥ 13) y los 6 del plazo
después (c + 5 ≤ 21, así que c ≤ 16): 4 cortes, c = 13, 14, 15 y 16.

Todo es ficticio: insumos, series y tasa inventados (ninguna cifra real).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from aplicacion.riesgo.comprobacion import Comprobacion, ResultadoCorte, comprobar_hacia_atras
from aplicacion.riesgo.proyeccion import SERIE_TASA, ParametrosProyeccion
from aplicacion.riesgo.series import MapaSeries
from tests.unit.test_riesgo_proyeccion import (
    ASFALTO,
    CARPETA,
    COMPONENTES,
    GASOIL,
    GASOIL_LITRO,
    INICIO,
    MEZCLA,
    PARAMETROS,
    PPI,
    RECETA,
    RIEGO,
    _historia_variable,
    _mes,
    _meses,
    _obra,
)

D = Decimal
TOLERANCIA = D("0.000001")
BASE = D("38582.5")  # 100 × (0,5 × 600 + 10 × 0,5) × 1,265
MAPA = MapaSeries({ASFALTO: PPI, GASOIL_LITRO: GASOIL})
FACTOR_MEDIO = D("5.1953125")  # promedio de 1,5^k, k = 1..6, a mano (véase el encabezado)


def _p(**cambios) -> ParametrosProyeccion:
    return ParametrosProyeccion(inicio=INICIO, trayectorias=cambios.pop("trayectorias", 30), **cambios)


def _serie(valores: list[Decimal]) -> dict[date, Decimal]:
    return dict(zip(_meses(len(valores)), valores, strict=True))


def _exponencial(n: int, razon: Decimal = D("1.5")) -> dict[str, dict[date, Decimal]]:
    """`n` meses que suben `razon` cada mes en las tres series; el último es el mes anterior a INICIO."""
    valores = [D(100) * razon**i for i in range(n)]
    return {
        PPI: _serie(valores),
        GASOIL: _serie(valores),
        SERIE_TASA: _serie([v / 2 for v in valores]),
    }


def _plana(n: int) -> dict[str, dict[date, Decimal]]:
    return {s: _serie([D(100)] * n) for s in (PPI, GASOIL, SERIE_TASA)}


def _comprobar(historia, p=None, **kw) -> Comprobacion:
    presupuesto, composiciones = _obra({RIEGO: D(100)})
    return comprobar_hacia_atras(
        presupuesto, composiciones, PARAMETROS, historia, MAPA, p or _p(meses=6), **kw
    )


def test_sin_sorpresas_cobertura_uno():
    # todo sube 50 % cada mes: la proyección de cada corte es exactamente lo que pasó después
    c = _comprobar(_exponencial(22))

    esperado = BASE * FACTOR_MEDIO  # 38.582,5 × 5,1953125 = 200.447,0703125 (a mano)
    assert c.n_cortes == 4
    assert [r.corte for r in c.cortes] == [_mes(INICIO, -22 + i) for i in (13, 14, 15, 16)]
    for r in c.cortes:
        assert r.dentro is True
        assert r.p50 == r.p80 == r.real
        assert abs(r.real - esperado) < TOLERANCIA
    assert c.cobertura == D(1)
    assert isinstance(c.cobertura, Decimal)


def test_un_choque_queda_fuera():
    # historia plana y, en el mes 20, un salto de +40 % en el asfalto y el gasoil que se queda. Ningún
    # corte lo ve en su ventana (c ≤ 16), así que todos proyectan el total base. En su plazo (meses
    # c .. c + 5): c = 13 y 14 no lo alcanzan (real = base, dentro); c = 15 lo tiene en el 6.º mes
    # (multiplicadores 1, 1, 1, 1, 1, 1,4: promedio 6,4/6) y c = 16 en el 5.º (1, 1, 1, 1, 1,4, 1,4:
    # promedio 6,8/6); ambos quedan fuera.
    historia = _plana(22)
    for s in (PPI, GASOIL):
        for i in (20, 21):
            historia[s][_mes(INICIO, -22 + i)] = D(140)

    c = _comprobar(historia)

    assert [r.dentro for r in c.cortes] == [True, True, False, False]
    assert [r.p80 for r in c.cortes] == [BASE] * 4
    assert [r.real for r in c.cortes[:2]] == [BASE, BASE]
    assert abs(c.cortes[2].real - BASE * D(64) / D(60)) < TOLERANCIA
    assert abs(c.cortes[3].real - BASE * D(68) / D(60)) < TOLERANCIA
    assert c.cobertura == D("0.5")
    assert c.n_cortes == 4


def test_la_proyeccion_no_ve_el_futuro():
    # historia con variaciones distintas (36 meses) y se altera un valor del futuro de los primeros
    # cortes: el P50 y el P80 de todo corte anterior o igual a esa fecha no se mueven; el real sí
    historia = _historia_variable()
    alterada = {s: dict(v) for s, v in historia.items()}
    mes_alterado = _mes(INICIO, -20)  # dentro del plazo del primer corte (-24 .. -19)
    for s in (PPI, GASOIL, SERIE_TASA):
        alterada[s][mes_alterado] = alterada[s][mes_alterado] * 3
    p = _p(meses=6)

    antes = _comprobar(historia, p)
    despues = _comprobar(alterada, p)

    por_corte = {r.corte: r for r in despues.cortes}
    comparados = 0
    for r in antes.cortes:
        if r.corte <= mes_alterado:
            comparados += 1
            assert por_corte[r.corte].p50 == r.p50
            assert por_corte[r.corte].p80 == r.p80
    assert comparados >= 5
    primero = antes.cortes[0]
    assert por_corte[primero.corte].real != primero.real  # el alterado cae en su plazo


def test_informa_el_numero_de_cortes():
    # 22 meses y plazo 6 -> 4 cortes; con plazo 3 el plazo cabe hasta c = 19 -> 7 cortes (13..19)
    historia = _exponencial(22)

    assert _comprobar(historia, _p(meses=6)).n_cortes == 4
    c3 = _comprobar(historia, _p(meses=3))
    assert c3.n_cortes == 7
    assert len(c3.cortes) == c3.n_cortes


def test_un_corte_sin_el_plazo_completo_no_entra():
    # 30 meses planos: sin hueco hay 12 cortes (c = 13..24); falta el último mes de una serie y el
    # corte 24 (su plazo llega al mes 29) sale, y también los de plazo que lo tocan: c + 5 ≥ 29
    historia = _plana(30)
    assert _comprobar(historia).n_cortes == 12

    del historia[GASOIL][_mes(INICIO, -1)]
    c = _comprobar(historia)

    assert c.n_cortes == 11
    assert c.cortes[-1].corte == _mes(INICIO, -30 + 23)


def test_un_corte_con_ventana_corta_no_entra():
    # el primer corte posible es el 13: antes de él hay 12 variaciones. Un hueco en el mes 3 de la
    # serie quita dos variaciones (la del 3 y la del 4): el corte 13 ya no tiene 12 -> empieza en 15
    historia = _plana(30)
    del historia[PPI][_mes(INICIO, -30 + 3)]

    c = _comprobar(historia)

    assert c.cortes[0].corte == _mes(INICIO, -30 + 15)
    assert c.n_cortes == 10


def test_sin_cortes_posibles_el_error_dice_cuantos_meses_hay_y_cuantos_hacen_falta():
    # 15 meses: hacen falta 12 + 1 antes de un corte y 6 después = 19
    with pytest.raises(ValueError, match=r"solo hay 15 meses.*hacen falta al menos 19"):
        _comprobar(_plana(15))


def test_sin_datos_de_una_serie_el_error_dice_cero_meses():
    historia = _plana(30)
    del historia[GASOIL]

    with pytest.raises(ValueError, match=r"solo hay 0 meses"):
        _comprobar(historia)


def test_la_mezcla_y_la_moneda_siguen_las_mismas_reglas_que_la_proyeccion():
    # presupuesto en Bs con mezcla propia y un insumo sin serie: con crecimiento constante la
    # proyección y lo real salen de la misma regla, así que coinciden exactos
    presupuesto, composiciones = _obra({CARPETA: D(1000), RIEGO: D(100)}, moneda="Bs")
    mapa = MapaSeries({"CA-30": PPI, ASFALTO: PPI})

    c = comprobar_hacia_atras(
        presupuesto,
        composiciones,
        PARAMETROS,
        _exponencial(22),
        mapa,
        _p(meses=6),
        recetas={MEZCLA: RECETA},
        costo_planta_por_t={MEZCLA: D(12)},
        precio_de_componente=COMPONENTES,
    )

    assert c.n_cortes == 4
    assert c.cobertura == D(1)
    for r in c.cortes:
        assert r.p50 == r.real
        assert r.real > presupuesto.total


def test_los_percentiles_pedidos_no_cambian_lo_que_se_reporta():
    # ResultadoCorte siempre trae P50 y P80, aunque p pida otros percentiles
    c = _comprobar(_exponencial(22), _p(meses=6, percentiles=(80, 90)))

    assert isinstance(c.cortes[0], ResultadoCorte)
    assert c.cortes[0].p50 == c.cortes[0].p80
