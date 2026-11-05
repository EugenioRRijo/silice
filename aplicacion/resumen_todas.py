"""La cartera de todas las carpetas, por moneda (rediseño F6, T7; contrato de rutas §4).

Corre `aplicacion.mesa.obras_de_la_mesa` en cada carpeta, abierta en **solo lectura**
(`motor_solo_lectura`: sin migrar ni crear `-wal`/`-shm`) y cerrada al terminar, como
`aplicacion.pendientes_todas`. Devuelve las obras con su carpeta y una fila por moneda presente:
cuántas obras, la suma de sus totales y cuántas están en ejecución (o atrasadas). **Nunca se suman
Bs con USD**: cada moneda es una fila aparte y no hay fila «total» ni conversión por tasa (la mesa
de una sola carpeta sí convierte; la cartera no, porque cada carpeta tendría su propia tasa).

Orden: la carpeta de la empresa (`None`) primero, las demás por nombre y, dentro de cada una, las
obras en el orden de la mesa (alfabético). Las monedas: Bs, USD y, si apareciera otra, después
por nombre. El total de cada obra se redondea a 0,01 (ROUND_HALF_UP) y la fila suma esos totales
redondeados, de modo que la suma de la tabla y la de la fila coinciden. Una obra sin total cuenta
como obra y no suma; una moneda sin ningún total suma 0,00.

Una carpeta sin archivo se salta sin contarla; una ilegible (no SQLite, sin las tablas de la mesa o
con datos que la mesa no puede leer) se omite, se cuenta en `carpetas_omitidas` y queda en el
registro; nunca tumba la cartera.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from aplicacion import mesa
from aplicacion.mesa import EN_CURSO, ObraEnMesa
from aplicacion.proyectos import leer_cada_carpeta
from core.catalog import Catalogo

__all__ = [
    "CarteraDeTodas",
    "MonedaDeLaCartera",
    "ObraDeLaCartera",
    "cartera_de_las_carpetas",
]

_registro = logging.getLogger(__name__)

_CENTESIMA = Decimal("0.01")
_ORDEN_DE_MONEDA = {"Bs": 0, "USD": 1}


@dataclass(frozen=True)
class ObraDeLaCartera:
    """Una obra de la mesa con su carpeta. `carpeta` es el nombre que acepta
    `POST /v1/casos/actual`; `None`, la carpeta de la empresa. `total`, a 0,01."""

    carpeta: str | None
    obra: ObraEnMesa
    total: Decimal | None


@dataclass(frozen=True)
class MonedaDeLaCartera:
    moneda: str
    obras: int
    total: Decimal
    en_ejecucion: int


@dataclass(frozen=True)
class CarteraDeTodas:
    por_moneda: tuple[MonedaDeLaCartera, ...]
    obras: tuple[ObraDeLaCartera, ...]
    carpetas_omitidas: int


def _a_centesimas(valor: Decimal | None) -> Decimal | None:
    return None if valor is None else valor.quantize(_CENTESIMA, rounding=ROUND_HALF_UP)


def _por_moneda(obras: list[ObraDeLaCartera]) -> tuple[MonedaDeLaCartera, ...]:
    monedas = sorted({o.obra.moneda for o in obras}, key=lambda m: (_ORDEN_DE_MONEDA.get(m, 2), m))
    filas = []
    for moneda in monedas:
        de_la_moneda = [o for o in obras if o.obra.moneda == moneda]
        filas.append(
            MonedaDeLaCartera(
                moneda=moneda,
                obras=len(de_la_moneda),
                total=sum((o.total for o in de_la_moneda if o.total is not None), Decimal("0.00")),
                en_ejecucion=sum(1 for o in de_la_moneda if o.obra.etapa in EN_CURSO),
            )
        )
    return tuple(filas)


def cartera_de_las_carpetas(carpetas: list[tuple[str | None, Path]], hoy: date) -> CarteraDeTodas:
    """Las obras de cada carpeta (`(nombre, ruta)`) y su resumen por moneda, en el orden descrito
    arriba."""
    leidas, omitidas = leer_cada_carpeta(
        carpetas,
        # Por el módulo, no por el nombre importado: así se puede reemplazar en pruebas.
        lambda sesion: mesa.obras_de_la_mesa(sesion, Catalogo(sesion), hoy),
        registro=_registro,
        que="las obras",
    )
    obras = [
        ObraDeLaCartera(carpeta=nombre, obra=o, total=_a_centesimas(o.total))
        for nombre, de_la_carpeta in leidas
        for o in de_la_carpeta
    ]
    return CarteraDeTodas(_por_moneda(obras), tuple(obras), omitidas)
