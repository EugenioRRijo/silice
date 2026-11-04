"""El CSV de un cómputo con la regla de Eugenio (pulido F5, tanda 2, Tarea 5).

Esbozo del rojo: todavía no convierte nada.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

__all__ = ["a_la_forma_de_siempre"]


def a_la_forma_de_siempre(ruta: Path, numericas: Collection[str], carpeta: Path) -> Path:
    del numericas, carpeta
    return ruta
