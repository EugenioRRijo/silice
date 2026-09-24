"""INV-049: los resumenes de los cuatro sembradores redondean con la fuente unica.

Oraculo escrito a mano: un solo material de precio 2,125 con cantidad 1, rendimiento 1, sin equipos
ni mano de obra, y administracion y utilidad en cero. El costo directo, el precio unitario y el
total son exactamente 2,125. `f"{x:.2f}"` redondea al par y da `2.12`;
`core.verification.texto.formatear_decimal` (`ROUND_HALF_UP`, dos decimales de
`DECIMALES_PRESENTACION`) da `2.13`. El resumen debe decir `2.13` y nunca `2.12`.
"""

from __future__ import annotations

import importlib
from datetime import date
from decimal import Decimal

import pytest

from core.budget import ResultadoElaboracion, elaborar
from core.contracts import (
    ComposicionAPU,
    Dominio,
    ItemComputo,
    LineaMaterial,
    OrigenTipo,
    ParametrosCosto,
)

SEMBRADORES = (
    "scripts.seed_demo",
    "scripts.seed_industrial",
    "scripts.seed_sistemas",
    "scripts.seed_telecom",
)


def _resultado_de_dos_con_ciento_veinticinco() -> ResultadoElaboracion:
    composicion = ComposicionAPU(
        codigo_partida="PRUEBA-A",
        descripcion="Partida minima de prueba",
        unidad="m",
        rendimiento=Decimal(1),
        materiales=(
            LineaMaterial(
                descripcion="Material de prueba",
                unidad="m",
                cantidad=Decimal(1),
                precio=Decimal("2.125"),
            ),
        ),
    )
    item = ItemComputo(
        codigo_partida="PRUEBA-A",
        descripcion="Partida minima de prueba",
        unidad="m",
        cantidad=Decimal(1),
        origen_id="fila-uno",
        origen_tipo=OrigenTipo.MANUAL,
        dominio=Dominio.CIVIL,
    )
    resultado = elaborar(
        [item],
        {"PRUEBA-A": composicion},
        ParametrosCosto(administracion=Decimal(0), utilidad=Decimal(0)),
        codigo="PRUEBA",
        fecha=date(2026, 9, 24),
        moneda="USD",
    )
    # El oraculo: el total es exactamente 2,125, el caso en que `:.2f` y ROUND_HALF_UP difieren.
    assert resultado.presupuesto.total == Decimal("2.125")
    return resultado


@pytest.mark.parametrize("nombre", SEMBRADORES)
def test_el_resumen_redondea_con_la_fuente_unica(nombre: str) -> None:
    modulo = importlib.import_module(nombre)
    texto = modulo.resumen(_resultado_de_dos_con_ciento_veinticinco(), "USD")
    assert "2.13" in texto
    assert "2.12" not in texto


@pytest.mark.parametrize("nombre", SEMBRADORES)
def test_el_resumen_declara_la_auditoria(nombre: str) -> None:
    # Principio 7 (CLAUDE.md §2): el informe de auditoria acompana siempre al presupuesto, tambien
    # en el texto que imprime cada sembrador. El oraculo sale del informe, no de `resumen`.
    resultado = _resultado_de_dos_con_ciento_veinticinco()
    esperado = (
        f"Auditoria: {len(resultado.informe.hallazgos)} hallazgo(s), "
        f"{'CUMPLE' if resultado.informe.cumple else 'NO CUMPLE'}"
    )
    texto = importlib.import_module(nombre).resumen(resultado, "USD")
    assert esperado in [linea.strip() for linea in texto.splitlines()]
