"""Tarifas de cada modelo, en un archivo de configuracion con fecha (S4 §8.4), no en el codigo."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from asistente.proveedores.base import Tarifa

RUTA_PRECIOS = Path(__file__).with_name("precios_ia.json")


def cargar_tarifas(ruta: Path = RUTA_PRECIOS) -> dict[str, Tarifa]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))["usd_por_millon_de_fichas"]
    return {
        modelo: Tarifa(**{campo: Decimal(valor) for campo, valor in precios.items()})
        for modelo, precios in datos.items()
    }


def fecha_de_los_precios(ruta: Path = RUTA_PRECIOS) -> str:
    return json.loads(ruta.read_text(encoding="utf-8"))["fecha_verificacion"]


def tarifa_de(modelo: str, *, local: bool = False) -> Tarifa:
    """La tarifa del modelo; el modo local cuesta cero. Un modelo sin tarifa es un error."""
    return cargar_tarifas()["local" if local else modelo]
