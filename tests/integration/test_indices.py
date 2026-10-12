"""SL-E1: series, importaciones idempotentes y tasa aplicable (S1 §5.3, S1-R1, S1-R2)."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core import models
from core.catalog.indices import (
    Observacion,
    TasaNoDisponible,
    definicion_tasa,
    registrar_importacion,
    tasa_aplicable,
    valor_en,
)

D = Decimal
HUELLA = "a" * 64
FUENTE = "https://www.bcv.org.ve/estadisticas/tipo-cambio-de-referencia-smc"


def _importar(sesion, lado, observaciones, huella=HUELLA):
    return registrar_importacion(
        sesion, definicion_tasa(lado), observaciones, archivo="2_1_2c26_smc.xls", huella=huella,
        fuente=FUENTE, fecha_descarga=date(2026, 10, 8), responsable="Admin",
        filas_leidas=len(observaciones), filas_rechazadas=0,
    )


@pytest.fixture
def con_tasas(sesion):
    # 01/10/2026 (jueves): literal verificado (antecedentes §6). 02/10 (viernes): 862,00 FICTICIO.
    _importar(sesion, "compra", [Observacion(date(2026, 10, 1), D("858.02"))])
    _importar(sesion, "venta", [Observacion(date(2026, 10, 1), D("860.18")),
                                Observacion(date(2026, 10, 2), D("862.00"))])
    return sesion


def test_el_sabado_toma_la_tasa_del_viernes_y_cada_lado_la_suya(con_tasas):
    assert tasa_aplicable(con_tasas, date(2026, 10, 3)).valor == D("862.00")
    assert tasa_aplicable(con_tasas, date(2026, 10, 1), lado="compra").valor == D("858.02")
    assert tasa_aplicable(con_tasas, date(2026, 10, 1)).fecha == date(2026, 10, 1)


def test_siete_dias_naturales_pasan_y_ocho_se_rechazan(con_tasas):
    assert tasa_aplicable(con_tasas, date(2026, 10, 9)).fecha == date(2026, 10, 2)
    with pytest.raises(TasaNoDisponible, match="8 dias"):
        tasa_aplicable(con_tasas, date(2026, 10, 10))
    with pytest.raises(TasaNoDisponible, match="no hay tasa"):
        tasa_aplicable(con_tasas, date(2026, 9, 30))


def test_la_misma_huella_no_escribe_nada(con_tasas):
    antes = con_tasas.scalar(select(func.count()).select_from(models.ValorIndice))
    assert _importar(con_tasas, "venta", [Observacion(date(2026, 10, 5), D("1"))]) is None
    assert con_tasas.scalar(select(func.count()).select_from(models.ValorIndice)) == antes


def test_una_revision_es_otra_importacion_y_la_citada_sigue_valiendo(con_tasas):
    primera = valor_en(con_tasas, "BCV-USD-VENTA", date(2026, 10, 1))
    _importar(con_tasas, "venta", [Observacion(date(2026, 10, 1), D("860.50"))], huella="b" * 64)
    assert valor_en(con_tasas, "BCV-USD-VENTA", date(2026, 10, 1)).valor == D("860.50")
    citada = valor_en(con_tasas, "BCV-USD-VENTA", date(2026, 10, 1),
                      importacion_id=primera.importacion_id)
    assert citada.valor == D("860.18")


def test_sin_fuente_sin_responsable_fecha_repetida_o_valor_no_positivo_se_rechaza(sesion):
    with pytest.raises(ValueError, match="fuente"):
        registrar_importacion(sesion, definicion_tasa("venta"), [], archivo="x", huella=HUELLA,
                              fuente=" ", fecha_descarga=date(2026, 10, 8), responsable="A",
                              filas_leidas=0, filas_rechazadas=0)
    with pytest.raises(ValueError, match="repetida"):
        _importar(sesion, "venta", [Observacion(date(2026, 10, 1), D("1")),
                                    Observacion(date(2026, 10, 1), D("2"))])
    with pytest.raises(ValueError, match="mayor que cero"):
        Observacion(date(2026, 10, 1), D("0"))
