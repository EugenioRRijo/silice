"""`scripts/descargar_modelo.py` pide el modelo que usa la normalizacion (I2), y solo ese."""

from __future__ import annotations

from ml.normalization import MODELO_POR_DEFECTO
from scripts.descargar_modelo import descargar


def test_descarga_el_modelo_de_la_normalizacion() -> None:
    pedidos: list[str] = []
    descargar(cargar=pedidos.append)
    assert pedidos == [MODELO_POR_DEFECTO]
