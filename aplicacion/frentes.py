"""El frente de cada renglón del presupuesto (libro por frentes, ola 2, línea 3, 2026-11-13).

Un presupuesto vial se arma por frentes (una estación, un tramo, un sector): el libro de la
empresa trae una hoja de presupuesto por frente. Sílice guarda el frente de cada renglón como una
**directiva** de `ItemComputo.especificaciones` (`CLAVE_FRENTE`, «_frente»): una clave que empieza
por «_» es una instrucción y no una especificación técnica (`core/verification/directivas.py`),
así que R4 la ignora, viaja con el renglón y se guarda y vuelve con cada versión
(`core/budget/persistencia.py` guarda las especificaciones). `core/` no cambia.

Decisión simulada en `docs/bitacora/2026-11-13-ola2-libro-por-frentes.md` (D7).
"""

from __future__ import annotations

from dataclasses import replace

from core.contracts import ItemComputo

__all__ = ["CLAVE_FRENTE", "MAX_FRENTE", "con_frente", "frente_de"]

#: La directiva del frente en `ItemComputo.especificaciones` (empieza por «_»: R4 no la lee).
CLAVE_FRENTE = "_frente"
#: Lo más largo que puede ser el nombre de un frente (una hoja de Excel se llama con 31).
MAX_FRENTE = 80


def frente_de(item: ItemComputo) -> str | None:
    """El frente del renglón, o `None` si no tiene."""
    valor = item.especificaciones.get(CLAVE_FRENTE, "").strip()
    return valor or None


def con_frente(item: ItemComputo, frente: str | None) -> ItemComputo:
    """El renglón con el frente `frente` (sin blancos en los bordes); `None` o vacío lo quita."""
    especificaciones = {k: v for k, v in item.especificaciones.items() if k != CLAVE_FRENTE}
    limpio = (frente or "").strip()
    if limpio:
        especificaciones[CLAVE_FRENTE] = limpio
    return replace(item, especificaciones=especificaciones)
