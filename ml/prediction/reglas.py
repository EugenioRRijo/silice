"""Prediccion de precio unitario por sistema de reglas (UC-07, Sesion I6.3, compuerta G2).

La compuerta G2 (CLAUDE.md §8.1) elige la tecnica por el conteo de registros de APU del dominio;
`tecnica_para` es esa tabla hecha codigo. Con los conteos del proyecto (civil = 5, el resto
0) corresponde el **sistema de reglas con analisis de sensibilidad, declarado como limitacion**:
no hay datos para entrenar nada, y este modulo no lo disimula.

La regla es deliberadamente simple y esta declarada: el PU estimado de una partida es su PU base
multiplicado por (1 + la media de las variaciones del historico de cambios de precio); el analisis
de sensibilidad recorre la variacion minima y la maxima observadas, dando un rango [pu_minimo,
pu_maximo] por partida. La regla NO conoce la composicion del APU (eso seria recalcular con el
motor de `core.costing`, que es la verdad de terreno contra la que se mide): su error frente al
motor es justamente lo que reportan las metricas de RF-28 (MAPE, RMSE, R2, todas en `Decimal`,
con la raiz cuadrada del propio `Decimal`).

El contraste de RF-29 compara el precio construido con el estimado y produce un `Hallazgo` de
severidad ADVERTENCIA (contrato `core.contracts.verificacion`) cuando la desviacion sale del rango
declarado de la clase 3 de AACE International (-20 % / +30 %, el marco que fija CLAUDE.md §8.1).

Como todo `ml/` (CLAUDE.md §2): datos planos, sin base de datos, y de `core` solo los contratos.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from core.contracts.verificacion import Hallazgo, Severidad

__all__ = [
    "RANGO_AACE_CLASE_3",
    "UMBRAL_CASOS",
    "UMBRAL_XGBOOST",
    "Metricas",
    "PrediccionPrecio",
    "Tecnica",
    "contrastar_aace",
    "metricas",
    "predecir_por_reglas",
    "tecnica_para",
]

#: Umbrales de la tabla de degradacion de CLAUDE.md §8.1 (registros de APU por dominio).
UMBRAL_CASOS = 50
UMBRAL_XGBOOST = 200

#: Rango de exactitud esperada de una estimacion clase 3 de AACE International
#: (Recommended Practice 18R-97: -10/-20 % por debajo, +10/+30 % por encima; se adopta el
#: extremo amplio de la banda como rango declarado del contraste). Limites inclusivos.
RANGO_AACE_CLASE_3 = (Decimal("-0.20"), Decimal("0.30"))

_CIEN = Decimal(100)


class Tecnica(StrEnum):
    """La tecnica de prediccion que dicta la compuerta G2 segun los datos disponibles."""

    REGLAS = "reglas"
    CASOS = "casos"
    XGBOOST = "xgboost"


def tecnica_para(registros: int) -> Tecnica:
    """La tabla de CLAUDE.md §8.1: < 50 reglas; 50-200 casos; > 200 XGBoost."""
    if registros < UMBRAL_CASOS:
        return Tecnica.REGLAS
    if registros <= UMBRAL_XGBOOST:
        return Tecnica.CASOS
    return Tecnica.XGBOOST


@dataclass(frozen=True, slots=True)
class PrediccionPrecio:
    """El PU estimado de una partida y su rango de sensibilidad, todo `Decimal` exacto."""

    codigo_partida: str
    pu_base: Decimal
    pu_estimado: Decimal
    pu_minimo: Decimal
    pu_maximo: Decimal


@dataclass(frozen=True, slots=True)
class Metricas:
    """Las tres metricas obligatorias de RF-28. `r2` es `None` si los reales no varian."""

    mape: Decimal
    rmse: Decimal
    r2: Decimal | None


def predecir_por_reglas(
    pus_base: Mapping[str, Decimal], variaciones: Sequence[Decimal]
) -> list[PrediccionPrecio]:
    """Una prediccion por partida, en orden de codigo, con su rango de sensibilidad.

    :param pus_base: PU conocido por partida (el punto de partida de la regla).
    :param variaciones: historico de variaciones de precio como fracciones (la forma de
        `CambioPrecio.variacion`); vacio, la prediccion es el propio PU base.
    """
    if variaciones:
        indice = sum(variaciones) / len(variaciones)
        variacion_minima = min(variaciones)
        variacion_maxima = max(variaciones)
    else:
        indice = variacion_minima = variacion_maxima = Decimal(0)

    return [
        PrediccionPrecio(
            codigo_partida=codigo,
            pu_base=pu_base,
            pu_estimado=pu_base * (1 + indice),
            pu_minimo=pu_base * (1 + variacion_minima),
            pu_maximo=pu_base * (1 + variacion_maxima),
        )
        for codigo, pu_base in sorted(pus_base.items())
    ]


def metricas(estimados: Mapping[str, Decimal], reales: Mapping[str, Decimal]) -> Metricas:
    """MAPE, RMSE y R2 de los estimados contra los reales, por partida.

    Los tres calculos son aritmetica de `Decimal` (la raiz de RMSE es `Decimal.sqrt()`, con la
    precision del contexto). `ValueError` si los dos mapas no traen las mismas partidas.
    """
    if set(estimados) != set(reales):
        raise ValueError(
            "estimados y reales deben traer las mismas partidas: "
            f"{sorted(set(estimados) ^ set(reales))}"
        )
    if not reales:
        raise ValueError("no hay partidas que evaluar")

    codigos = sorted(reales)
    errores = [estimados[codigo] - reales[codigo] for codigo in codigos]
    cantidad = len(codigos)

    mape = sum(abs(error) / reales[codigo] for codigo, error in zip(codigos, errores, strict=True))
    mape /= cantidad
    rmse = (sum(error * error for error in errores) / cantidad).sqrt()

    media_reales = sum(reales.values()) / cantidad
    ss_tot = sum((reales[codigo] - media_reales) ** 2 for codigo in codigos)
    ss_res = sum(error * error for error in errores)
    r2 = None if ss_tot == 0 else 1 - ss_res / ss_tot

    return Metricas(mape=mape, rmse=rmse, r2=r2)


def contrastar_aace(
    codigo_partida: str, pu_construido: Decimal, pu_estimado: Decimal
) -> Hallazgo | None:
    """RF-29: `Hallazgo` ADVERTENCIA si el construido se aparta del estimado fuera de la clase 3.

    La desviacion es (construido - estimado) / estimado, expresada en porcentaje en la
    descripcion. Dentro del rango declarado (limites inclusivos) no hay hallazgo.
    """
    if pu_estimado <= 0:
        raise ValueError(f"el PU estimado debe ser mayor que cero: {pu_estimado}")

    desviacion = (pu_construido - pu_estimado) / pu_estimado
    inferior, superior = RANGO_AACE_CLASE_3
    if inferior <= desviacion <= superior:
        return None

    # La descripcion presenta a dos decimales (CLAUDE.md §2.3: se redondea solo al presentar);
    # `valor_observado` y `valor_esperado` conservan los Decimal exactos.
    return Hallazgo(
        regla="CONTRASTE-AACE3",
        severidad=Severidad.ADVERTENCIA,
        descripcion=(
            f"el precio construido de {codigo_partida} ({_a_dos_decimales(pu_construido):f}) "
            f"se desvia {_a_dos_decimales(desviacion * _CIEN):+f} % del estimado "
            f"({_a_dos_decimales(pu_estimado):f}), fuera del rango de la clase 3 de AACE "
            f"({inferior * _CIEN:+.0f} % / {superior * _CIEN:+.0f} %)"
        ),
        impacto=abs(pu_construido - pu_estimado),
        origen_ids=(codigo_partida,),
        valor_observado=pu_construido,
        valor_esperado=pu_estimado,
    )


def _a_dos_decimales(valor: Decimal) -> Decimal:
    """Cuantiza para presentar con ROUND_HALF_UP, la convencion de los informes del proyecto.

    Replica `core.verification.texto.formatear_decimal(valor, 2)`: `ml/` solo puede importar
    `core.contracts` (`tests/unit/test_arquitectura.py`) y la convencion de presentacion no vive
    ahi. El formato `:.2f` de `Decimal` no sirve: redondea al par (2.125 -> 2.12).
    """
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
