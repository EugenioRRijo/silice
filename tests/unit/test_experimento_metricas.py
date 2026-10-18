"""Metricas, bootstrap agrupado y Wilson contra la memoria de calculo hecha a mano (S4 §9.5).

Memoria (`tests/fixtures/memorias/asistente_metricas.md`): modelo M, condicion A, 3 corridas.
  T1 rep 1: errores E3(q1) y E6; detecta E3; 2 hallazgos no esperados, 1 falsa alarma.
  T1 rep 2: error E3(q1); nada lo detecta; 0 hallazgos no esperados.
  T2 rep 1: errores E4(r1) y E3(r2); detecta los dos; 3 hallazgos no esperados, 0 falsas.
Detectables por hipotesis: E3, E4 (E6 no lo es). Detectables = 1 + 1 + 2 = 4; detectados = 3,
es decir 75 %.
Por tipo: E3 2/3, E4 1/1. Escapan: E3 = 1; no detectables por diseno: E6 = 1.
Falsas alarmas = 1 de 5 no esperados = 20 %. Por tarea: T1 (1, 2), T2 (2, 2).
Bootstrap (2 tareas): las razones posibles son 1/2 (T1,T1), 3/4 (T1,T2 o T2,T1) y 1 (T2,T2), con
probabilidades 1/4, 1/2, 1/4 -> percentil 2,5 = 0,5 y percentil 97,5 = 1,0 con cualquier semilla.
Wilson: 24/24 -> [24/(24+z^2), 1] = [0,86203, 1]; 0/24 -> [0, 1 - 0,86203];
12/24 -> [0,3143, 0,6857].
"""

from __future__ import annotations

import json

import pytest

from asistente.experimento.metricas import (
    bootstrap_agrupado,
    deteccion_controlada,
    percentil,
    resumir,
    wilson,
)
from tests.fixtures.asistente_corridas import CORRIDAS, HIPOTESIS


def test_el_resumen_da_las_cifras_de_la_memoria():
    r = resumir(CORRIDAS, HIPOTESIS, semilla=1, replicas=2_000)
    assert (r.errores_detectables, r.detectados, r.deteccion) == (4, 3, 0.75)
    assert dict(r.por_tipo) == {"E3": (2, 3), "E4": (1, 1)}
    assert dict(r.escapan_por_tipo) == {"E3": 1}
    assert dict(r.no_detectables_por_diseno) == {"E6": 1}
    assert (r.inesperados, r.falsas_alarmas, r.tasa_falsas_alarmas) == (5, 1, 0.2)
    assert r.propuestas_validas == pytest.approx(9 / 10)
    assert dict(r.rechazos_por_causa) == {"sin_cita_ni_supuesto": 3}
    assert r.exhaustividad == pytest.approx(11 / 12)
    assert dict(r.por_tarea) == {"T1": (1, 2), "T2": (2, 2)}


def test_el_bootstrap_agrupado_con_dos_tareas_da_el_intervalo_de_la_memoria_con_cualquier_semilla():
    for semilla in (1, 2, 20261011):
        assert bootstrap_agrupado({"T1": (1, 2), "T2": (2, 2)}, semilla) == (0.5, 1.0)


def test_el_bootstrap_es_reproducible_y_una_sola_tarea_es_degenerada():
    datos = {"A": (1, 3), "B": (3, 3), "C": (0, 2), "D": (2, 4)}
    assert bootstrap_agrupado(datos, 7, 500) == bootstrap_agrupado(datos, 7, 500)
    assert bootstrap_agrupado({"A": (1, 4)}, 7, 100) == (0.25, 0.25)
    assert bootstrap_agrupado({}, 7) == (0.0, 1.0)


def test_percentil_por_rango_mas_cercano():
    valores = [float(i) for i in range(1, 101)]
    obtenidos = (percentil(valores, 2.5), percentil(valores, 97.5), percentil(valores, 50))
    assert obtenidos == (3, 98, 50)


@pytest.mark.parametrize(
    ("k", "n", "bajo", "alto"),
    [
        (24, 24, 24 / (24 + 1.959963984540054**2), 1.0),
        (0, 24, 0.0, 1 - 0.86203),
        (12, 24, 0.3143, 0.6857),
    ],
)
def test_wilson_contra_los_valores_de_la_memoria(k, n, bajo, alto):
    b, a = wilson(k, n)
    assert b == pytest.approx(bajo, abs=1e-4) and a == pytest.approx(alto, abs=1e-4)


def test_wilson_sin_ensayos_y_deteccion_controlada_por_tipo():
    assert wilson(0, 0) == (0.0, 1.0)
    r = deteccion_controlada([("E3", True)] * 12 + [("E3", False)] * 12 + [("E4", True)] * 24)
    assert r["E3"][:2] == (12, 24) and r["E4"][:2] == (24, 24)
    assert r["E3"][2] == pytest.approx((0.3143, 0.6857), abs=1e-4)


def test_la_corrida_ida_y_vuelta_por_json_no_pierde_nada():
    from asistente.experimento.metricas import corrida_a_dict, corrida_de_dict

    for c in CORRIDAS:
        assert corrida_de_dict(json.loads(json.dumps(corrida_a_dict(c)))) == c
