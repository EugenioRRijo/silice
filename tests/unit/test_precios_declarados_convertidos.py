"""Un precio del corte declarado en otra moneda que la obra se convierte con la tasa del BCV de su
fecha (decisión de Eugenio del 2026-10-27, Tarea D2; antes era un 409, T25 punto 2).

Sobre la obra ficticia OB-S2 (`tests/fixtures/control_ob_s2.py`) en USD y, para el otro sentido,
su variante en Bs (los mismos números, rotulados en Bs). La tasa es una sembrada de 36,50 Bs/USD con
fecha valor 10/11/2026, de la fuente que deja `registrar_importacion` de la fixture de tasas.

Oráculos a mano, ninguno sacado del código bajo prueba:

- Bs → USD (obra en USD): 146,00 Bs / 36,50 Bs/USD = 4,00 USD. El material de B pasa de 3,00 a
  4,00 y u' de B = 5 + (4 − 3) × 1 = 6,00 (memoria de OB-S2, §1).
- USD → Bs (obra en Bs): 2,00 USD × 36,50 Bs/USD = 73,00 Bs. El material de B pasa de 3,00 a 73,00 y
  u' de B = 5 + (73 − 3) × 1 = 75,00.
- Con la tasa del 10/11 y un precio del 17/11 (7 días después) la tasa aún vale (a lo sumo 7 días,
  S1-R2) y la equivalencia dice la fecha de la tasa, 10/11; con el precio del 18/11 (8 días) no hay
  tasa y no se guarda nada.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from aplicacion.precios_declarados import (
    ReglaDelCorte,
    SinTasaDelCorte,
    declarar_precio_del_corte,
    precios_convertidos,
    precios_declarados,
)
from aplicacion.tablas_corte import PrecioDelCorte
from core import models
from core.catalog import Catalogo, abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures.hoja_versiones_api import registrar_tasa_en

D = Decimal
TUBO = "Material de Tuberia de drenaje"
AHORA = datetime(2026, 11, 20, 8, 0)
QUIEN = "Ana <ana>"
FUENTE_TASA = "https://www.bcv.org.ve/"
DIA_DE_LA_TASA = date(2026, 11, 10)


def _abrir(tmp_path: Path, moneda: str, con_tasa: bool) -> Iterator:
    ruta = tmp_path / f"carpeta_{moneda}.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion, moneda)
            ob.declarar_linea_base(sesion, "costo")
            if moneda == "USD":
                ob.registrar_v01_y_v02(sesion)
            if con_tasa:
                registrar_tasa_en(sesion, DIA_DE_LA_TASA, "36.50")
            sesion.commit()
            yield sesion
            sesion.rollback()
    finally:
        motor.dispose()


@pytest.fixture
def obra_usd(tmp_path: Path) -> Iterator:
    yield from _abrir(tmp_path, "USD", con_tasa=True)


@pytest.fixture
def obra_bs(tmp_path: Path) -> Iterator:
    yield from _abrir(tmp_path, "Bs", con_tasa=True)


@pytest.fixture
def obra_usd_sin_tasa(tmp_path: Path) -> Iterator:
    yield from _abrir(tmp_path, "USD", con_tasa=False)


def _declarar(sesion, precio: str, moneda: str | None, fecha: date = DIA_DE_LA_TASA):
    equivalencia = declarar_precio_del_corte(
        sesion,
        ob.NOMBRE,
        descripcion=TUBO,
        unidad="m",
        precio=D(precio),
        fecha=fecha,
        fuente="Estudio de mercado: precio propio",
        responsable=QUIEN,
        ahora=AHORA,
        moneda=moneda,
    )
    sesion.commit()
    return equivalencia


def _precios(sesion):
    return precios_declarados(sesion, ob.NOMBRE, Catalogo(sesion), ob.CORTE, "costo")


# --- Bs → USD ----------------------------------------------------------------------------------


def test_un_precio_en_bs_para_una_obra_en_usd_se_convierte_con_la_tasa_del_dia(obra_usd) -> None:
    equivalencia = _declarar(obra_usd, "146.00", "Bs")
    # 146,00 Bs / 36,50 Bs/USD = 4,00 USD
    assert equivalencia.convertido == D("4")
    assert equivalencia.moneda == "USD"
    assert (equivalencia.precio_original, equivalencia.moneda_original) == (D("146.00"), "Bs")
    assert (equivalencia.tasa, equivalencia.fecha_tasa, equivalencia.fuente_tasa) == (
        D("36.50"),
        DIA_DE_LA_TASA,
        FUENTE_TASA,
    )


def test_el_unitario_del_corte_usa_el_convertido(obra_usd) -> None:
    _declarar(obra_usd, "146.00", "Bs")
    precios = _precios(obra_usd)
    # el material de B pasa de 3,00 a 4,00 USD: u' de B = 5 + (4 − 3) × 1 = 6,00; A y C no cambian
    assert dict(precios.unitarios) == {"OB-A": D("10.00"), "OB-B": D("6.00"), "OB-C": D("20.00")}


def test_el_rastro_guarda_original_tasa_fecha_fuente_y_resultado_sin_sobrescribir(obra_usd) -> None:
    _declarar(obra_usd, "146.00", "Bs")
    [fila] = obra_usd.scalars(select(PrecioDelCorte)).all()
    assert (fila.precio, fila.moneda) == (D("4"), "USD")  # el resultado, en la moneda de la obra
    assert (fila.precio_original, fila.moneda_original) == (D("146.00"), "Bs")
    assert (fila.tasa, fila.fecha_tasa, fila.fuente_tasa) == (
        D("36.50"),
        DIA_DE_LA_TASA,
        FUENTE_TASA,
    )
    # solo inserción: declarar otro precio es otra fila y la primera queda como estaba
    _declarar(obra_usd, "182.50", "Bs", date(2026, 11, 11))
    filas = obra_usd.scalars(select(PrecioDelCorte).order_by(PrecioDelCorte.id)).all()
    assert [(f.precio_original, f.precio) for f in filas] == [
        (D("146.00"), D("4")),
        (D("182.50"), D("5")),  # 182,50 / 36,50 = 5,00
    ]


def test_un_precio_ya_en_la_moneda_de_la_obra_no_se_convierte_ni_deja_tasa(obra_usd) -> None:
    assert _declarar(obra_usd, "4.00", "USD") is None
    assert _declarar(obra_usd, "4.50", None) is None
    for fila in obra_usd.scalars(select(PrecioDelCorte)):
        assert (fila.moneda_original, fila.precio_original, fila.tasa) == (None, None, None)
        assert (fila.fecha_tasa, fila.fuente_tasa) == (None, None)


def test_la_tasa_vale_hasta_7_dias_y_la_equivalencia_dice_la_fecha_de_la_tasa(obra_usd) -> None:
    equivalencia = _declarar(obra_usd, "146.00", "Bs", date(2026, 11, 17))
    assert equivalencia.fecha_tasa == DIA_DE_LA_TASA


# --- USD → Bs ----------------------------------------------------------------------------------


def test_un_precio_en_usd_para_una_obra_en_bs_se_multiplica_por_la_tasa(obra_bs) -> None:
    equivalencia = _declarar(obra_bs, "2.00", "USD")
    # 2,00 USD × 36,50 Bs/USD = 73,00 Bs
    assert equivalencia.convertido == D("73.00")
    assert equivalencia.moneda == "Bs"
    assert (equivalencia.precio_original, equivalencia.moneda_original) == (D("2.00"), "USD")
    [fila] = obra_bs.scalars(select(PrecioDelCorte)).all()
    assert (fila.precio, fila.moneda, fila.moneda_original) == (D("73.00"), "Bs", "USD")


def test_el_unitario_de_la_obra_en_bs_usa_el_convertido(obra_bs) -> None:
    _declarar(obra_bs, "2.00", "USD")
    # el material de B pasa de 3,00 a 73,00 Bs: u' de B = 5 + (73 − 3) × 1 = 75,00
    assert dict(_precios(obra_bs).unitarios) == {
        "OB-A": D("10.00"),
        "OB-B": D("75.00"),
        "OB-C": D("20.00"),
    }


# --- sin tasa ----------------------------------------------------------------------------------


def test_sin_tasa_del_dia_no_se_convierte_ni_se_guarda_nada(obra_usd_sin_tasa) -> None:
    with pytest.raises(SinTasaDelCorte) as error:
        _declarar(obra_usd_sin_tasa, "146.00", "Bs")
    assert str(error.value) == (
        "No hay tasa del BCV del 10/11/2026 para convertir este precio a USD. Cargue la tasa en "
        "Índices y vuelva a intentarlo."
    )
    assert isinstance(error.value, ReglaDelCorte)  # la API ya lo lleva a 409
    obra_usd_sin_tasa.rollback()
    assert obra_usd_sin_tasa.scalars(select(PrecioDelCorte)).all() == []


def test_con_mas_de_7_dias_desde_la_tasa_tampoco_se_convierte(obra_usd) -> None:
    with pytest.raises(SinTasaDelCorte) as error:
        _declarar(obra_usd, "146.00", "Bs", date(2026, 11, 18))
    assert str(error.value) == (
        "No hay tasa del BCV del 18/11/2026 para convertir este precio a USD. Cargue la tasa en "
        "Índices y vuelva a intentarlo."
    )
    obra_usd.rollback()
    assert obra_usd.scalars(select(PrecioDelCorte)).all() == []


# --- lo que lee la pantalla del corte -----------------------------------------------------------


def test_los_precios_convertidos_vigentes_al_corte_traen_su_equivalencia(obra_usd) -> None:
    assert precios_convertidos(obra_usd, ob.NOMBRE, ob.CORTE) == []
    _declarar(obra_usd, "4.00", "USD", date(2026, 11, 9))  # sin conversión: no es de la lista
    _declarar(obra_usd, "146.00", "Bs", DIA_DE_LA_TASA)
    [convertido] = precios_convertidos(obra_usd, ob.NOMBRE, ob.CORTE)
    assert (convertido.descripcion, convertido.unidad, convertido.fecha) == (
        TUBO,
        "m",
        DIA_DE_LA_TASA,
    )
    assert convertido.fuente == "Estudio de mercado: precio propio"
    assert (convertido.equivalencia.precio_original, convertido.equivalencia.convertido) == (
        D("146.00"),
        D("4"),
    )
    # uno posterior al corte no cuenta (el corte es el 13/11)
    _declarar(obra_usd, "182.50", "Bs", date(2026, 11, 14))
    [vigente] = precios_convertidos(obra_usd, ob.NOMBRE, ob.CORTE)
    assert vigente.equivalencia.precio_original == D("146.00")
    # y si un convertido es reemplazado por uno sin conversión, deja de ser el vigente
    _declarar(obra_usd, "3.90", "USD", date(2026, 11, 12))
    assert precios_convertidos(obra_usd, ob.NOMBRE, ob.CORTE) == []


def test_ninguna_version_sellada_cambia_al_convertir(obra_usd) -> None:
    def sellados():
        return [
            (f.descripcion, f.precio)
            for f in obra_usd.scalars(
                select(models.LineaComposicionVersion).order_by(models.LineaComposicionVersion.id)
            )
        ]

    antes = sellados()
    _declarar(obra_usd, "146.00", "Bs")
    assert (TUBO, D("3.00")) in antes
    assert sellados() == antes
