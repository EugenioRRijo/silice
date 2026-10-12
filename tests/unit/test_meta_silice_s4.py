"""Parte S4 de la meta unica de Silice (spec S4 §11; plan 0.9.0, tarea 1)."""

from __future__ import annotations

from scripts.meta_alpha import Estado
from scripts.meta_silice import FASES, partes, validar_partes
from scripts.meta_silice_s4 import (
    PARES_S4,
    PARTE,
    REQUISITOS_S4,
    evaluar_arquitectura,
    evaluar_banco,
    evaluar_congelado,
    evaluar_nucleo,
    evaluar_resultados,
    evaluar_rnf08,
)

HUELLA = "ab" * 32


def test_la_parte_s4_se_descubre_y_usa_las_fases_de_la_0_9_0():
    assert FASES["0.9.0"] == ("S4-0", "S4-1", "S4-2", "S4-3", "S4-4")
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert PARTE.requisitos == {"S4-0": REQUISITOS_S4}
    assert {par.fase for par in PARES_S4} == set(FASES["0.9.0"])
    assert [(c.codigo, c.fase) for c in PARTE.comprobaciones] == [
        ("S4-RNF08", "S4-0"),
        ("S4-BANCO", "S4-0"),
        ("S4-ARQ", "S4-1"),
        ("S4-NUCLEO", "S4-1"),
        ("S4-CONGELADO", "S4-4"),
        ("S4-RESULTADOS", "S4-4"),
    ]


def test_los_numeros_de_s4_son_los_del_spec():
    assert REQUISITOS_S4 == (
        "UC-09",
        "RF-32",
        "RF-90",
        "RF-91",
        "RF-92",
        "RF-93",
        "RF-94",
        "RF-95",
        "RNF-18",
    )


def test_rnf08_exige_la_excepcion_del_asistente_en_modo_nube():
    sin = "| Ejecucion local | RNF-08 | sin servicios externos |\n| Otra | RNF-09 | x |\n"
    con = (
        "| Ejecucion local | RNF-08 | sin servicios externos, salvo el asistente en modo nube "
        "activado por el administrador |\n| Otra | RNF-09 | x |\n"
    )
    assert evaluar_rnf08(None)[0] is Estado.PENDIENTE
    assert evaluar_rnf08("nada")[0] is Estado.FALLA
    assert evaluar_rnf08(sin)[0] is Estado.FALLA
    assert evaluar_rnf08(con)[0] is Estado.OK


def test_el_banco_exige_16_fichas_3_sembrados_y_la_huella_en_el_protocolo():
    bueno = {"desarrollo": 4, "evaluacion": 12}
    assert evaluar_banco({"desarrollo": 4, "evaluacion": 11}, 3, HUELLA, "x")[0] is Estado.FALLA
    assert evaluar_banco(bueno, 2, HUELLA, "x")[0] is Estado.FALLA
    assert evaluar_banco(bueno, 3, HUELLA, None)[0] is Estado.PENDIENTE
    assert evaluar_banco(bueno, 3, HUELLA, "huella: otra")[0] is Estado.FALLA
    assert evaluar_banco(bueno, 3, HUELLA, f"huella: {HUELLA}")[0] is Estado.OK


def test_arquitectura_nucleo_congelado_y_resultados():
    texto = 'PAQUETES_FUERA_DEL_NUCLEO = ("adapters", "ml", "asistente", "ui")'
    assert evaluar_arquitectura(False, texto)[0] is Estado.FALLA
    assert (
        evaluar_arquitectura(True, 'PAQUETES_FUERA_DEL_NUCLEO = ("adapters",)')[0] is Estado.FALLA
    )
    assert evaluar_arquitectura(True, texto)[0] is Estado.OK
    assert evaluar_nucleo(None)[0] is Estado.PENDIENTE
    assert evaluar_nucleo(["abc1234"])[0] is Estado.FALLA
    assert evaluar_nucleo([])[0] is Estado.OK
    sin_congelar = ["el protocolo aun no esta congelado (falta congelado.json)"]
    assert evaluar_congelado(sin_congelar)[0] is Estado.PENDIENTE
    assert evaluar_congelado(["auditor cambio desde el congelado"])[0] is Estado.FALLA
    assert evaluar_congelado([])[0] is Estado.OK
    assert evaluar_resultados(None, "x")[0] is Estado.PENDIENTE
    assert evaluar_resultados("x", None)[0] is Estado.PENDIENTE
    assert evaluar_resultados("a mano", "generado")[0] is Estado.FALLA
    assert evaluar_resultados("igual", "igual")[0] is Estado.OK
