"""Reglas de cantidades por especialidad (spec §7): una por módulo, `derivar_<especialidad>`.

Cada constante vive en una tabla de su módulo con su fuente; una constante sin fuente verificada
lleva la etiqueta `SUPUESTO_DECLARADO` y se muestra como tal en la descripción de cada ítem (RS-5).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

#: Fuente de toda constante cuya fuente normativa no está verificada (spec §7, RS-5).
SUPUESTO_DECLARADO = "supuesto declarado"


@dataclass(frozen=True, slots=True)
class Constante:
    """Una constante de cálculo con su fuente. Nunca un número suelto en el código."""

    id: str
    nombre: str
    valor: Decimal | str
    fuente: str

    def __post_init__(self) -> None:
        if not self.fuente.strip():
            raise ValueError(f"la constante {self.id} exige fuente o «{SUPUESTO_DECLARADO}»")

    @property
    def supuesto_declarado(self) -> bool:
        return self.fuente == SUPUESTO_DECLARADO


def porcentaje(valor: Decimal) -> str:
    """`Decimal('0.10')` -> `'10 %'`, sin ceros sobrantes."""
    return f"{format((valor * 100).normalize(), 'f')} %"
