"""La API lee los decimales de maquina con la misma funcion que la capa de aplicacion (tarea 2.1
del plan de desenredo): un solo mensaje y una sola regla para `12,50`, `NaN` o `Infinity`."""

from __future__ import annotations

import api.esquemas
import aplicacion.composicion


def test_la_api_usa_la_lectura_de_aplicacion():
    assert api.esquemas.decimal_desde_texto is aplicacion.composicion.decimal_desde_texto
