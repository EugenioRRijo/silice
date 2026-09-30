"""Sesion I6.1: deteccion de anomalias con Isolation Forest (RF-27 y RF-29, parte I6.1).

`ml.anomaly` recibe datos planos -- series de `Decimal` con su identificador -- igual que
`ml.normalization` recibe pares (codigo, descripcion): `ml/` no conoce la base de datos
(NORMAS.md §2, `test_arquitectura.py`). La capa de composicion (I6.2 para rendimientos, I6.3
para el contraste de precios) le pasara lo que consulte `core.catalog`.

Dos usos, los del PLAN (Sesion I6.1):

1. `precios_atipicos`: marca las variaciones de precio que se apartan del historico acumulado
   (RF-29: «marcara como atipicos los precios que se aparten del historico»).
2. `evaluar_rendimiento`: dice si un rendimiento introducido se aparta del comportamiento
   observado de su partida (RF-27); impedir o no el registro es del llamador («sin impedir el
   registro», I6.2).

Sin datos etiquetados: se entrena sobre el historico acumulado, con semilla fija (los resultados
del detector son reproducibles, requisito para que estas pruebas y el capitulo de resultados de la
tesis citen cifras estables).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("sklearn")

#: Treinta variaciones de precio pequenas y realistas (entre -6 % y +8 %), mas una de 300 %.
VARIACIONES_NORMALES = {
    f"cambio-{i:02d}": Decimal(valor)
    for i, valor in enumerate(
        [
            "0.02",
            "0.05",
            "-0.01",
            "0.03",
            "0.04",
            "-0.02",
            "0.06",
            "0.01",
            "0.03",
            "-0.03",
            "0.05",
            "0.02",
            "-0.01",
            "0.04",
            "0.07",
            "0.00",
            "0.02",
            "-0.04",
            "0.03",
            "0.05",
            "0.01",
            "-0.02",
            "0.06",
            "0.02",
            "0.04",
            "-0.01",
            "0.08",
            "0.03",
            "-0.06",
            "0.02",
        ]
    )
}
VARIACION_EXTREMA = {"cambio-99": Decimal("3.00")}

#: Historico de rendimientos de una misma partida: ocho observaciones alrededor de 8 m3/dia.
RENDIMIENTOS_OBSERVADOS = [
    Decimal(valor) for valor in ["7.5", "8.0", "8.2", "7.8", "8.5", "7.9", "8.1", "8.3"]
]


def test_la_variacion_extrema_es_atipica_y_tiene_el_peor_puntaje():
    """RF-29 (parte I6.1): la variacion de 300 % sobre un historico de variaciones de un digito
    queda marcada como atipica, con el puntaje mas bajo de toda la serie (mas negativo = mas
    anomalo, convencion de `score_samples` que el modulo conserva).
    """
    from ml.anomaly import precios_atipicos

    atipicos = precios_atipicos({**VARIACIONES_NORMALES, **VARIACION_EXTREMA})

    ids = {atipico.id for atipico in atipicos}
    assert "cambio-99" in ids
    assert len(atipicos) <= 4  # marca poco: anomalias, no una fraccion fija del historico
    peor = min(atipicos, key=lambda atipico: atipico.puntaje)
    assert peor.id == "cambio-99"
    assert peor.valor == Decimal("3.00")  # el valor original viaja intacto, sin pasar por float


def test_los_atipicos_salen_ordenados_del_mas_anomalo_al_menos():
    from ml.anomaly import precios_atipicos

    atipicos = precios_atipicos({**VARIACIONES_NORMALES, **VARIACION_EXTREMA})
    puntajes = [atipico.puntaje for atipico in atipicos]
    assert puntajes == sorted(puntajes)


def test_deterministico_con_la_misma_semilla():
    """Dos corridas identicas dan exactamente lo mismo: el detector fija la semilla del bosque."""
    from ml.anomaly import precios_atipicos

    serie = {**VARIACIONES_NORMALES, **VARIACION_EXTREMA}
    assert precios_atipicos(serie) == precios_atipicos(serie)


def test_rendimiento_coherente_con_lo_observado_no_es_atipico():
    from ml.anomaly import evaluar_rendimiento

    veredicto = evaluar_rendimiento(RENDIMIENTOS_OBSERVADOS, Decimal("8.0"))

    assert veredicto is not None
    assert veredicto.atipico is False


def test_rendimiento_desviado_es_atipico_pero_el_veredicto_no_prohibe():
    """RF-27 (parte I6.1): 30 m3/dia contra un historico de ~8 se aparta del comportamiento
    observado. El veredicto solo informa (atipico + puntaje): impedir o permitir el registro es
    decision del flujo de I6.2 («sin impedir el registro»).
    """
    from ml.anomaly import evaluar_rendimiento

    veredicto = evaluar_rendimiento(RENDIMIENTOS_OBSERVADOS, Decimal("30"))

    assert veredicto is not None
    assert veredicto.atipico is True
    assert veredicto.puntaje < 0  # convencion de decision_function: negativo = fuera del bosque


def test_rendimiento_muy_bajo_tambien_es_atipico():
    from ml.anomaly import evaluar_rendimiento

    veredicto = evaluar_rendimiento(RENDIMIENTOS_OBSERVADOS, Decimal("1.5"))

    assert veredicto is not None and veredicto.atipico is True


def test_historico_insuficiente_no_da_veredicto():
    """Con menos de `MINIMO_OBSERVACIONES` no hay comportamiento observado que sustente un
    veredicto: se devuelve `None` (el llamador registra sin advertencia), nunca un juicio
    estadistico sobre tres numeros.
    """
    from ml.anomaly import MINIMO_OBSERVACIONES, evaluar_rendimiento

    corto = RENDIMIENTOS_OBSERVADOS[: MINIMO_OBSERVACIONES - 1]
    assert evaluar_rendimiento(corto, Decimal("30")) is None


def test_precios_atipicos_con_historico_insuficiente_no_marca_nada():
    from ml.anomaly import MINIMO_OBSERVACIONES, precios_atipicos

    pocos = dict(list(VARIACIONES_NORMALES.items())[: MINIMO_OBSERVACIONES - 1])
    assert precios_atipicos(pocos) == []
