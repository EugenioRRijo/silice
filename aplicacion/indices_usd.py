"""Un índice del BCV expresado en USD (RF-214): esqueleto para ver el rojo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class SerieInexistente(LookupError):  # noqa: N818
    pass


class HuellaCambiada(ValueError):  # noqa: N818
    pass


@dataclass(frozen=True, slots=True)
class MesEnUsd:
    mes: date
    indice_bs: Decimal
    tasa_promedio: Decimal
    dias: int
    valor: Decimal
    provisional: bool


@dataclass(frozen=True, slots=True)
class MesOmitido:
    mes: date
    motivo: str


def expresar_en_usd(indices, tasas):
    raise NotImplementedError


def origenes(sesion):
    raise NotImplementedError


def ver(sesion, codigo, *, lado="venta"):
    raise NotImplementedError


def guardar(sesion, codigo, *, huella, responsable, ahora, lado="venta"):
    raise NotImplementedError
