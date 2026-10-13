"""Los servicios de ESTA instalación para la reauditoría (spec S3 §9 paso 3): la referencia MaPreX,
la tasa del BCV y la erosión, leídas de la base de quien revisa (S1: listas, orígenes y tasas).

La reauditoría recibe estos servicios por inyección (`Servicios`); aquí se prueba el armado real
contra una base en memoria. Los esperados son literales sembrados a mano o aritmética aparte
(fracciones), nunca lo que devuelve la función bajo prueba."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction

import pytest

from auditoria.reauditoria import ReferenciaDeMercado
from auditoria.servicios import servicios_de_la_instalacion
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor

D = Decimal
FECHA = date(2026, 11, 10)


@pytest.fixture
def base():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        yield sesion
    motor.dispose()


def _referencia(sesion, moneda="USD", tasa=None, precio_unico="10.00", nombre="MaPreX"):
    lista = models.ListaPrecios(nombre=nombre, moneda=moneda, fecha_vigencia=FECHA, origen="maprex")
    sesion.add(lista)
    sesion.flush()
    sesion.add(
        models.ListaPreciosOrigen(
            lista_id=lista.id,
            tasa=tasa,
            fecha_tasa=FECHA if tasa else None,
            alcance=models.ALCANCE_REFERENCIA,
        )
    )
    insumos = {}
    for codigo, descripcion in (("MAT-1", "Cemento"), ("MAT-2", "Arena"), ("MAT-3", "Arena fina")):
        insumo = sesion.query(models.Insumo).filter_by(codigo=codigo).one_or_none()
        if insumo is None:
            insumo = models.Insumo(
                codigo=codigo, tipo="material", descripcion=descripcion, unidad="m3"
            )
            sesion.add(insumo)
            sesion.flush()
        insumos[codigo] = insumo
    for codigo, ref, precio in (
        ("MAT-1", "MP-0042", D(precio_unico)),
        ("MAT-2", "MP-0099", D("5.00")),
        ("MAT-3", "MP-0099", D("6.00")),
    ):
        fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=insumos[codigo].id, precio=precio)
        sesion.add(fila)
        sesion.flush()
        sesion.add(models.ReferenciaPrecio(precio_id=fila.id, referencia=ref))
    sesion.flush()
    return lista


def _tasas(sesion, *valores: tuple[date, str], codigo="BCV-USD-VENTA") -> None:
    serie = models.SerieIndice(
        codigo=codigo,
        nombre="USD",
        organismo="BCV",
        unidad="Bs/USD",
        periodicidad="diaria",
    )
    sesion.add(serie)
    sesion.flush()
    importacion = models.ImportacionIndice(
        serie_id=serie.id,
        archivo="tasas.xls",
        huella="a" * 64,
        fuente="prueba",
        fecha_descarga=FECHA,
        fecha_importacion=datetime(2026, 11, 10),
        responsable="admin",
        filas_leidas=len(valores),
        filas_rechazadas=0,
    )
    sesion.add(importacion)
    sesion.flush()
    for fecha, valor in valores:
        sesion.add(
            models.ValorIndice(
                serie_id=serie.id, importacion_id=importacion.id, fecha=fecha, valor=D(valor)
            )
        )
    sesion.flush()


def test_sin_lista_de_referencia_no_hay_precio_de_mercado(base) -> None:
    servicios = servicios_de_la_instalacion(base)
    assert servicios.referencia_de("MP-0042") is None
    assert servicios.reglas_de_control is None  # S2 no entrega el servicio de R13-R14 (RP8-21)


def test_la_referencia_de_un_codigo_unico_trae_su_precio_y_su_moneda(base) -> None:
    _referencia(base)
    servicios = servicios_de_la_instalacion(base)
    assert servicios.referencia_de("MP-0042") == ReferenciaDeMercado(
        "MP-0042", D("10.00"), "USD", None
    )
    assert servicios.referencia_de("MP-9999") is None


def test_una_ref_repetida_en_la_referencia_no_contrasta(base) -> None:
    """S1 §6.3: si dos insumos de la lista de referencia comparten la misma Ref, no se sabe cuál
    es la del mercado y no se contrasta ninguno."""
    _referencia(base)
    assert servicios_de_la_instalacion(base).referencia_de("MP-0099") is None


def test_una_lista_global_no_es_referencia(base) -> None:
    """Solo cuenta la lista de alcance `referencia`: una global con la misma Ref no contrasta."""
    lista = models.ListaPrecios(nombre="global", moneda="USD", fecha_vigencia=FECHA)
    insumo = models.Insumo(codigo="MAT-1", tipo="material", descripcion="Cemento", unidad="saco")
    base.add_all([lista, insumo])
    base.flush()
    fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=D("10.00"))
    base.add(fila)
    base.flush()
    base.add(models.ReferenciaPrecio(precio_id=fila.id, referencia="MP-0042"))
    base.flush()
    assert servicios_de_la_instalacion(base).referencia_de("MP-0042") is None


def test_manda_la_ultima_lista_de_referencia_cargada(base) -> None:
    _referencia(base, precio_unico="10.00", nombre="MaPreX julio")
    _referencia(base, precio_unico="12.50", nombre="MaPreX octubre")
    ref = servicios_de_la_instalacion(base).referencia_de("MP-0042")
    assert ref is not None and ref.precio == D("12.50")


def test_la_referencia_en_bs_trae_la_tasa_de_su_lista(base) -> None:
    _referencia(base, moneda="Bs", tasa=D("36.50"))
    ref = servicios_de_la_instalacion(base).referencia_de("MP-0042")
    assert (ref.moneda, ref.tasa) == ("Bs", D("36.50"))


def test_la_tasa_es_la_ultima_hasta_la_fecha_y_a_mas_de_7_dias_no_hay(base) -> None:
    _tasas(base, (date(2026, 11, 3), "36.00"), (date(2026, 11, 9), "37.25"))
    servicios = servicios_de_la_instalacion(base)
    assert servicios.tasa_en(date(2026, 11, 10)) == D("37.25")  # la de mayor fecha <= la pedida
    assert servicios.tasa_en(date(2026, 11, 8)) == D("36.00")  # 5 días después de la del 3
    assert servicios.tasa_en(date(2026, 11, 16)) == D("37.25")  # 7 días naturales: todavía vale
    assert servicios.tasa_en(date(2026, 11, 17)) is None  # 8 días: no se convierte (S1-R2)
    assert servicios.tasa_en(date(2026, 11, 1)) is None  # antes de la primera: no hay


def test_la_tasa_de_compra_solo_con_el_lado_compra(base) -> None:
    _tasas(base, (date(2026, 11, 9), "37.00"), codigo="BCV-USD-COMPRA")
    assert servicios_de_la_instalacion(base).tasa_en(FECHA) is None  # venta por omisión
    assert servicios_de_la_instalacion(base, lado="compra").tasa_en(FECHA) == D("37.00")


def test_la_erosion_de_un_precio_en_usd_es_cero_y_sin_tasa_es_desconocida(base) -> None:
    erosion = servicios_de_la_instalacion(base).erosion
    assert erosion(D("100"), "USD", "USD", D("100"), None, None) == D(0)
    assert erosion(D("3650"), "Bs", "Bs", D("3650"), None, D("40")) is None
    assert erosion(D("3650"), "Bs", "Bs", D("3650"), D("40"), None) is None


def test_la_erosion_en_bs_es_la_diferencia_a_la_tasa_de_hoy(base) -> None:
    erosion = servicios_de_la_instalacion(base).erosion
    # 100 Bs a tasa 40 valían 2,50 USD; hoy, a tasa 50, 2,00 USD: perdió 100*(50/40) - 100 = 25 Bs
    assert erosion(D("100"), "Bs", "Bs", D("100"), D("40"), D("50")) == D("25")


def test_la_erosion_en_una_lista_en_usd_de_un_original_en_bs_es_en_usd(base) -> None:
    erosion = servicios_de_la_instalacion(base).erosion
    resultado = erosion(D("2.50"), "USD", "Bs", D("100"), D("40"), D("50"))
    # 100/40 - 100/50 = 2,5 - 2 = 0,5 USD, hecho con fracciones
    assert Fraction(resultado) == Fraction(100, 40) - Fraction(100, 50)
