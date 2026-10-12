# tests/unit/test_alertas.py
"""SL-E5: alertas AL-1 a AL-6 con umbrales declarados (spec S2 §4.5; RF-77).

Las cinco alertas de OB-S2 (iguales con y sin el reajuste reconocido) y cada frontera de §7.3:
SPI y CPI en 1,0000 / 0,9999 / 0,9000 / 0,8999, retraso de 2 días (10 %) y de 3, `|ΔP|` de 5 %
exacto y de 4,99 %, y el punto de equilibrio que sube 10,00 y 10,01 puntos. Un indicador no
disponible no se evalúa y la pantalla lo dice.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from core.budget.control import construir_estado
from core.budget.equilibrio import EstadoEquilibrio, PuntoEquilibrio
from core.budget.valor_ganado import (
    ParametrosControl,
    alertas,
    indicadores,
    reproyectar,
    separar_desvio,
)
from core.contracts.verificacion import Severidad
from tests.fixtures import control_ob_s2 as ob

D = Decimal
PARAMETROS = ParametrosControl()


def _insumos(costo_real=ob.COSTO_REAL):
    estado = construir_estado(
        ob.instantanea(ob.v01_v02()), costo_real=costo_real, precios=ob.precios_del_corte()
    )
    ind = indicadores(estado)
    return estado, ind, separar_desvio(estado, ind), reproyectar(estado)


def _pe(porcentaje: str, estado=EstadoEquilibrio.CALCULADO) -> PuntoEquilibrio:
    return PuntoEquilibrio(
        estado, D(5060), D(4000), D(600), D(460), D("0.2095"), D(100), D(porcentaje),
        "Semana 4", D("0.5"), "se alcanza",
    )  # fmt: skip


def _alertas(*, ind=None, sep=None, rep=None, base="56.60", proyectado="56.60", **parametros):
    estado, i, s, r = _insumos()
    return alertas(
        ind or i,
        sep or s,
        rep or r,
        dias_plan=20,
        equilibrio_base=_pe(base),
        equilibrio_proyectado=None if proyectado is None else _pe(proyectado),
        parametros=replace(PARAMETROS, **parametros),
    )


def _por_codigo(resultado):
    return {a.codigo: a for a in resultado.alertas}


def test_las_alertas_de_ob_s2_sin_el_equilibrio_proyectado_alcanzable():
    estado, ind, sep, rep = _insumos()
    resultado = alertas(
        ind, sep, rep, dias_plan=20, equilibrio_base=_pe("56.60"),
        equilibrio_proyectado=_pe("119.00", EstadoEquilibrio.NO_SE_ALCANZA), parametros=PARAMETROS,
    )  # fmt: skip
    por_codigo = _por_codigo(resultado)
    assert {c: a.severidad for c, a in por_codigo.items()} == {
        "AL-1": Severidad.ERROR,
        "AL-2": Severidad.ADVERTENCIA,
        "AL-3": Severidad.ERROR,
        "AL-4": Severidad.ERROR,
        "AL-5": Severidad.INFO,
    }
    assert por_codigo["AL-1"].valor_observado == D("0.8") and por_codigo["AL-1"].umbral == D("0.9")
    assert por_codigo["AL-3"].valor_observado == 3 and por_codigo["AL-3"].umbral == D(2)
    assert "LCP art. 133, a cotejar" in por_codigo["AL-5"].descripcion
    assert all(a.naturaleza_umbral == "SUPUESTO_DECLARADO" for a in resultado.alertas)
    assert resultado.no_evaluadas == {}


@pytest.mark.parametrize(
    ("spi", "severidad"),
    [
        ("1.0000", None),
        ("1.2000", None),
        ("0.9999", Severidad.ADVERTENCIA),
        ("0.9000", Severidad.ADVERTENCIA),
        ("0.8999", Severidad.ERROR),
    ],
)
def test_fronteras_del_spi_y_del_cpi(spi, severidad):
    _, ind, _, _ = _insumos()
    en_spi = _por_codigo(_alertas(ind=replace(ind, spi=D(spi), cpi=D(1)))).get("AL-1")
    en_cpi = _por_codigo(_alertas(ind=replace(ind, cpi=D(spi), spi=D(1)))).get("AL-2")
    assert (None if en_spi is None else en_spi.severidad) == severidad
    assert (None if en_cpi is None else en_cpi.severidad) == severidad


@pytest.mark.parametrize(
    ("termino", "severidad"),
    [(20, None), (19, None), (22, Severidad.ADVERTENCIA), (23, Severidad.ERROR)],
    ids=["en plazo", "antes", "2 dias = 10 % advierte", "3 dias = 15 % es error"],
)
def test_fronteras_del_retraso_del_termino(termino, severidad):
    _, _, _, rep = _insumos()
    alerta = _por_codigo(_alertas(rep=replace(rep, termino=termino))).get("AL-3")
    assert (None if alerta is None else alerta.severidad) == severidad


@pytest.mark.parametrize(
    ("precio", "salta"),
    [(D("-60.00"), True), (D("-59.88"), False), (D("60.00"), True), (D("-59.99"), False)],
    ids=["5 % exacto", "4,99 %", "5 % favorable", "casi 5 %"],
)
def test_fronteras_de_la_desviacion_de_precio(precio, salta):
    _, _, sep, _ = _insumos()
    alerta = _por_codigo(_alertas(sep=replace(sep, precio=precio, consumo=D(0)))).get("AL-5")
    assert (alerta is not None) is salta
    assert alerta is None or alerta.severidad is Severidad.INFO


@pytest.mark.parametrize(
    ("proyectado", "severidad"),
    [("66.60", None), ("66.61", Severidad.ADVERTENCIA), ("50.00", None)],
    ids=["sube 10,00 puntos: sin alerta", "sube 10,01: advierte", "baja: sin alerta"],
)
def test_fronteras_del_equilibrio_proyectado(proyectado, severidad):
    alerta = _por_codigo(_alertas(proyectado=proyectado)).get("AL-4")
    assert (None if alerta is None else alerta.severidad) == severidad


def test_un_equilibrio_que_no_existe_o_no_se_alcanza_es_error():
    for estado in (EstadoEquilibrio.NO_EXISTE, EstadoEquilibrio.NO_SE_ALCANZA):
        _, ind, sep, rep = _insumos()
        resultado = alertas(
            ind, sep, rep, dias_plan=20, equilibrio_base=_pe("56.60"),
            equilibrio_proyectado=_pe("200", estado), parametros=PARAMETROS,
        )  # fmt: skip
        assert _por_codigo(resultado)["AL-4"].severidad is Severidad.ERROR


def test_una_partida_detenida_da_su_advertencia_al_6():
    solo_b = ob.valuacion({**ob.V02, "lineas": ob.V02["lineas"][1:]}, 2)
    estado = construir_estado(
        ob.instantanea([solo_b]), costo_real=ob.COSTO_REAL, precios=ob.precios_del_corte()
    )
    ind = indicadores(estado)
    resultado = alertas(
        ind, separar_desvio(estado, ind), reproyectar(estado), dias_plan=20,
        equilibrio_base=_pe("56.60"), equilibrio_proyectado=_pe("56.60"), parametros=PARAMETROS,
    )  # fmt: skip
    detenida = [a for a in resultado.alertas if a.codigo == "AL-6"]
    assert len(detenida) == 1 and detenida[0].severidad is Severidad.ADVERTENCIA
    assert "OB-A" in detenida[0].descripcion


def test_lo_que_no_esta_disponible_no_se_evalua_y_se_declara():
    estado = construir_estado(
        ob.instantanea(ob.v01_v02()), costo_real=None, precios=ob.precios_del_corte()
    )
    ind = replace(indicadores(estado), spi=None)
    estado_sin_precios = construir_estado(ob.instantanea(ob.v01_v02()), costo_real=D(1280))
    sep = separar_desvio(estado_sin_precios)
    resultado = alertas(
        ind, sep, reproyectar(estado), dias_plan=20, equilibrio_base=None,
        equilibrio_proyectado=None, parametros=PARAMETROS,
    )  # fmt: skip
    assert set(resultado.no_evaluadas) == {"AL-1", "AL-2", "AL-4", "AL-5"}
    assert "AL-3" not in resultado.no_evaluadas  # el termino por plan si se calcula
    assert resultado.no_evaluadas["AL-1"] == "SPI no aplica"


def test_un_termino_no_proyectable_no_evalua_al_3():
    _, _, _, rep = _insumos()
    resultado = _alertas(rep=replace(rep, termino=None, motivo_termino="no proyectable: OB-A"))
    assert resultado.no_evaluadas == {"AL-3": "no proyectable: OB-A"}


def test_los_umbrales_son_editables_por_proyecto():
    _, ind, _, _ = _insumos()
    resultado = _alertas(ind=replace(ind, spi=D("0.85"), cpi=D(1)), spi_error=D("0.80"))
    assert _por_codigo(resultado)["AL-1"].severidad is Severidad.ADVERTENCIA


def test_los_parametros_de_control_validan_sus_rangos():
    with pytest.raises(ValueError, match="eta_cuadrilla"):
        ParametrosControl(eta_cuadrilla=D(0))
    with pytest.raises(ValueError, match="eta_horas_extra"):
        ParametrosControl(eta_horas_extra=D("1.1"))
    with pytest.raises(ValueError, match="cuadrillas_max"):
        ParametrosControl(cuadrillas_max=1)
    with pytest.raises(ValueError, match="penalizacion_diaria"):
        ParametrosControl(penalizacion_diaria=D(-1))
