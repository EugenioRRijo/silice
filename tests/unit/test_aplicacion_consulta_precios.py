"""`aplicacion.consulta.buscar` con el precio de la lista para armar (AC1b).

Al elegir un insumo en Componer se llenan descripción, unidad y precio. El precio no es el de la
lista vigente del catálogo sino el de la lista con que se arma a la fecha de la composición
(`aplicacion.listas_para_armar.lista_para_armar`, la misma que usa el guardado), con su moneda y su
fecha. Si esa lista no está en la moneda de la carpeta, no viaja ningún precio: solo el aviso.
Sin `detalle` ni `para_armar_al` la sugerencia es la de siempre (Producción y los demás campos).

Base en memoria con `crear_esquema` + `crear_esquema_carpeta`. Datos ficticios; los precios de las
dos listas son distintos a propósito y los oráculos están escritos a mano.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from aplicacion.consulta import Sugerencia, buscar
from aplicacion.listas_para_armar import declarar_moneda_de_la_carpeta
from aplicacion.tablas_carpeta import crear_esquema_carpeta
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor

JULIO = date(2026, 7, 1)
OCTUBRE = date(2026, 10, 1)
AGOSTO = date(2026, 8, 15)  # arma con la de julio: la de octubre todavía no rige


def _insumos(s: Session) -> dict[str, models.Insumo]:
    filas = {
        "MAT-1": models.Insumo(
            codigo="MAT-1", tipo="material", descripcion="Cemento gris ficticio", unidad="saco"
        ),
        "EQ-1": models.Insumo(
            codigo="EQ-1", tipo="equipo", descripcion="Mezcladora ficticia", unidad="h"
        ),
        "MO-1": models.Insumo(
            codigo="MO-1", tipo="mano_obra", descripcion="Albañil ficticio", unidad=None
        ),
        "MAT-9": models.Insumo(
            codigo="MAT-9", tipo="material", descripcion="Cemento blanco ficticio", unidad=None
        ),
    }
    s.add_all(filas.values())
    s.flush()
    return filas


def _lista(
    s: Session, insumos: dict[str, models.Insumo], nombre: str, moneda: str, fecha: date, precios
) -> None:
    lista = models.ListaPrecios(nombre=nombre, moneda=moneda, fecha_vigencia=fecha, origen="")
    s.add(lista)
    s.flush()
    for codigo, precio in precios.items():
        s.add(
            models.PrecioInsumo(
                lista_id=lista.id, insumo_id=insumos[codigo].id, precio=Decimal(precio)
            )
        )
    s.flush()


@pytest.fixture
def motor():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    crear_esquema_carpeta(motor)
    try:
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def en_bs(motor) -> Iterator[Session]:
    """Carpeta en Bs con dos listas en Bs: julio (cemento a 18,00) y octubre (cemento a 25,50)."""
    with abrir_sesion(motor) as s:
        insumos = _insumos(s)
        _lista(
            s,
            insumos,
            "Julio ficticia",
            "Bs",
            JULIO,
            {"MAT-1": "18.00", "EQ-1": "2000", "MO-1": "320.00"},
        )
        _lista(
            s,
            insumos,
            "Octubre ficticia",
            "Bs",
            OCTUBRE,
            {"MAT-1": "25.50", "EQ-1": "2500", "MO-1": "400.00"},
        )
        yield s


@pytest.fixture
def lista_en_usd(motor) -> Iterator[Session]:
    """La carpeta declaró Bs, pero su única lista vigente está en USD (hay que convertirla)."""
    with abrir_sesion(motor) as s:
        declarar_moneda_de_la_carpeta(
            s, "Bs", responsable="Ana Demo", ahora=datetime(2026, 6, 1, 8, 0)
        )
        insumos = _insumos(s)
        _lista(s, insumos, "Dólares ficticia", "USD", JULIO, {"MAT-1": "0.45", "MO-1": "8.00"})
        yield s


@pytest.fixture
def sin_lista(motor) -> Iterator[Session]:
    with abrir_sesion(motor) as s:
        _insumos(s)
        yield s


def _una(s: Session, tabla: str, q: str, **opciones) -> Sugerencia:
    halladas = buscar(s, tabla, q, **opciones)
    assert len(halladas) == 1, halladas
    return halladas[0]


# --- la misma moneda: el precio de la lista para armar a la fecha ----------------------------


def test_el_precio_es_el_de_la_lista_para_armar_a_la_fecha_y_no_el_de_la_vigente_hoy(
    en_bs: Session,
) -> None:
    cemento = _una(en_bs, "insumos", "cemento gris", para_armar_al=AGOSTO)
    assert cemento.precio == Decimal("18.00")  # julio; la vigente hoy (octubre) lo tiene a 25,50
    assert cemento.moneda == "Bs"
    assert cemento.fecha_precio == JULIO
    assert cemento.aviso_precio is None
    assert cemento.descripcion == "Cemento gris ficticio"
    assert cemento.unidad == "saco"


def test_a_otra_fecha_cambia_la_lista_y_con_ella_el_precio(en_bs: Session) -> None:
    cemento = _una(en_bs, "insumos", "cemento gris", para_armar_al=date(2026, 10, 20))
    assert (cemento.precio, cemento.moneda, cemento.fecha_precio) == (
        Decimal("25.50"),
        "Bs",
        OCTUBRE,
    )


def test_el_jornal_de_la_mano_de_obra_tambien_sale_de_la_lista_para_armar(en_bs: Session) -> None:
    albanil = _una(en_bs, "salarios_cct", "albañil", para_armar_al=AGOSTO)
    assert (albanil.precio, albanil.moneda, albanil.fecha_precio) == (
        Decimal("320.00"),
        "Bs",
        JULIO,
    )
    assert albanil.descripcion == "Albañil ficticio"
    assert albanil.unidad is None


def test_un_insumo_sin_precio_en_la_lista_no_trae_precio_ni_aviso(en_bs: Session) -> None:
    blanco = _una(en_bs, "insumos", "cemento blanco", para_armar_al=AGOSTO)
    assert (blanco.precio, blanco.moneda, blanco.fecha_precio, blanco.aviso_precio) == (
        None,
        None,
        None,
        None,
    )
    assert blanco.descripcion == "Cemento blanco ficticio"


# --- otra moneda: no viaja el precio, viaja el aviso --------------------------------------------


def test_en_otra_moneda_no_hay_precio_y_el_aviso_dice_las_dos_monedas(
    lista_en_usd: Session,
) -> None:
    cemento = _una(lista_en_usd, "insumos", "cemento gris", para_armar_al=AGOSTO)
    assert cemento.precio is None
    assert cemento.moneda == "USD"
    assert cemento.fecha_precio == JULIO
    assert cemento.aviso_precio == "El catálogo lo tiene en USD; escriba el precio en Bs."
    assert (cemento.descripcion, cemento.unidad) == ("Cemento gris ficticio", "saco")


def test_en_otra_moneda_el_aviso_de_la_mano_de_obra_habla_del_sueldo(
    lista_en_usd: Session,
) -> None:
    albanil = _una(lista_en_usd, "salarios_cct", "albañil", para_armar_al=AGOSTO)
    assert albanil.precio is None
    assert albanil.aviso_precio == "El catálogo lo tiene en USD; escriba el sueldo en Bs."


def test_en_otra_moneda_sin_precio_en_la_lista_no_hay_aviso(lista_en_usd: Session) -> None:
    mezcladora = _una(lista_en_usd, "insumos", "mezcladora", para_armar_al=AGOSTO)
    assert (mezcladora.precio, mezcladora.aviso_precio) == (None, None)
    assert mezcladora.descripcion == "Mezcladora ficticia"


# --- sin lista para armar o sin fecha: descripción y unidad, nunca precio ----------------------


def test_sin_lista_de_precios_hay_descripcion_y_unidad_pero_no_precio(sin_lista: Session) -> None:
    cemento = _una(sin_lista, "insumos", "cemento gris", para_armar_al=AGOSTO)
    assert (cemento.descripcion, cemento.unidad) == ("Cemento gris ficticio", "saco")
    assert (cemento.precio, cemento.moneda, cemento.fecha_precio, cemento.aviso_precio) == (
        None,
        None,
        None,
        None,
    )


def test_antes_de_la_primera_lista_no_hay_precio(en_bs: Session) -> None:
    cemento = _una(en_bs, "insumos", "cemento gris", para_armar_al=date(2026, 6, 30))
    assert cemento.precio is None and cemento.aviso_precio is None
    assert cemento.unidad == "saco"


def test_con_detalle_y_sin_fecha_hay_descripcion_y_unidad_pero_no_precio(en_bs: Session) -> None:
    cemento = _una(en_bs, "insumos", "cemento gris", detalle=True)
    assert (cemento.descripcion, cemento.unidad) == ("Cemento gris ficticio", "saco")
    assert (cemento.precio, cemento.moneda, cemento.fecha_precio) == (None, None, None)


# --- quien ya usa la consulta no cambia ------------------------------------------------------


def test_sin_detalle_ni_fecha_la_sugerencia_es_la_de_siempre(en_bs: Session) -> None:
    assert buscar(en_bs, "insumos", "cemento gris") == [
        Sugerencia(
            "MAT-1",
            "Cemento gris ficticio (MAT-1, saco)",
            "Catálogo de la carpeta de trabajo: material",
        )
    ]


def test_las_tablas_sin_precio_no_cambian_con_la_fecha(en_bs: Session) -> None:
    for tabla, q in (("partidas_viales", "carpeta"), ("tasa_bcv", "2026")):
        assert buscar(en_bs, tabla, q, para_armar_al=AGOSTO, detalle=True) == buscar(
            en_bs, tabla, q
        )
