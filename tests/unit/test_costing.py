"""Pruebas del motor de costos (Sesión I0.2). Fallan con ImportError hasta que exista core.costing.

Estado esperado hasta la Sesión I0.3: siete fallos por `ImportError`. Es deliberado
(CLAUDE.md §2, principio 5): la línea base verificada existe antes que el motor, y el motor se
escribe para pasarla. Estas pruebas NO se modifican para ponerlas en verde; se implementa
`core.costing.calcular_apu`.

Contrato esperado del motor:
    calcular_apu(composicion: ComposicionAPU, parametros: ParametrosCosto) -> ResultadoAPU
"""

from decimal import Decimal

import pytest

from tests.fixtures import apu_linea_base as lb

TOLERANCIA = Decimal("0.01")

pytestmark = pytest.mark.rojo_esperado


def _motor():
    """Import diferido a propósito: así el resto de la suite corre aunque el motor no exista."""
    from core.costing import calcular_apu

    return calcular_apu


def _codigo(apu):
    return apu.codigo_partida


@pytest.mark.parametrize("apu", lb.APUS_LINEA_BASE, ids=_codigo)
def test_precio_unitario_reproduce_la_linea_base(apu, parametros_linea_base):
    """Los cinco APU de la línea base, con tolerancia de 0,01 sobre el precio unitario."""
    resultado = _motor()(apu, parametros_linea_base)
    esperado = lb.PRECIO_UNITARIO_ESPERADO[apu.codigo_partida]
    assert abs(resultado.precio_unitario - esperado) <= TOLERANCIA, (
        f"{apu.codigo_partida}: precio_unitario={resultado.precio_unitario} esperado={esperado}"
    )
    costo_directo_esperado = lb.SUBTOTALES_ESPERADOS[apu.codigo_partida]["costo_directo"]
    assert abs(resultado.costo_directo - costo_directo_esperado) <= TOLERANCIA


def test_los_materiales_no_se_dividen_entre_el_rendimiento(parametros_linea_base):
    """Error probable n.º 1. En tubería, materiales = 7,19 aunque el rendimiento sea 100."""
    resultado = _motor()(lb.APU_TUBERIA, parametros_linea_base)
    assert resultado.materiales == lb.SUBTOTALES_ESPERADOS["LB-02-TUB"]["materiales"]
    equipos_esperado = (
        lb.SUBTOTALES_ESPERADOS["LB-02-TUB"]["equipos_total"] / lb.APU_TUBERIA.rendimiento
    )
    assert resultado.equipos == equipos_esperado


def test_administracion_y_utilidad_se_aplican_en_cascada(parametros_linea_base):
    """Error probable n.º 2. costo_directo × 1,15 × 1,10 (= × 1,265), no × (1 + 0,15 + 0,10)."""
    parametros = parametros_linea_base
    resultado = _motor()(lb.APU_EXCAVACION, parametros)
    en_cascada = (
        resultado.costo_directo * (1 + parametros.administracion) * (1 + parametros.utilidad)
    )
    sumados = resultado.costo_directo * (1 + parametros.administracion + parametros.utilidad)
    assert abs(resultado.precio_unitario - en_cascada) <= TOLERANCIA
    assert abs(resultado.precio_unitario - sumados) > TOLERANCIA
    assert resultado.con_administracion == resultado.costo_directo * (1 + parametros.administracion)
