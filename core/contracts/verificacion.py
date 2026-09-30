"""Contrato de las reglas de verificación y de sus hallazgos (NORMAS.md §7)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import IntEnum
from typing import ClassVar

from core.contracts.presupuesto import Presupuesto


class Severidad(IntEnum):
    INFO = 1
    ADVERTENCIA = 2
    ERROR = 3
    CRITICO = 4


@dataclass(frozen=True, slots=True)
class Hallazgo:
    """Resultado de una regla. `impacto` cuantifica el efecto (monto o cantidad) cuando aplica."""

    regla: str
    severidad: Severidad
    descripcion: str
    impacto: Decimal | None = None
    origen_ids: tuple[str, ...] = ()
    valor_observado: Decimal | None = None
    valor_esperado: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.regla.strip():
            raise ValueError("regla no puede estar vacía")
        if not self.descripcion.strip():
            raise ValueError("descripcion no puede estar vacía")
        object.__setattr__(self, "origen_ids", tuple(self.origen_ids))


class ReglaVerificacion(ABC):
    """Una comprobación de consistencia. Se ejecuta siempre; nunca modifica el presupuesto."""

    codigo: ClassVar[str]
    nombre: ClassVar[str]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "evaluar" in cls.__dict__:
            faltan = [atributo for atributo in ("codigo", "nombre") if not hasattr(cls, atributo)]
            if faltan:
                raise TypeError(f"{cls.__name__} debe declarar {', '.join(faltan)}")

    @abstractmethod
    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        """Devuelve los hallazgos encontrados; lista vacía si el presupuesto cumple la regla."""
