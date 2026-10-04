"""Generador determinista de puntos para la hoja de presupuesto (RNF-11, spec §4.3 y §11.3).

`generar_items(n, semilla)` produce `n` ítems de cómputo reproducibles (misma semilla, mismos
ítems) sobre las partidas de `composiciones_de_prueba()`, que son pequeñas y sintéticas: sirven
para medir el costo de `core.budget.elaborar`, no para representar una obra. Lo usan la prueba
corta de `st.data_editor` (SF0) y `scripts/medir_rnf11.py` (SF3).
"""

from __future__ import annotations

import random
from decimal import Decimal

from core.contracts import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo

__all__ = ["PARAMETROS_PRUEBA", "composiciones_de_prueba", "generar_items"]

PARAMETROS_PRUEBA = ParametrosCosto()

#: (código, descripción, unidad, rendimiento, precio del material por unidad de obra)
_PARTIDAS = (
    ("GEN-01", "Partida sintetica 01", "m3", "8", "15"),
    ("GEN-02", "Partida sintetica 02", "m2", "12", "9.5"),
    ("GEN-03", "Partida sintetica 03", "m", "20", "6"),
    ("GEN-04", "Partida sintetica 04", "m3", "5", "32"),
    ("GEN-05", "Partida sintetica 05", "m2", "16", "12"),
    ("GEN-06", "Partida sintetica 06", "m", "40", "3.25"),
    ("GEN-07", "Partida sintetica 07", "m3", "10", "21"),
    ("GEN-08", "Partida sintetica 08", "m2", "25", "4.8"),
)


def composiciones_de_prueba() -> dict[str, ComposicionAPU]:
    """Una composición simple (un material, un equipo, una cuadrilla) por partida generada."""
    return {
        codigo: ComposicionAPU(
            codigo_partida=codigo,
            descripcion=descripcion,
            unidad=unidad,
            rendimiento=Decimal(rendimiento),
            materiales=(
                LineaMaterial("Material " + codigo, unidad, Decimal("1.05"), Decimal(precio)),
            ),
            equipos=(
                LineaEquipo("Herramienta " + codigo, Decimal("2"), Decimal("15"), Decimal("0.03")),
            ),
            mano_obra=(LineaManoObra("Ayudante", Decimal("2"), Decimal("3")),),
        )
        for codigo, descripcion, unidad, rendimiento, precio in _PARTIDAS
    }


def generar_items(n: int, semilla: int = 0) -> list[ItemComputo]:
    """`n` ítems reproducibles: partida elegida al azar entre las de `composiciones_de_prueba()`,
    cantidad `Decimal` con dos decimales, origen manual `gen-{i}`, dominio civil."""
    azar = random.Random(semilla)
    composiciones = composiciones_de_prueba()
    codigos = sorted(composiciones)
    items: list[ItemComputo] = []
    for i in range(n):
        apu = composiciones[azar.choice(codigos)]
        cantidad = Decimal(azar.randint(1, 100_000)) / Decimal(100)
        items.append(
            ItemComputo(
                codigo_partida=apu.codigo_partida,
                descripcion=f"{apu.descripcion} (punto {i})",
                unidad=apu.unidad,
                cantidad=cantidad,
                origen_id=f"gen-{i}",
                origen_tipo=OrigenTipo.MANUAL,
                dominio=Dominio.CIVIL,
            )
        )
    return items
