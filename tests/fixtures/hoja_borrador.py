"""Ayudantes de las pruebas de la hoja (SF3): el borrador del baño de OF-001 con APU sinteticos.

Unica copia de como se arma un `ui.hoja.Borrador` en las pruebas: el baño de agua fria de
`espacio_bano` con un origen de levantamiento (sin supuestos: sin ruido de R8) y un APU por
partida de un solo material a 2,00 por unidad, rendimiento 1 y parametros por defecto. Asi el
precio unitario de cada partida es 2 x 1,15 x 1,10 = 2,53, que las pruebas calculan a mano.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from adapters.espacio import Espacio, OrigenMedida, TipoOrigen
from aplicacion import hoja
from core.budget import plan_secuencial
from core.contracts import ComposicionAPU, ItemComputo, ParametrosCosto
from core.contracts.apu import LineaMaterial
from tests.fixtures.espacio_bano import espacio_bano

D = Decimal
FECHA = date(2026, 10, 5)
PRECIO_MATERIAL = D("2")
PU_SINTETICO = D("2.53")  # 2 x (1 + 0,15) x (1 + 0,10)


def espacio_bano_limpio() -> Espacio:
    """El baño con un origen de levantamiento: ninguna fila es supuesto."""
    levantamiento = OrigenMedida(
        id="O1",
        tipo=TipoOrigen.LEVANTAMIENTO,
        referencia={"fecha": "2026-10-05", "responsable": "E"},
    )
    return replace(espacio_bano(), origenes=(levantamiento,))


def composiciones_sinteticas(items: list[ItemComputo]) -> dict[str, ComposicionAPU]:
    """Un APU por codigo: un material de cantidad 1 a `PRECIO_MATERIAL`, rendimiento 1."""
    return {
        i.codigo_partida: ComposicionAPU(
            codigo_partida=i.codigo_partida,
            descripcion=i.descripcion,
            unidad=i.unidad,
            rendimiento=D("1"),
            materiales=(LineaMaterial("material", i.unidad, D("1"), PRECIO_MATERIAL),),
        )
        for i in items
    }


def borrador_bano(con_plan: bool = True, **cambios) -> hoja.Borrador:
    """El borrador del baño, con su plan secuencial (o sin plan) y `cambios` sobre sus campos."""
    espacio = espacio_bano_limpio()
    items = hoja.items_del_borrador(espacio, hoja.TODAS)
    base = hoja.Borrador(
        fecha=FECHA,
        espacio=espacio,
        composiciones=composiciones_sinteticas(items),
        parametros=ParametrosCosto(),
    )
    if con_plan:
        presupuesto = hoja.elaborar_borrador(base).elaboracion.presupuesto
        base = replace(base, plan=tuple(plan_secuencial(presupuesto)))
    return replace(base, **cambios)
