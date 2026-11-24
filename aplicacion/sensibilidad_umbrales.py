"""Análisis de sensibilidad de los umbrales viales marcados como supuesto declarado.

Sustituye temporalmente el valor de una `Constante` de `adapters/vial/constantes.py` (y en los
módulos que ya la importaron por nombre) sin modificar el código de las reglas, mide cuántos
hallazgos VR cambian frente al factor 1 y restaura el valor al salir. No calibra nada: mide.
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from types import ModuleType

from adapters.vial import constantes as constantes_viales
from adapters.vial import derivacion as derivacion_vial
from adapters.vial import reglas as reglas_viales
from adapters.vial.constantes import SUPUESTO_DECLARADO, Constante
from core.contracts.verificacion import Hallazgo, Severidad

__all__ = [
    "FACTORES_POR_OMISION",
    "Fila",
    "barrido",
    "con_umbral",
    "umbrales_supuestos",
]

FACTORES_POR_OMISION: tuple[Decimal, ...] = (
    Decimal("0.5"),
    Decimal("0.75"),
    Decimal("1.25"),
    Decimal("1.5"),
)

_MODULOS_BASE: tuple[ModuleType, ...] = (
    constantes_viales,
    reglas_viales,
    derivacion_vial,
)
_MODULO_CONCILIACION = "aplicacion.conciliacion"

_ClaveVR = tuple[str, Severidad, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class Fila:
    """Resultado del barrido para un umbral y un factor frente al factor 1."""

    umbral: str
    factor: Decimal
    base: int
    ahora: int
    cambian: int


def _es_supuesto_numerico(objeto: object) -> bool:
    return (
        isinstance(objeto, Constante)
        and isinstance(objeto.valor, Decimal)
        and SUPUESTO_DECLARADO in objeto.fuente
    )


def umbrales_supuestos() -> tuple[str, ...]:
    """Los nombres de todas las `Constante` numéricas marcadas `SUPUESTO_DECLARADO` en
    `adapters/vial/constantes.py`, en su orden de definición."""
    return tuple(
        nombre
        for nombre, objeto in vars(constantes_viales).items()
        if _es_supuesto_numerico(objeto)
    )


def _obtener_supuesto(nombre: str) -> Constante:
    objeto = getattr(constantes_viales, nombre, None)
    if not isinstance(objeto, Constante):
        raise ValueError(f"«{nombre}» no es una constante vial de adapters/vial/constantes.py.")
    if not isinstance(objeto.valor, Decimal) or SUPUESTO_DECLARADO not in objeto.fuente:
        raise ValueError(
            f"«{nombre}» no está marcada como {SUPUESTO_DECLARADO!r}: solo se barren supuestos "
            "declarados numéricos."
        )
    return objeto


def _a_decimal(factor: Decimal | float | int | str) -> Decimal:
    if isinstance(factor, bool):
        raise ValueError("El factor debe ser un número positivo, no un booleano.")
    try:
        valor = factor if isinstance(factor, Decimal) else Decimal(str(factor))
    except InvalidOperation as exc:
        raise ValueError(f"El factor {factor!r} no es un número válido.") from exc
    if not valor.is_finite() or valor <= 0:
        raise ValueError(f"El factor debe ser un número finito mayor que cero: {factor!r}.")
    return valor


def _modulos_objetivo() -> list[ModuleType]:
    modulos = list(_MODULOS_BASE)
    conciliacion = sys.modules.get(_MODULO_CONCILIACION)
    if isinstance(conciliacion, ModuleType):
        modulos.append(conciliacion)
    return modulos


@contextmanager
def con_umbral(nombre: str, factor: Decimal | float | int | str) -> Iterator[Constante]:
    """Sustituye temporalmente el valor de una `Constante` marcada `SUPUESTO_DECLARADO` por
    `valor * factor` en `constantes.py` y en los módulos que la importaron, y la restaura al
    salir (también ante excepciones)."""
    original = _obtener_supuesto(nombre)
    escala = _a_decimal(factor)
    assert isinstance(original.valor, Decimal)
    sustituida = replace(original, valor=original.valor * escala)
    modificados: list[tuple[ModuleType, Constante]] = []
    try:
        for modulo in _modulos_objetivo():
            if getattr(modulo, nombre, None) is original:
                setattr(modulo, nombre, sustituida)
                modificados.append((modulo, original))
        yield sustituida
    finally:
        for modulo, previo in reversed(modificados):
            setattr(modulo, nombre, previo)


def _conteo_vr(hallazgos: Sequence[Hallazgo]) -> Counter[_ClaveVR]:
    return Counter(
        (h.regla, h.severidad, tuple(h.origen_ids))
        for h in hallazgos
        if str(h.regla).startswith("VR")
    )


def barrido(
    auditar: Callable[[], Sequence[Hallazgo]],
    umbrales: Sequence[str] | None = None,
    factores: Sequence[Decimal | float | int | str] = FACTORES_POR_OMISION,
) -> list[Fila]:
    """Mide, por umbral y factor, cuántos hallazgos VR cambian frente al factor 1."""
    elegidos = list(umbrales_supuestos() if umbrales is None else umbrales)
    for nombre in elegidos:
        _obtener_supuesto(nombre)
    escalas = [_a_decimal(f) for f in factores]
    conteo_base = _conteo_vr(auditar())
    total_base = sum(conteo_base.values())
    filas: list[Fila] = []
    for nombre in elegidos:
        for escala in escalas:
            with con_umbral(nombre, escala):
                conteo_ahora = _conteo_vr(auditar())
            cambian = sum((conteo_base - conteo_ahora).values()) + sum(
                (conteo_ahora - conteo_base).values()
            )
            filas.append(
                Fila(
                    umbral=nombre,
                    factor=escala,
                    base=total_base,
                    ahora=sum(conteo_ahora.values()),
                    cambian=cambian,
                )
            )
    return filas
