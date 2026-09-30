"""Cómputo métrico del caso auditado, como `ItemComputo` del contrato.

Traduce cada línea de `apu_linea_base.PRESUPUESTO_AUDITADO` (la única copia de los datos, principio
DRY de NORMAS.md §2) a la forma que consume el núcleo. Aquí no se inventa ningún número: todas las
cantidades, unidades y descripciones vienen del PDF transcrito en el Sprint 0.

La unidad que escribió el proyectista se guarda además en `especificaciones[CLAVE_UNIDAD_ORIGINAL]`
porque `ItemComputo.__post_init__` normaliza `unidad` ("mts" -> "m") y la regla R3 necesita citar la
grafía original en su hallazgo.

Consumidores: `tests/fixtures/presupuesto_auditado.py` (Sesión I4) y el presupuesto de la Sesión
I0.5.
"""

from __future__ import annotations

from core.contracts import ComposicionAPU, Dominio, ItemComputo, OrigenTipo
from core.verification.directivas import CLAVE_UNIDAD_ORIGINAL
from tests.fixtures import apu_linea_base as linea_base

PREFIJO_ORIGEN_COMPUTO = "computo:"


def origen_de(codigo_partida: str) -> str:
    """`origen_id` del ítem de cómputo de una partida: la hoja de cómputos métricos del PDF."""
    return f"{PREFIJO_ORIGEN_COMPUTO}{codigo_partida}"


def items_auditados() -> tuple[ItemComputo, ...]:
    """Un `ItemComputo` por línea del presupuesto auditado, sin reglas ni especificaciones.

    `origen_tipo` es MANUAL porque el cómputo original se transcribió a mano: ninguna de sus
    cantidades declara la expresión que la produjo. La fixture de la Sesión I4 añade las reglas
    conocidas con `dataclasses.replace`.
    """
    return tuple(
        ItemComputo(
            codigo_partida=linea.codigo_partida,
            descripcion=linea.descripcion_computo,
            unidad=linea.unidad_computo,
            cantidad=linea.cantidad,
            origen_id=origen_de(linea.codigo_partida),
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
            especificaciones={CLAVE_UNIDAD_ORIGINAL: linea.unidad_computo},
        )
        for linea in linea_base.PRESUPUESTO_AUDITADO
    )


def composiciones_linea_base() -> dict[str, ComposicionAPU]:
    """Los cinco APU de la línea base, indexados por código de partida."""
    return {apu.codigo_partida: apu for apu in linea_base.APUS_LINEA_BASE}
