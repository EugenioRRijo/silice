# tests/unit/test_equilibrio_extraido.py
"""SL-E5: extraer `equilibrio` de `punto_equilibrio` no mueve ningún resultado (spec S2 §5.2).

`punto_equilibrio(presupuesto, parametros)` llama ahora a `equilibrio(venta, costo_variable,
costo_fijo, curva)` con los mismos argumentos que antes calculaba en su cuerpo; TI-001 sigue en
28 586,76 USD en el Día 6 (regresión literal, sin editar).
"""

from __future__ import annotations

from decimal import Decimal

from core.budget import punto_equilibrio
from core.budget.equilibrio import EstadoEquilibrio, equilibrio
from tests.fixtures import caso_ti001

D = Decimal
MONTOS = D("0.01")


def test_la_extraccion_de_equilibrio_no_mueve_el_pe_de_ti_001():
    """TI-001 sigue en 28 586,76 USD en el Día 6 (regresión literal); `equilibrio` da lo mismo."""
    resultado = caso_ti001.elaborar_caso()
    presupuesto = resultado.presupuesto
    esperado = punto_equilibrio(presupuesto, caso_ti001.PARAMETROS)
    assert abs(esperado.punto - D("28586.76")) <= MONTOS
    assert esperado.periodo.startswith("Dia 6")
    costo_variable = sum(
        (p.item.cantidad * p.resultado.costo_directo for p in presupuesto.partidas), D(0)
    )
    directo = equilibrio(
        presupuesto.total,
        costo_variable,
        costo_variable * caso_ti001.PARAMETROS.administracion,
        presupuesto.curva,
    )
    assert directo == esperado


def test_equilibrio_da_los_estados_tipados_de_sf_e3():
    curva = ()
    assert equilibrio(D(0), D(0), D(0), curva).estado is EstadoEquilibrio.NO_APLICABLE
    assert equilibrio(D(100), D(100), D(10), curva).estado is EstadoEquilibrio.NO_EXISTE
    assert equilibrio(D(100), D(50), D(100), curva).estado is EstadoEquilibrio.NO_SE_ALCANZA
    sin_curva = equilibrio(D(100), D(50), D(25), curva)
    assert sin_curva.estado is EstadoEquilibrio.CALCULADO and sin_curva.periodo is None
    assert sin_curva.punto == D(50)  # CF x V / (V - CV) = 25 x 100 / 50
