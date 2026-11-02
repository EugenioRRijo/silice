"""Una carpeta de trabajo ficticia en Bs con su lista de julio (MP-1, Tarea 3: Componer guarda en la
lista de hoy). La comparten `tests/unit/test_composicion_lista_de_hoy.py` y
`tests/unit/test_api_composicion_prever.py` (INV-052: lo compartido entre pruebas vive aquí).

Datos ficticios: «Cemento gris» (saco, 18,00 Bs), «Arena lavada» (m3, 450,00 Bs) y «Albañil»
(320,00 Bs) en la lista «MaPreX julio 2026 en Bs» del 01/07/2026. Los textos esperados están
escritos a mano (los mensajes del plan y la regla de nombres de la Tarea 1).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from core import models

HOY = date(2026, 10, 25)
JULIO = date(2026, 7, 1)
MAPREX = "MaPreX julio 2026 en Bs"
DE_HOY = "MaPreX julio 2026 en Bs al 25/10/2026"
CONDICIONES = "Cuadrilla ficticia de prueba: un albañil y un ayudante, terreno seco."
SIN_LISTA = (
    "Esta carpeta de trabajo no tiene lista de precios para armar. Créela a partir de MaPreX o "
    "convirtiendo la que tiene."
)
OTRA_MONEDA = (
    "La lista vigente «MaPreX julio 2026 en Bs» está en Bs y la carpeta trabaja en USD: "
    "conviértala antes de armar."
)

#: (código, tipo, descripción, unidad, precio en Bs) de la siembra ficticia.
INSUMOS = (
    ("MAT-001", "material", "Cemento gris", "saco", Decimal("18.00")),
    ("MAT-002", "material", "Arena lavada", "m3", Decimal("450.00")),
    ("MO-001", "mano_obra", "Albañil", None, Decimal("320.00")),
)
PRECIOS_DE_JULIO = {codigo: precio for codigo, *_, precio in INSUMOS}


def sembrar(s: Session, *, moneda_declarada: str | None = None) -> None:
    """Los tres insumos y la lista de julio, sin confirmar. Con `moneda_declarada`, la carpeta la
    declara antes de tener lista (el único momento en que puede declarar una moneda distinta de la
    de su lista: el foco 1 del plan)."""
    if moneda_declarada is not None:
        declarar_moneda_de_la_carpeta(
            s, moneda_declarada, responsable="Ana Demo", ahora=datetime(2026, 6, 1, 8, 0)
        )
    lista = models.ListaPrecios(nombre=MAPREX, moneda="Bs", fecha_vigencia=JULIO, origen="")
    s.add(lista)
    s.flush()
    for codigo, tipo, descripcion, unidad, precio in INSUMOS:
        insumo = models.Insumo(codigo=codigo, tipo=tipo, descripcion=descripcion, unidad=unidad)
        s.add(insumo)
        s.flush()
        s.add(models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=precio))
    s.flush()


def nombres_de_listas(s: Session) -> list[str]:
    return list(s.scalars(select(models.ListaPrecios.nombre).order_by(models.ListaPrecios.id)))


def precios_de(s: Session, nombre: str) -> dict[str, Decimal]:
    """Código de insumo → precio, en la lista de ese nombre."""
    filas = s.execute(
        select(models.Insumo.codigo, models.PrecioInsumo.precio)
        .join(models.PrecioInsumo, models.PrecioInsumo.insumo_id == models.Insumo.id)
        .join(models.ListaPrecios, models.ListaPrecios.id == models.PrecioInsumo.lista_id)
        .where(models.ListaPrecios.nombre == nombre)
    )
    return dict(filas.all())


def cuentas(s: Session) -> dict[str, int]:
    """Cuántas filas hay de todo lo que un guardado de Componer escribe."""
    tablas = {
        "listas": models.ListaPrecios,
        "precios": models.PrecioInsumo,
        "insumos": models.Insumo,
        "partidas": models.Partida,
        "lineas": models.ComposicionAPU,
        "rendimientos": models.Rendimiento,
    }
    return {
        nombre: s.scalar(select(func.count()).select_from(tabla))
        for nombre, tabla in tablas.items()
    }


def codigos_de_insumos(s: Session) -> set[str]:
    return set(s.scalars(select(models.Insumo.codigo)))
