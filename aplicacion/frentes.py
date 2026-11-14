"""El frente de cada renglón del presupuesto (libro por frentes, ola 2, línea 3, 2026-11-13).

Un presupuesto vial se arma por frentes (una estación, un tramo, un sector): el libro de la
empresa trae una hoja de presupuesto por frente. Sílice guarda el frente de cada renglón como una
**directiva** de `ItemComputo.especificaciones` (`CLAVE_FRENTE`, «_frente»): una clave que empieza
por «_» es una instrucción y no una especificación técnica (`core/verification/directivas.py`),
así que R4 la ignora, viaja con el renglón y se guarda y vuelve con cada versión
(`core/budget/persistencia.py` guarda las especificaciones). `core/` no cambia.

Decisión simulada en `docs/bitacora/2026-11-13-ola2-libro-por-frentes.md` (D7).

**Agrupar el presupuesto por frente** (D8): `por_frentes` arma, con el cálculo de la Hoja, el
subtotal de cada frente (la suma de los totales de sus renglones, cantidad × P.U.) y el total
general (el del presupuesto), en el orden en que aparece cada frente; los renglones sin frente van
al final, en un grupo sin nombre (`frente: None`; la pantalla y el PDF lo rotulan `SIN_FRENTE`).
Un renglón pendiente (sin APU) se cuenta aparte y no suma. La interfaz no calcula: solo muestra lo
que manda el servidor. `poner_frentes` pone (o quita) el frente de renglones propios del
borrador; uno que sale del espacio no se cambia aquí.

**El PDF por frente** (ronda 1 del árbitro de la ola 2, hallazgo 8): `repartir_por_frente` reparte
las filas de la vista del presupuesto (las del PDF, `aplicacion.presupuesto_pdf`) en los mismos
grupos y en el mismo orden que `por_frentes`, así el subtotal de cada frente del PDF es el de la
pantalla; sin ningún frente, un solo grupo sin título (el PDF de siempre).

**El grupo de los renglones sin frente** (ronda 2 del árbitro de la ola 2, R2-N2) se rotula
«(sin frente)» en la pantalla y en el PDF, entre paréntesis como el «(en blanco)» de una tabla
dinámica de Excel; un frente no puede llamarse «Sin frente» ni «(sin frente)» (`es_reservado`, sin
distinguir mayúsculas, tildes ni blancos), ni a mano ni desde el libro, para que no se confunda
con ese grupo. Simulación en `docs/bitacora/arbitrajes/ola2-claude-xhigh.md`, «Ronda 2:
correcciones».
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Protocol

from aplicacion import hoja
from aplicacion.errores import HojaInvalida
from core.contracts import ItemComputo

__all__ = [
    "CLAVE_FRENTE",
    "MAX_FRENTE",
    "MENSAJE_RENGLON",
    "MENSAJE_RESERVADO",
    "SIN_FRENTE",
    "FrenteDelPresupuesto",
    "PresupuestoPorFrentes",
    "con_frente",
    "es_reservado",
    "frente_de",
    "poner_frentes",
    "por_frentes",
    "repartir_por_frente",
]

MENSAJE_RENGLON = "Ese renglón no está en el presupuesto o sale del espacio: vuelva a cargarlo."

#: La directiva del frente en `ItemComputo.especificaciones` (empieza por «_»: R4 no la lee).
CLAVE_FRENTE = "_frente"
#: El título del grupo de los renglones sin frente, en la pantalla y en el PDF (R2-N2).
SIN_FRENTE = "(sin frente)"
#: Los nombres que un frente no puede tener (ya normalizados, ver `es_reservado`).
_RESERVADOS = frozenset({"sin frente", "(sin frente)"})
MENSAJE_RESERVADO = (
    "Un frente no puede llamarse «Sin frente» ni «(sin frente)»: así se rotulan los renglones sin "
    "frente. Para quitar el frente de un renglón deje el campo vacío; a una hoja del libro con ese "
    "nombre, cámbiele el nombre en el libro."
)
#: Lo más largo que puede ser el nombre de un frente (una hoja de Excel se llama con 31).
MAX_FRENTE = 80


def es_reservado(frente: str | None) -> bool:
    """Si `frente` se llama como el grupo de los renglones sin frente («Sin frente», «(sin
    frente)»), sin distinguir mayúsculas, tildes ni blancos."""
    descompuesto = unicodedata.normalize("NFKD", (frente or "").casefold())
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return " ".join(sin_tildes.split()) in _RESERVADOS


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


@dataclass(frozen=True, slots=True)
class FrenteDelPresupuesto:
    """Un frente: su nombre (`None`: los renglones sin frente), cuántos renglones tiene, cuántos
    están pendientes (sin APU: no suman) y su subtotal."""

    frente: str | None
    renglones: int
    pendientes: int
    total: Decimal


@dataclass(frozen=True, slots=True)
class PresupuestoPorFrentes:
    """Los frentes en el orden en que aparecen (los renglones sin frente al final), el total
    general y si algún renglón tiene frente."""

    frentes: tuple[FrenteDelPresupuesto, ...]
    total: Decimal
    con_frentes: bool


def por_frentes(resultado: hoja.ResultadoHoja) -> PresupuestoPorFrentes:
    """El presupuesto del cálculo de la Hoja agrupado por frente (ver la cabecera del módulo)."""
    presupuesto = resultado.elaboracion.presupuesto
    valorados = dict(
        zip(
            hoja.claves_de_items([p.item for p in presupuesto.partidas]),
            presupuesto.partidas,
            strict=True,
        )
    )
    orden: list[str | None] = []
    cuentas: dict[str | None, list] = {}
    for clave, item in zip(hoja.claves_de_items(resultado.todos), resultado.todos, strict=True):
        frente = frente_de(item)
        if frente not in cuentas:
            orden.append(frente)
            cuentas[frente] = [0, 0, Decimal(0)]
        cuenta = cuentas[frente]
        cuenta[0] += 1
        renglon = valorados.get(clave)
        if renglon is None:
            cuenta[1] += 1
        else:
            cuenta[2] += renglon.total
    nombrados = [f for f in orden if f is not None]
    if None in cuentas or not orden:
        nombrados.append(None)
        cuentas.setdefault(None, [0, 0, Decimal(0)])
    return PresupuestoPorFrentes(
        frentes=tuple(FrenteDelPresupuesto(f, *cuentas[f]) for f in nombrados),
        total=presupuesto.total,
        con_frentes=any(f is not None for f in orden),
    )


class _FilaConClave(Protocol):
    @property
    def clave(self) -> str: ...


def repartir_por_frente[F: _FilaConClave](
    filas: Sequence[F], resultado: hoja.ResultadoHoja
) -> list[tuple[str, list[F]]]:
    """Las filas del presupuesto (cada una con la `clave` de su renglón) en grupos (frente, filas):
    los frentes en el orden en que aparecen y los renglones sin frente al final, en «Sin frente»;
    sin ningún frente, un solo grupo sin título (ver la cabecera del módulo)."""
    del_renglon = {
        clave: frente_de(item)
        for clave, item in zip(hoja.claves_de_items(resultado.todos), resultado.todos, strict=True)
    }
    grupos: dict[str | None, list[F]] = {}
    for fila in filas:
        grupos.setdefault(del_renglon.get(fila.clave), []).append(fila)
    if all(frente is None for frente in grupos):
        return [("", list(filas))]
    sin_frente = grupos.pop(None, None)
    repartidas = [(frente or "", del_frente) for frente, del_frente in grupos.items()]
    return [*repartidas, (SIN_FRENTE, sin_frente)] if sin_frente else repartidas


def poner_frentes(borrador: hoja.Borrador, frentes: Mapping[str, str | None]) -> hoja.Borrador:
    """El borrador con el frente de cada renglón propio de `frentes` (clave → frente; vacío o
    `None` lo quita). `HojaInvalida` si una clave no es de un renglón propio del borrador (los del
    espacio salen de su modelo), si un frente pasa de `MAX_FRENTE` o si se llama como el grupo de
    los renglones sin frente (`es_reservado`)."""
    claves = hoja.claves_propias(borrador)
    for clave, frente in frentes.items():
        if clave not in claves:
            raise HojaInvalida(MENSAJE_RENGLON)
        if len((frente or "").strip()) > MAX_FRENTE:
            raise HojaInvalida(f"El nombre de un frente no puede pasar de {MAX_FRENTE} caracteres.")
        if es_reservado(frente):
            raise HojaInvalida(MENSAJE_RESERVADO)
    items = tuple(
        con_frente(item, frentes[clave]) if clave in frentes else item
        for clave, item in zip(claves, borrador.items_base, strict=True)
    )
    return replace(borrador, items_base=items)
