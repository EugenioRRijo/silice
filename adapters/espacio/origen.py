"""Origen de la medida (spec §6.3): de dónde sale cada dato, con su referencia obligatoria.

Una referencia incompleta NO se rechaza al construir (RF-44, UC-13a): el origen se acepta, se guarda
y se recarga con la marca `incompleto`, y quien lo marca ERROR es R8 («origen sin referencia»). Solo
un id vacío o un tipo que no existe son errores de construcción: sin ellos no hay origen que citar.

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
    IA = "ia"


#: Datos que cada tipo de origen debe traer, no vacíos (spec §6.3, RF-44).
REFERENCIA_OBLIGATORIA: dict[TipoOrigen, tuple[str, ...]] = {
    TipoOrigen.PLANO: ("plano", "lamina", "revision"),
    TipoOrigen.DXF: ("archivo", "capa", "handle"),
    TipoOrigen.IFC: ("archivo", "global_id"),
    TipoOrigen.LEVANTAMIENTO: ("fecha", "responsable"),
    TipoOrigen.SUPUESTO: ("motivo",),
    TipoOrigen.IA: ("proveedor", "modelo", "sesion", "propuesta"),
}

#: Prefijo de las claves de la referencia de un origen IA que declaran un campo supuesto por el
#: modelo (`supuesto.x0` = «esquina del baño en el origen»). R8 emite una ADVERTENCIA por cada una
#: (S4 §5.4).
PREFIJO_SUPUESTO_IA = "supuesto."


def clave_esp(tabla: str, id_fila: str) -> str:
    """Clave de una fila `esp_*` como la citan los hallazgos en `origen_ids` (spec §8.2)."""
    return f"{tabla}:{id_fila}"


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

    @property
    def faltantes(self) -> tuple[str, ...]:
        """Datos de la referencia obligatoria de su tipo que faltan o están en blanco."""
        dada = dict(self.referencia)
        return tuple(c for c in REFERENCIA_OBLIGATORIA[self.tipo] if not dada.get(c, "").strip())

    @property
    def incompleto(self) -> bool:
        """True si le falta algún dato de su referencia obligatoria (R8: ERROR)."""
        return bool(self.faltantes)

    @property
    def es_supuesto(self) -> bool:
        return self.tipo is TipoOrigen.SUPUESTO


def supuestos_de_ia(origen: OrigenMedida) -> tuple[tuple[str, str], ...]:
    """Los campos que la IA supuso, como pares (campo, motivo) ordenados; vacio si no es IA."""
    if origen.tipo is not TipoOrigen.IA:
        return ()
    return tuple(
        (clave.removeprefix(PREFIJO_SUPUESTO_IA), motivo)
        for clave, motivo in origen.referencia
        if clave.startswith(PREFIJO_SUPUESTO_IA)
    )
