"""El sembrador determinista de mutaciones E1-E8 (S4 §9.5, PRU-H9; plan 0.9.0, tarea 19).

Cada tipo da exactamente `n` mutantes (repartidos entre las tareas donde aplica), la misma
semilla da los mismos mutantes, y el comparador clasifica cada mutante como su tipo.
"""

from __future__ import annotations

from datetime import date

import pytest

from aplicacion import hoja
from aplicacion.hoja import Borrador
from asistente.experimento.banco import cargar_banco, referencia_de
from asistente.experimento.comparador import comparar
from asistente.experimento.metricas import TIPOS
from asistente.experimento.mutaciones import generar, mutar
from tests.fixtures.asistente_banco import codigos_y_unidades

SEMILLA = 20261011
N = 24
REFERENCIAS = {
    f.id: referencia_de(f) for f in cargar_banco().values() if f.conjunto == "evaluacion"
}
CATALOGO = codigos_y_unidades()
# Mutantes DISTINTOS por tipo (ruling del plan 0.9.0, T18 ronda 1: el auditor es determinista, un
# mutante repetido no es un ensayo independiente, asi que `generar` devuelve el n EFECTIVO).
# Cuenta a mano de E8 sobre el banco de evaluacion: hay tres sembrados (ev-agua-04: P1.x = 3,00;
# ev-datos-03: A1.ancho = 0; ev-elec-03: E2.y = 6,0). El de ev-datos-03 da un ambiente de ancho 0,
# que no se puede construir (se salta). Cada sembrado copia UN valor fijo: un solo mutante distinto
# por tarea. 2 mutantes distintos en total, no 24. E1-E7 tienen espacio de sobra: 24.
ESPERADOS = {**{t: N for t in TIPOS}, "E8": 2}


@pytest.mark.parametrize("tipo", TIPOS)
def test_cada_tipo_da_n_mutantes_deterministas_y_el_comparador_los_clasifica(tipo):
    mutantes = generar(tipo, REFERENCIAS, SEMILLA, N, CATALOGO)
    assert len(mutantes) == ESPERADOS[tipo]
    assert mutantes == generar(tipo, REFERENCIAS, SEMILLA, N, CATALOGO)  # mismas entradas
    for m in mutantes:
        comparacion = comparar(REFERENCIAS[m.tarea], m.espacio, m.items)
        encontrados = {e.tipo for e in comparacion.errores}
        assert tipo in encontrados, (m.tarea, m.indice, comparacion.errores)
        # el mutante se elabora y audita igual que una corrida (nunca revienta)
        borrador = Borrador(fecha=date(2026, 10, 31), espacio=m.espacio, items_base=m.items)
        assert hoja.elaborar_borrador(borrador).elaboracion.informe is not None


def test_otra_semilla_da_otros_mutantes_y_una_tarea_sin_aplicacion_se_salta():
    a = generar("E3", REFERENCIAS, SEMILLA, N)
    b = generar("E3", REFERENCIAS, SEMILLA + 1, N)
    assert a != b
    sin_partidas = REFERENCIAS["ev-agua-01"]
    assert mutar("E1", "ev-agua-01", sin_partidas, SEMILLA, 0, CATALOGO) is None
    assert mutar("E8", "ev-agua-01", sin_partidas, SEMILLA, 0) is None


def test_e8_solo_se_siembra_donde_la_ficha_lo_declara_y_se_salta_lo_que_no_se_puede_construir():
    mutantes = generar("E8", REFERENCIAS, SEMILLA, N)
    # ev-datos-03 siembra ancho = 0, que ni siquiera es un ambiente valido: se salta
    assert {m.tarea for m in mutantes} == {"ev-agua-04", "ev-elec-03"}
    assert len(mutantes) == ESPERADOS["E8"] == 2  # uno por sembrado construible (ver arriba)


def test_la_medicion_controlada_no_detecta_jamas_un_elemento_omitido_porque_no_hay_fila_que_citar():
    from asistente.experimento.ejecucion import medir_mutantes
    from tests.fixtures import caso_of001, caso_ti001

    composiciones = {**caso_of001.COMPOSICIONES, **caso_ti001.COMPOSICIONES}
    omitidos = generar("E6", REFERENCIAS, SEMILLA, 6)
    resultados = medir_mutantes(omitidos, REFERENCIAS, composiciones=composiciones)
    assert resultados == [("E6", False)] * 6
