"""Origen de la medida (spec §6.3): de dónde sale cada dato, con su referencia obligatoria.

El origen de medida es de la fila. La fuente del cambio es del `RegistroCambio` del núcleo y no se
modela aquí.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class TipoOrigen(StrEnum):
    PLANO = "plano"
    DXF = "dxf"
    IFC = "ifc"
    LEVANTAMIENTO = "levantamiento"
    SUPUESTO = "supuesto"


#: Datos que cada tipo de origen debe traer, no vacíos (spec §6.3, RF-44).
REFERENCIA_OBLIGATORIA: dict[TipoOrigen, tuple[str, ...]] = {
    TipoOrigen.PLANO: ("plano", "lamina", "revision"),
    TipoOrigen.DXF: ("archivo", "capa", "handle"),
    TipoOrigen.IFC: ("archivo", "global_id"),
    TipoOrigen.LEVANTAMIENTO: ("fecha", "responsable"),
    TipoOrigen.SUPUESTO: ("motivo",),
}


def pares(valor: Mapping[str, str] | tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    """Normaliza un mapa a una tupla de pares ordenada por clave (hashable e inmutable)."""
    items = valor.items() if isinstance(valor, Mapping) else valor
    return tuple(sorted((str(k), str(v)) for k, v in items))


@dataclass(frozen=True, slots=True)
class OrigenMedida:
    id: str
    tipo: TipoOrigen
    referencia: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("el id del origen no puede estar vacío")
        object.__setattr__(self, "tipo", TipoOrigen(self.tipo))
        object.__setattr__(self, "referencia", pares(self.referencia))
        dada = dict(self.referencia)
        for clave in REFERENCIA_OBLIGATORIA[self.tipo]:
            if not dada.get(clave, "").strip():
                raise ValueError(
                    f"el origen {self.id!r} de tipo {self.tipo.value} exige «{clave}» "
                    "en su referencia"
                )

    @property
    def es_supuesto(self) -> bool:
        return self.tipo is TipoOrigen.SUPUESTO
