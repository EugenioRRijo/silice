"""Contrato de los adaptadores de dominio (NORMAS.md §5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo


class AdaptadorDominio(ABC):
    """Lee la fuente propia de un dominio y devuelve cantidades de obra trazables.

    Un adaptador concreto:
    - declara `dominio`;
    - implementa `extraer`, devolviendo ItemComputo con `origen_id` real;
    - importa de `core` únicamente `core.contracts` (lo vigila tests/unit/test_arquitectura.py).
    """

    dominio: ClassVar[Dominio]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "extraer" in cls.__dict__ and not hasattr(cls, "dominio"):
            raise TypeError(f"{cls.__name__} implementa extraer() pero no declara 'dominio'")

    @abstractmethod
    def extraer(self, fuente: Path | str) -> list[ItemComputo]:
        """Devuelve la lista de cantidades de obra derivadas de `fuente`."""
