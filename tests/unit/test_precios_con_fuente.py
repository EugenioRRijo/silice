"""La pestaña Precios no dice «el precio no tiene fuente» de un precio que la tiene (prueba de punta
a punta del 2026-11-13, D-17).

`aplicacion/hoja.py` (congelado del experimento) marca «Sin referencia ni cotización: el precio no
tiene fuente» cuando el precio no trae Ref de MaPreX ni cotización, aunque su origen declare una
fuente (la de la lista de la empresa, por fila o la de la lista). La vista (`hoja_vista`, no
congelada) quita ese aviso cuando la fuente existe y deja los demás. Datos FICTICIOS.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion import hoja, hoja_vista

SIN_FUENTE = "Sin referencia ni cotización: el precio no tiene fuente"
R12 = "R12: el precio tiene 40 días y el plazo es 30 (ficticio)"


def _fila(estado: str, fuente: str) -> hoja.FilaPrecio:
    return hoja.FilaPrecio(
        codigo="MAT-001",
        descripcion="Cemento de prueba",
        tipo="material",
        precio=Decimal("1.10"),
        lista="Empresa ficticia 2026-10-05",
        moneda="USD",
        fecha=date(2026, 10, 5),
        tasa=None,
        fecha_tasa=None,
        referencia="",
        cotizacion="",
        alcance="empresa",
        estado=estado,
        fuente=fuente,
    )


def _estados(*filas: hoja.FilaPrecio) -> list[str]:
    vista = hoja_vista.vista_precios(list(filas), "USD", date(2026, 11, 13))
    return [f.estado for f in vista.filas]


def test_con_fuente_no_dice_que_no_la_tiene() -> None:
    assert _estados(_fila(SIN_FUENTE, "cotización 17 (ficticia)")) == [hoja.TEXTO_OK]


def test_con_fuente_conserva_los_demas_avisos() -> None:
    assert _estados(_fila(f"{SIN_FUENTE}; {R12}", "cotización 17 (ficticia)")) == [R12]


def test_sin_fuente_el_aviso_sigue() -> None:
    assert _estados(_fila(SIN_FUENTE, "  ")) == [SIN_FUENTE]
