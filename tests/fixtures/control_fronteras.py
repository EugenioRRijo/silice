# tests/fixtures/control_fronteras.py
"""Partidas de otros dominios sin mano de obra a jornal (spec S2 §4.6, ARQ-H3).

Las opciones «más cuadrillas» y «horas extra» dividen por el rendimiento y escalan el jornal de la
cuadrilla: una partida solo a destajo o sin mano de obra no tiene nada que escalar y debe dar «no
aplica» sin dividir. Ninguna partida de TI-001 ni de SIS-001 lo es tal cual (todas pagan jornal),
así que cada una se siembra como **variante declarada** de una partida real del caso:

* TI-001: `TI-LAP` (laptop HP configurada) con el técnico pagado a destajo, 50 USD por unidad;
* SIS-001: el APU de un punto de función sin mano de obra (todo el costo sería de terceros).

Son datos ficticios y declarados (NORMAS.md §1): la composición real de esas partidas no se toca.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from core.contracts.apu import ComposicionAPU, LineaManoObra, ModalidadManoObra
from tests.fixtures import caso_ti001
from tests.fixtures import tarifas_sistemas as sis

D = Decimal
PARTIDA_TI001 = "TI-LAP"
PARTIDA_SIS001 = "SIS-FRONTERA-01"


def ti001_a_destajo() -> ComposicionAPU:
    """`TI-LAP` con la mano de obra a destajo: no hay jornal que escalar."""
    original = caso_ti001.COMPOSICIONES[PARTIDA_TI001]
    return replace(
        original,
        mano_obra=(
            LineaManoObra(
                "Tecnico a destajo (variante declarada)", D(1), D(50), ModalidadManoObra.DESTAJO
            ),
        ),
    )


def sis001_sin_mano_de_obra() -> ComposicionAPU:
    """El APU de un punto de función de SIS-001 sin mano de obra."""
    return replace(
        sis.composicion_para(PARTIDA_SIS001, "Punto de funcion sin mano de obra (variante)"),
        mano_obra=(),
    )
