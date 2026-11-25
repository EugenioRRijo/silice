"""Reparto determinista de la suite en trozos, para correrla en varias máquinas a la vez.

`SILICE_TROZO=k/N` deja en la corrida solo el trozo `k` de `N` (`tests/conftest.py`). Cada prueba
cae en un solo trozo según la huella SHA-256 de su identificador, la misma en cualquier proceso y
en cualquier máquina (`hash()` de Python cambia de un proceso a otro). Regla de Eugenio del
2026-11-24: pruebas en paralelo y repartidas.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

__all__ = ["VARIABLE_TROZO", "Trozo", "leer_trozo"]

VARIABLE_TROZO = "SILICE_TROZO"
_K_DE_N = re.compile(r"(\d+)/(\d+)")


@dataclass(frozen=True, slots=True)
class Trozo:
    """El trozo `numero` de `total` (de 1 a `total`). No existe un trozo ilegal."""

    numero: int
    total: int

    def __post_init__(self) -> None:
        if self.total < 1 or not 1 <= self.numero <= self.total:
            raise ValueError(f"trozo {self.numero}/{self.total}: debe ser k/N con 1 <= k <= N")

    def incluye(self, nodeid: str) -> bool:
        huella = hashlib.sha256(nodeid.encode("utf-8")).digest()
        return int.from_bytes(huella[:8], "big") % self.total == self.numero - 1


def leer_trozo(texto: str | None) -> Trozo | None:
    """El valor de `SILICE_TROZO`: vacío no reparte; otra cosa que no sea `k/N` es un error."""
    if not texto:
        return None
    k_de_n = _K_DE_N.fullmatch(texto.strip())
    if k_de_n is None:
        raise ValueError(f"{VARIABLE_TROZO}={texto!r} no tiene la forma k/N (por ejemplo, 2/4)")
    try:
        return Trozo(int(k_de_n[1]), int(k_de_n[2]))
    except ValueError as error:
        raise ValueError(f"{VARIABLE_TROZO}={texto!r}: {error}") from None
