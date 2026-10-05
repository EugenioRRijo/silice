"""SF-E3 (RF-58, RS-4, spec 9.4): el punto de equilibrio de cualquier presupuesto.

Oraculos independientes del codigo:

- el literal de la bitacora del caso TI-001 (`docs/bitacora/2026-09-30-caso-ti001.md`: 28 586,76 USD
  = 56,60 % del contrato, durante el Dia 6), no el script que lo calculaba;
- un caso de dos partidas resuelto a mano (ver `_dos_partidas`);
- los cuatro casos limite de la spec: V = 0, margen <= 0, PE > V y sin curva.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.budget.equilibrio import EstadoEquilibrio, PuntoEquilibrio, punto_equilibrio
from core.contracts.apu import ComposicionAPU, ParametrosCosto, ResultadoAPU
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto, PuntoCurva
from tests.fixtures import caso_ti001 as caso

D = Decimal


def _partida(codigo: str, cantidad: str, costo_directo: str, pu: str) -> PartidaPresupuestada:
    return PartidaPresupuestada(
        item=ItemComputo(
            codigo_partida=codigo,
            descripcion=codigo,
            unidad="m",
            cantidad=D(cantidad),
            origen_id=f"{codigo}-1",
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
        ),
        apu=ComposicionAPU(codigo_partida=codigo, descripcion=codigo, unidad="m", rendimiento=D(1)),
        resultado=ResultadoAPU(
            materiales=D(0),
            equipos=D(0),
            mano_obra=D(0),
            costo_directo=D(costo_directo),
            con_administracion=D(pu),
            precio_unitario=D(pu),
        ),
    )


def _presupuesto(partidas, curva=()) -> Presupuesto:
    return Presupuesto(
        codigo="EQ", fecha=date(2026, 10, 5), moneda="USD", partidas=tuple(partidas), curva=curva
    )


def _dos_partidas(con_curva: bool = True) -> Presupuesto:
    """A: 10 x (costo directo 50, PU 65) = 650; B: 4 x (100, 130) = 520.

    V = 1170; CV = 500 + 400 = 900; CF = 900 x 0,15 = 135; m = 270 / 1170;
    PE = CF / m = 135 x 1170 / 270 = 585 = 50 % de V. La curva reparte A en el periodo 1 y B en el
    2 (650 y 1170 acumulados): el PE cae en el periodo 1, a 585 / 650 = 0,9 de su monto."""
    curva = (
        (PuntoCurva("Dia 1 [A]", D(650), D(650)), PuntoCurva("Dia 2 [B]", D(520), D(1170)))
        if con_curva
        else ()
    )
    return _presupuesto([_partida("A", "10", "50", "65"), _partida("B", "4", "100", "130")], curva)


PARAMETROS = ParametrosCosto()  # administracion 0,15


def test_dos_partidas_resueltas_a_mano():
    r = punto_equilibrio(_dos_partidas(), PARAMETROS)

    assert r.estado is EstadoEquilibrio.CALCULADO
    assert (r.venta, r.costo_variable, r.costo_fijo) == (D(1170), D(900), D(135))
    assert r.utilidad == D(1170) - D(900) - D(135)
    assert r.margen == D(270) / D(1170)
    assert r.punto == D(585)
    assert r.porcentaje == D(50)
    assert r.periodo == "Dia 1 [A]"
    assert r.fraccion_periodo == D("0.9")


def test_el_pe_cubre_el_costo_fijo_con_el_margen():
    r = punto_equilibrio(_dos_partidas(), PARAMETROS)

    assert abs(r.punto * r.margen - r.costo_fijo) < D("1e-20")


def test_la_administracion_sale_de_los_parametros_de_la_version():
    r = punto_equilibrio(_dos_partidas(), replace(PARAMETROS, administracion=D("0.10")))

    assert r.costo_fijo == D(90)
    assert r.punto == D(90) * D(1170) / D(270)


def test_el_periodo_es_el_primero_cuyo_acumulado_alcanza_el_pe():
    # PE = 585: el acumulado del periodo 1 (650) lo alcanza; con PE exactamente igual al acumulado
    # tambien es ese periodo (>=), y fraccion 1.
    presupuesto = _dos_partidas()
    curva = (PuntoCurva("Dia 1 [A]", D(585), D(585)), PuntoCurva("Dia 2 [B]", D(585), D(1170)))

    r = punto_equilibrio(replace(presupuesto, curva=curva), PARAMETROS)

    assert r.periodo == "Dia 1 [A]"
    assert r.fraccion_periodo == D(1)


def test_el_pe_en_el_segundo_periodo_descuenta_lo_acumulado():
    curva = (PuntoCurva("Dia 1", D(300), D(300)), PuntoCurva("Dia 2", D(870), D(1170)))

    r = punto_equilibrio(replace(_dos_partidas(), curva=curva), PARAMETROS)

    assert r.periodo == "Dia 2"
    assert r.fraccion_periodo == (D(585) - D(300)) / D(870)


def test_un_periodo_de_monto_cero_da_fraccion_cero():
    curva = (PuntoCurva("Dia 1", D(0), D(585)), PuntoCurva("Dia 2", D(585), D(1170)))

    r = punto_equilibrio(replace(_dos_partidas(), curva=curva), PARAMETROS)

    assert (r.periodo, r.fraccion_periodo) == ("Dia 1", D(0))


def test_sin_curva_hay_pe_sin_ubicacion():
    r = punto_equilibrio(_dos_partidas(con_curva=False), PARAMETROS)

    assert r.estado is EstadoEquilibrio.CALCULADO
    assert r.punto == D(585)
    assert (r.periodo, r.fraccion_periodo) == (None, None)
    assert "curva" in r.mensaje


def test_ventas_cero_no_es_aplicable():
    r = punto_equilibrio(_presupuesto([]), PARAMETROS)

    assert r.estado is EstadoEquilibrio.NO_APLICABLE
    assert (r.venta, r.margen, r.punto, r.porcentaje, r.periodo) == (D(0), None, None, None, None)
    assert r.mensaje


@pytest.mark.parametrize("pu", ["100", "90"])
def test_margen_cero_o_negativo_no_tiene_punto_de_equilibrio(pu):
    r = punto_equilibrio(_presupuesto([_partida("A", "1", "100", pu)]), PARAMETROS)

    assert r.estado is EstadoEquilibrio.NO_EXISTE
    assert r.punto is None and r.periodo is None and r.fraccion_periodo is None
    assert r.margen <= 0
    assert "no existe punto de equilibrio" in r.mensaje


def test_pe_mayor_que_las_ventas_no_se_alcanza_dentro_del_contrato():
    # CD 100, PU 110: V = 110, CV = 100, CF = 15 > V - CV = 10: PE = 15 x 110 / 10 = 165 > V.
    curva = (PuntoCurva("Dia 1 [A]", D(110), D(110)),)
    r = punto_equilibrio(_presupuesto([_partida("A", "1", "100", "110")], curva), PARAMETROS)

    assert r.estado is EstadoEquilibrio.NO_SE_ALCANZA
    assert r.punto == D(165)
    assert r.periodo is None and r.fraccion_periodo is None
    assert "no se alcanza dentro del contrato" in r.mensaje


def test_pe_igual_a_las_ventas_si_se_alcanza_en_el_ultimo_periodo():
    # CF = V - CV: CD 100, PU 115 => CF = 15 = 115 - 100 => PE = 115 = V.
    curva = (PuntoCurva("Dia 1 [A]", D(115), D(115)),)
    r = punto_equilibrio(_presupuesto([_partida("A", "1", "100", "115")], curva), PARAMETROS)

    assert r.estado is EstadoEquilibrio.CALCULADO
    assert r.punto == D(115)
    assert r.periodo == "Dia 1 [A]"


def test_todo_es_decimal():
    r = punto_equilibrio(_dos_partidas(), PARAMETROS)

    for valor in (r.venta, r.costo_variable, r.costo_fijo, r.utilidad, r.margen, r.punto):
        assert isinstance(valor, Decimal)
    assert isinstance(r, PuntoEquilibrio)


# ---------------------------------------------------------------------------------------------
# Oraculo literal de TI-001
# ---------------------------------------------------------------------------------------------


def test_ti001_da_los_literales_de_la_bitacora_del_caso():
    """28 586,76 USD = 56,60 % del contrato, durante el Dia 6 (bitacora de TI-001, tabla de
    resultados), contra la elaboracion del caso y no contra el script."""
    resultado = caso.elaborar_caso()

    r = punto_equilibrio(resultado.presupuesto, caso.PARAMETROS)

    assert r.estado is EstadoEquilibrio.CALCULADO
    assert abs(r.punto - D("28586.76")) <= D("0.01")
    assert abs(r.porcentaje - D("56.60")) <= D("0.01")
    assert r.periodo.startswith("Dia 6")
