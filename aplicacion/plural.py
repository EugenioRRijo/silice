"""El plural de un mensaje: la cantidad con punto de miles y la palabra que le toca."""

from __future__ import annotations

from decimal import Decimal

from aplicacion.cifras import texto_de_cifra


def plural(n: int, singular: str, en_plural: str) -> str:
    """`n` con punto de miles y la palabra que le toca («1 obra atrasada», «1.200 días»)."""
    return f"{texto_de_cifra(Decimal(n))} {singular if n == 1 else en_plural}"
