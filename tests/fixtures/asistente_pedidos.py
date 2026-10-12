"""Ayudantes de las pruebas del asistente (S4): el pedido del bano y un catalogo en memoria.

Unica copia de como se arma un `asistente.validacion.Contexto` en las pruebas. El pedido es el de
`tests/fixtures/memorias/bano_of001.md` reducido a lo que las pruebas citan literalmente.
"""

from __future__ import annotations

from datetime import date

from asistente.catalogo import CatalogoDeLaBase, PartidaVista
from asistente.propuestas import OrigenIA
from asistente.validacion import Contexto
from core.contracts.dominio import Dominio
from ui.hoja import Borrador

PEDIDO = "Bano de 2,4 x 1,5 m con alto de 2,5 m, con un lavamanos a 60 cm del piso."
FECHA = date(2026, 10, 5)
ORIGEN = OrigenIA(proveedor="guionado", modelo="guion-1", sesion=7)

PARTIDAS = (
    PartidaVista("AF-SALIDA", "Salida de agua fria", "punto", Dominio.CIVIL),
    PartidaVista("ELE-001", "Tablero electrico", "pieza", Dominio.CIVIL, de_maprex=True),
)

AMBIENTE = {
    "id": "BAN-01",
    "nombre": "Bano",
    "x0": "0",
    "y0": "0",
    "largo": "2.4",
    "ancho": "1.5",
    "alto": "2.5",
    "citas": [
        {"campo": "largo", "texto": "2,4"},
        {"campo": "ancho", "texto": "1,5 m"},
        {"campo": "alto", "texto": "alto de 2,5 m"},
    ],
    "supuestos": [
        {"campo": "x0", "motivo": "esquina del bano en el origen"},
        {"campo": "y0", "motivo": "esquina del bano en el origen"},
    ],
}


def catalogo() -> CatalogoDeLaBase:
    return CatalogoDeLaBase(PARTIDAS)


def contexto(
    borrador: Borrador | None = None, pendientes=(), textos=(PEDIDO,), siguiente_id="P1"
) -> Contexto:
    return Contexto(
        textos_de_la_persona=tuple(textos),
        borrador=borrador if borrador is not None else Borrador(fecha=FECHA),
        pendientes=tuple(pendientes),
        catalogo=catalogo(),
        origen=ORIGEN,
        siguiente_id=siguiente_id,
    )
