"""Corridas escritas a mano para las pruebas de las metricas (memoria de calculo en
`tests/unit/test_experimento_metricas.py`)."""

from __future__ import annotations

from asistente.experimento.comparador import Error, Veredicto
from asistente.experimento.metricas import Corrida

HIPOTESIS = {
    "E1": None,
    "E2": ["R3"],
    "E3": ["R9"],
    "E4": ["R9"],
    "E5": ["R10"],
    "E6": None,
    "E7": ["R10"],
    "E8": ["R9"],
}
E3_Q1 = Error("E3", "punto", "esp_puntos:q1", "esp_puntos:P1", "x")
E6 = Error("E6", "punto", None, "esp_puntos:P2")
E4_R1 = Error("E4", "punto", "esp_puntos:r1", "esp_puntos:P1", "fuera")
E3_R2 = Error("E3", "punto", "esp_puntos:r2", "esp_puntos:P2", "x")


def corrida(tarea, rep, errores, detectados, inesperados, falsas, **kw):
    return Corrida(
        tarea,
        "M",
        "A",
        rep,
        tuple(errores),
        Veredicto(
            tuple(detectados), tuple(e for e in errores if e not in detectados), inesperados, falsas
        ),
        **kw,
    )


CORRIDAS = [
    corrida(
        "T1",
        1,
        [E3_Q1, E6],
        [E3_Q1],
        2,
        1,
        llamadas_de_propuesta=4,
        validas_al_primer_intento=3,
        rechazos={"sin_cita_ni_supuesto": 1},
        elementos_de_referencia=4,
        elementos_presentes=3,
    ),
    corrida(
        "T1",
        2,
        [E3_Q1],
        [],
        0,
        0,
        llamadas_de_propuesta=2,
        validas_al_primer_intento=2,
        elementos_de_referencia=4,
        elementos_presentes=4,
    ),
    corrida(
        "T2",
        1,
        [E4_R1, E3_R2],
        [E4_R1, E3_R2],
        3,
        0,
        llamadas_de_propuesta=4,
        validas_al_primer_intento=4,
        rechazos={"sin_cita_ni_supuesto": 2},
        elementos_de_referencia=4,
        elementos_presentes=4,
    ),
]
