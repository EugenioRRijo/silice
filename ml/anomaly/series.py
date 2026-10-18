"""RF-100: la serie fechada de precios de un insumo, en USD, reducida a variaciones (spec S3 §3.2).

El detector (`ml.anomaly.precios_atipicos`, I6.1) no se toca: este módulo solo arma lo que le
llega. Sobre los precios de un insumo en el tiempo (las listas de la empresa de S1, RF-67, y las
MaPreX, cada precio con su fecha):

1. cada precio se lleva a **USD con la tasa de ese precio** (RF-65): un precio en Bs entre la
   tasa de su fecha; uno en USD queda igual; **uno en Bs sin tasa no se inventa**: se omite y se
   dice cuál;
2. la serie se ordena por fecha (y, a igual fecha, por el nombre de la lista) y se reduce a
   variaciones entre puntos consecutivos, `(p2 - p1) / p1` como fracción (0,05 = subió 5 %);
3. `precios_atipicos` juzga las variaciones. Con menos de `MINIMO_OBSERVACIONES` (8) variaciones
   se abstiene: la serie corta no es sospechosa, es insuficiente (`se_abstuvo`).

Sin acceso a la base (`ml/` no la conoce): recibe puntos planos. `ui/atipicos.py` los arma.
Los umbrales y la semilla son los del detector (SUPUESTO_DECLARADO, RS3-6); no se ajustan aquí.

Aritmética: las divisiones (el precio entre la tasa y la variación) usan el mismo contexto decimal
que `core.catalog.moneda` (`prec=28`, `ROUND_HALF_EVEN`), declarado aquí porque `ml/` solo puede
importar `core.contracts` y no reutiliza ese módulo.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from ml.anomaly.detector import MINIMO_OBSERVACIONES, PrecioAtipico, precios_atipicos

__all__ = [
    "PuntoDePrecio",
    "ResultadoDeSerie",
    "SerieEnUsd",
    "a_usd",
    "analizar",
    "variaciones",
]


def _contexto():
    """El contexto decimal de `core.catalog.moneda._contexto` (misma precisión y redondeo)."""
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class PuntoDePrecio:
    """Un precio de un insumo en una fecha. `tasa` es Bs por USD de la fecha del precio."""

    fecha: date
    monto: Decimal
    moneda: str  # "USD" o "Bs"
    tasa: Decimal | None = None
    origen: str = ""  # la lista de donde sale, para citarlo


@dataclass(frozen=True, slots=True)
class SerieEnUsd:
    puntos: tuple[tuple[date, Decimal, str], ...]  # (fecha, USD, origen), por fecha
    sin_tasa: tuple[str, ...]  # los orígenes de los precios en Bs a los que les faltó la tasa


@dataclass(frozen=True, slots=True)
class ResultadoDeSerie:
    serie: SerieEnUsd
    variaciones: dict[str, Decimal]
    atipicas: tuple[PrecioAtipico, ...]
    se_abstuvo: bool  # menos de `MINIMO_OBSERVACIONES` variaciones


def a_usd(puntos: Sequence[PuntoDePrecio]) -> SerieEnUsd:
    """Cada precio en USD con la tasa de su fecha; ordenada por fecha (y origen, a igual fecha)."""
    llevados: list[tuple[date, Decimal, str]] = []
    sin_tasa: list[str] = []
    with _contexto():
        for p in puntos:
            if p.moneda == "USD":
                llevados.append((p.fecha, p.monto, p.origen))
            elif p.tasa is not None and p.tasa > 0:
                llevados.append((p.fecha, p.monto / p.tasa, p.origen))
            else:
                sin_tasa.append(p.origen or p.fecha.isoformat())
    llevados.sort(key=lambda t: (t[0], t[2]))
    return SerieEnUsd(tuple(llevados), tuple(sin_tasa))


def variaciones(serie: SerieEnUsd) -> dict[str, Decimal]:
    """`{«AAAA-MM-DD>AAAA-MM-DD#k»: variación}` entre puntos consecutivos con anterior > 0."""
    salida: dict[str, Decimal] = {}
    pares = zip(serie.puntos, serie.puntos[1:], strict=False)
    with _contexto():
        for k, ((f1, p1, _), (f2, p2, _)) in enumerate(pares):
            if p1 > 0:
                salida[f"{f1.isoformat()}>{f2.isoformat()}#{k}"] = (p2 - p1) / p1
    return salida


def analizar(puntos: Sequence[PuntoDePrecio]) -> ResultadoDeSerie:
    """La serie del insumo en USD, sus variaciones y las que el detector marca como atípicas."""
    serie = a_usd(puntos)
    cambios = variaciones(serie)
    return ResultadoDeSerie(
        serie=serie,
        variaciones=cambios,
        atipicas=tuple(precios_atipicos(cambios)),
        se_abstuvo=len(cambios) < MINIMO_OBSERVACIONES,
    )
