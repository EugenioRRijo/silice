"""Deteccion de anomalias en precios y rendimientos con Isolation Forest (Sesion I6.1).

Dos usos, los del PLAN:

1. `precios_atipicos` marca, dentro del historico acumulado de variaciones de precio, las que se
   apartan del resto (RF-29, parte I6.1: «marcara como atipicos los precios que se aparten del
   historico»). La capa de composicion (I6.3) le pasa las variaciones de `CambioPrecio`.
2. `evaluar_rendimiento` dice si un rendimiento introducido se aparta del comportamiento observado
   de su partida (RF-27, parte I6.1). El veredicto solo informa: impedir o permitir el registro es
   del flujo de I6.2 («sin impedir el registro», docs/ERS.md).

Sin datos etiquetados ni entrenamiento supervisado: el bosque de aislamiento se ajusta sobre el
historico acumulado cada vez, con semilla fija (`SEMILLA`) para que el mismo historico produzca
siempre el mismo resultado -- las pruebas y el capitulo de resultados citan cifras estables.

Arquitectura (NORMAS.md §2, `test_arquitectura.py`): `ml/` no conoce la base de datos. Este modulo
recibe series planas -- un `Mapping[str, Decimal]` de variaciones o una secuencia de `Decimal` de
rendimientos observados -- y devuelve identificadores, valores y puntajes.

Numeros: los valores llegan como `Decimal` (regla de NORMAS.md §2.3) y **se devuelven intactos**;
la conversion a `float` ocurre solo dentro del bosque, que es aritmetica estadistica de
scikit-learn, no un calculo monetario. Los puntajes son `float` adimensionales, como el puntaje
de similitud de `ml.normalization`: mas negativo = mas anomalo (convencion de `decision_function`,
que este modulo conserva sin reinterpretar).

Con menos de `MINIMO_OBSERVACIONES` observaciones no hay comportamiento observado que sustente un
veredicto: `precios_atipicos` no marca nada y `evaluar_rendimiento` devuelve `None`, en vez de
emitir un juicio estadistico sobre un punado de numeros.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

#: Semilla del bosque: mismo historico, mismo veredicto (reproducibilidad de la tesis).
SEMILLA = 42

#: Observaciones minimas para emitir un veredicto. Por debajo, el detector se abstiene.
MINIMO_OBSERVACIONES = 8

#: Margen de decision declarado sobre `decision_function`: atipico si el puntaje queda por
#: debajo. El corte crudo de `predict()` (puntaje < 0 con umbral 'auto') marca tambien puntos
#: frontera en muestras pequenas -- observado en el RED de esta sesion: 6 de 31 variaciones
#: marcadas, con puntajes desde apenas -0.007 frente al -0.39 de la verdadera anomalia. El margen
#: exige separacion real, pero no puede ser grande: con historicos cortos (el minimo son 8
#: observaciones, el caso real de los rendimientos por partida) los arboles quedan poco profundos
#: y hasta un valor extremo satura cerca de -0.10 (un rendimiento de 30 sobre un historico de ~8
#: puntua -0.095). Constante declarada y ajustable, no una fraccion fija del historico.
UMBRAL_ATIPICO = -0.05

__all__ = [
    "MINIMO_OBSERVACIONES",
    "SEMILLA",
    "UMBRAL_ATIPICO",
    "PrecioAtipico",
    "VeredictoRendimiento",
    "evaluar_rendimiento",
    "precios_atipicos",
]


@dataclass(frozen=True)
class PrecioAtipico:
    """Una variacion de precio marcada como atipica: id de origen, valor exacto y puntaje."""

    id: str
    valor: Decimal
    puntaje: float


@dataclass(frozen=True)
class VeredictoRendimiento:
    """El juicio sobre un rendimiento introducido frente al comportamiento observado."""

    atipico: bool
    puntaje: float


def precios_atipicos(variaciones: Mapping[str, Decimal]) -> list[PrecioAtipico]:
    """Las variaciones que se apartan del historico, del puntaje mas anomalo al menos.

    :param variaciones: historico acumulado como {id del cambio: variacion}, con la variacion
        expresada como fraccion (0.05 = subio 5 %), la misma forma de `CambioPrecio.variacion`.
    :return: lista vacia si el historico no alcanza `MINIMO_OBSERVACIONES`.
    """
    if len(variaciones) < MINIMO_OBSERVACIONES:
        return []
    ids = list(variaciones)
    bosque = _bosque_ajustado([variaciones[id_] for id_ in ids])
    puntajes = bosque.decision_function(_columna([variaciones[id_] for id_ in ids]))
    atipicos = [
        PrecioAtipico(id=id_, valor=variaciones[id_], puntaje=float(puntaje))
        for id_, puntaje in zip(ids, puntajes, strict=True)
        if float(puntaje) < UMBRAL_ATIPICO
    ]
    return sorted(atipicos, key=lambda atipico: atipico.puntaje)


def evaluar_rendimiento(
    observados: Sequence[Decimal], valor: Decimal
) -> VeredictoRendimiento | None:
    """Si `valor` se aparta de los rendimientos `observados` de la partida (RF-27, parte I6.1).

    :param observados: rendimientos del historico de la misma partida, en unidades de partida
        por dia (la forma de `Rendimiento.valor`).
    :param valor: el rendimiento que el usuario introduce.
    :return: `None` si el historico no alcanza `MINIMO_OBSERVACIONES` (sin comportamiento
        observado no hay veredicto y el llamador registra sin advertencia).
    """
    if len(observados) < MINIMO_OBSERVACIONES:
        return None
    bosque = _bosque_ajustado(observados)
    puntaje = float(bosque.decision_function(_columna([valor]))[0])
    return VeredictoRendimiento(atipico=puntaje < UMBRAL_ATIPICO, puntaje=puntaje)


def _bosque_ajustado(valores: Sequence[Decimal]):
    """Un `IsolationForest` ajustado sobre la serie, con semilla fija. El criterio de atipico no
    es su `predict()` sino `decision_function` contra `UMBRAL_ATIPICO` (ver esa constante).
    """
    from sklearn.ensemble import IsolationForest

    bosque = IsolationForest(random_state=SEMILLA)
    bosque.fit(_columna(valores))
    return bosque


def _columna(valores: Sequence[Decimal]) -> np.ndarray:
    """La serie como columna `float` de numpy: la unica frontera Decimal -> float del modulo."""
    return np.array([float(valor) for valor in valores]).reshape(-1, 1)
