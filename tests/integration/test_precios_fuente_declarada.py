"""La pestaña Precios mira la fuente declarada de cada precio (D-17 de la prueba de punta a punta).

«Sin referencia ni cotización: el precio no tiene fuente» se decía de todo precio sin Ref de MaPreX
ni cotización, aunque la lista de la empresa declarara su fuente fila por fila. Ahora la fuente
declarada cuenta, y la que el precio solo hereda del `origen` de una lista (la regla de
`core.catalog.origen.origenes_efectivos` para un precio sin `PrecioOrigen`, que las copias
arrastran) sigue sin contar. Oráculo: la tabla de la simulación del acta
`docs/bitacora/2026-11-13-recongelado-experimento-2.md`. Datos FICTICIOS (la vivienda de
`tests/fixtures/obra_vivienda.py`, «Empresa ficticia»).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion import hoja
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from core import models
from core.budget import crear_proyecto
from core.budget.moneda import declarar_moneda
from core.catalog import Catalogo, abrir_sesion, crear_motor
from core.catalog.empresa import PrecioPropio, crear_lista_de_empresa
from core.contracts.dominio import Dominio
from operacion.base_datos import preparar_base
from tests.fixtures.obra_vivienda import FECHA, ITEMS, sembrar_catalogo

ANA = "Ana <ana>"
OBRA = "Vivienda ficticia"
FUENTE_DE_LA_LISTA = "Cotizaciones ficticias oct-2026"
SIN_FUENTE = "Sin referencia ni cotización: el precio no tiene fuente"
OK = hoja.TEXTO_OK


def _insumo(sesion, descripcion: str) -> models.Insumo:
    return sesion.scalars(
        select(models.Insumo).where(models.Insumo.descripcion == descripcion)
    ).one()


@pytest.fixture
def sesion(tmp_path: Path) -> Iterator:
    """La vivienda valorada con una lista de empresa: el cemento con su cotización ficticia y el
    agua con la fuente de la lista escrita en su fila; lo demás, heredado de la lista base."""
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as s:
        base = sembrar_catalogo(s)
        declarar_moneda_de_la_carpeta(s, "Bs", responsable=ANA, ahora=datetime(2026, 11, 2, 8))
        declarar_moneda(s, crear_proyecto(s, OBRA, dominio=Dominio.CIVIL), "Bs", responsable=ANA)
        cemento, agua = _insumo(s, "Cemento gris"), _insumo(s, "Agua")
        empresa = crear_lista_de_empresa(
            s, "Empresa ficticia", "J-00000000-0", base,
            [
                PrecioPropio(cemento.id, Decimal("99"), date(2026, 10, 30), "Cotización 17"),
                PrecioPropio(agua.id, Decimal("2.5"), date(2026, 10, 30), FUENTE_DE_LA_LISTA),
            ],
            moneda="Bs", fecha=date(2026, 10, 30), fuente=FUENTE_DE_LA_LISTA, referencia=None,
        )  # fmt: skip
        s.commit()
        hoja.crear_primera_version(
            s,
            Catalogo(s),
            OBRA,
            hoja.Borrador(fecha=FECHA, moneda="Bs", items_base=ITEMS),
            fuente="Medición ficticia",
            responsable=ANA,
            lista=empresa,
        )
        yield s
    motor.dispose()


def _estados(sesion, codigo: str) -> dict[str, str]:
    return {f.descripcion: f.estado for f in hoja.precios_de_version(sesion, OBRA, codigo)}


def test_la_fuente_declarada_en_la_fila_cuenta(sesion):
    estados = _estados(sesion, "001")
    assert estados["Cemento gris"] == OK
    # la fila trae escrita la fuente de la lista de la empresa: también está declarada
    assert estados["Agua"] == OK


def test_lo_heredado_del_origen_de_la_lista_base_sigue_sin_fuente(sesion):
    estados = _estados(sesion, "001")
    heredados = {d: e for d, e in estados.items() if d not in ("Cemento gris", "Agua")}
    assert heredados and set(heredados.values()) == {SIN_FUENTE}


def test_una_cotizacion_copia_la_lista_y_la_fuente_declarada_sigue_contando(sesion):
    hoja.cotizar(
        sesion, Catalogo(sesion), OBRA, "001", insumo=_insumo(sesion, "Andamio").codigo,
        precio=Decimal("9"), proveedor="Proveedor ficticio", numero="C-1",
        fecha=date(2026, 11, 1), responsable=ANA, fuente="cotización C-1",
    )  # fmt: skip
    estados = _estados(sesion, "002")
    assert (estados["Cemento gris"], estados["Agua"], estados["Andamio"]) == (OK, OK, OK)
    assert estados["Pala y pico"] == SIN_FUENTE
