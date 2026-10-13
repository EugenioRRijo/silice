"""Alertas de precio en la moneda del libro y en bolívares (Silice 1.5, RF-106; spec §4, F-D8).

Los servicios de la instalación (tasa del BCV, precio propio) son dobles inyectados en
`ContextoPrecios`: sin base y sin red. Oráculo: aritmética a mano con las tasas ficticias de la
prueba (precio × tasa; variación = (nuevo − anterior) ÷ anterior, como fracción) y el umbral del
spec (5 %, «pasa» si |variación| ≥ umbral).

INSUMOS del libro limpio: MT-01 10 USD, MT-02 25, MT-03 0,8 (fuente «REFERENCIAL — ajustar»),
MO-01 20, MO-02 15, MO-03 3, EQ-01 30 (sin fuente), EQ-02 4.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from adapters.hoja_empresa.lector import leer_libro
from fusion.alertas import (
    TIPO_BS,
    TIPO_EMPRESA,
    TIPO_SIN_FUENTE,
    TIPO_VERSION,
    UMBRAL_POR_DEFECTO,
    ContextoPrecios,
    alertas_de_precios,
)
from tests.fixtures.libros_empresa import (
    APUS_LIMPIOS,
    INSUMOS,
    D,
    Siembra,
    con,
    construir_libro,
    libro_limpio,
)

F_LIBRO = date(2026, 7, 31)
F_DEV = date(2026, 10, 13)
CODIGOS = ["MT-01", "MT-02", "MT-03", "MO-01", "MO-02", "MO-03", "EQ-01", "EQ-02"]


@pytest.fixture(scope="module")
def libro():
    return leer_libro(libro_limpio().datos, "limpio.xlsx")


def _tasas(tabla):
    return lambda fecha: tabla.get(fecha)


def test_umbral_por_defecto_es_cinco_por_ciento():
    assert UMBRAL_POR_DEFECTO == D("0.05")


def test_sin_contexto_sin_fuente_y_bs_no_contrastable(libro):
    filas = alertas_de_precios(libro, F_LIBRO, F_DEV, None)
    # Orden: tipo (sin fuente, empresa, versión, USD-Bs), prefijo (EQ < MO < MT) y número.
    assert [(f.tipo, f.codigo) for f in filas] == [
        (TIPO_SIN_FUENTE, "EQ-01"),
        (TIPO_SIN_FUENTE, "MT-03"),
        *[
            (TIPO_BS, c)
            for c in ["EQ-01", "EQ-02", "MO-01", "MO-02", "MO-03", "MT-01", "MT-02", "MT-03"]
        ],
    ]
    sin = {f.codigo: f for f in filas if f.tipo == TIPO_SIN_FUENTE}
    assert "dice «REFERENCIAL — ajustar»" in sin["MT-03"].mensaje
    assert "está vacía" in sin["EQ-01"].mensaje
    assert "INSUMOS!E11" in sin["EQ-01"].mensaje
    for f in filas:
        if f.tipo == TIPO_BS:
            assert (f.tasa, f.precio_bs, f.variacion) == (None, None, None)
            assert f.mensaje.startswith("no contrastable")
            assert f.fecha == "2026-07-31"
            assert f.moneda == "USD"


@pytest.mark.parametrize(
    ("tasa_dev", "variacion", "juicio"),
    [
        (D("105"), D("0.05"), "pasa del umbral"),  # (105 − 100) ÷ 100 = 5 % ≥ 5 %
        (D("104.99"), D("0.0499"), "dentro del umbral"),
        (D("95"), D("-0.05"), "pasa del umbral"),  # la caída también cuenta
    ],
)
def test_usd_bs_con_tasa_de_las_dos_fechas(libro, tasa_dev, variacion, juicio):
    ctx = ContextoPrecios(tasa_en=_tasas({F_LIBRO: D("100"), F_DEV: tasa_dev}))
    filas = {
        f.codigo: f for f in alertas_de_precios(libro, F_LIBRO, F_DEV, ctx) if f.tipo == TIPO_BS
    }
    mt01 = filas["MT-01"]  # 10 USD: 1 000 Bs al 31/07 y 10 × tasa al 13/10
    assert mt01.tasa == tasa_dev
    assert mt01.precio_bs == D("10") * tasa_dev
    assert mt01.variacion == variacion
    assert juicio in mt01.mensaje
    assert "1000 Bs al 2026-07-31 (tasa 100)" in mt01.mensaje


def test_falta_la_tasa_de_una_fecha(libro):
    ctx = ContextoPrecios(tasa_en=_tasas({F_LIBRO: D("100")}))
    mt01 = next(
        f
        for f in alertas_de_precios(libro, F_LIBRO, F_DEV, ctx)
        if f.codigo == "MT-01" and f.tipo == TIPO_BS
    )
    assert mt01.tasa is None
    assert mt01.mensaje == "no contrastable: la instalación no tiene la tasa del BCV de 2026-10-13"


def test_sin_fecha_del_libro_no_se_inventa(libro):
    ctx = ContextoPrecios(tasa_en=_tasas({F_LIBRO: D("100"), F_DEV: D("105")}))
    mt01 = next(
        f
        for f in alertas_de_precios(libro, None, F_DEV, ctx)
        if f.codigo == "MT-01" and f.tipo == TIPO_BS
    )
    assert mt01.tasa is None and mt01.fecha == ""
    assert "la fecha del libro (no legible)" in mt01.mensaje


def test_libro_en_bolivares_mide_el_valor_en_dolares(libro):
    """Libro en Bs: 10 Bs valen 0,1 USD a 100 y 0,08 USD a 125: variación −20 %."""
    en_bs = replace(libro, portada=replace(libro.portada, moneda="Bolívares (Bs)"))
    ctx = ContextoPrecios(tasa_en=_tasas({F_LIBRO: D("100"), F_DEV: D("125")}))
    mt01 = next(
        f
        for f in alertas_de_precios(en_bs, F_LIBRO, F_DEV, ctx)
        if f.codigo == "MT-01" and f.tipo == TIPO_BS
    )
    assert mt01.moneda == "Bs"
    assert mt01.precio_bs == D("10")
    assert mt01.variacion == D("-0.2")
    assert "pasa del umbral" in mt01.mensaje


@pytest.mark.parametrize(
    ("propio", "umbral", "hay"),
    [
        # (10 − 8) ÷ 8 = 0,25
        (D("8"), D("0.25"), True),  # |0,25| ≥ 0,25
        (D("8"), D("0.2500001"), False),
        (D("10"), UMBRAL_POR_DEFECTO, False),  # mismo precio
    ],
)
def test_precio_propio_de_la_empresa_con_umbral(libro, propio, umbral, hay):
    ctx = ContextoPrecios(
        precio_propio=lambda c: (propio, date(2026, 6, 1), "USD") if c == "MT-01" else None,
        umbral=umbral,
    )
    empresa = [f for f in alertas_de_precios(libro, F_LIBRO, F_DEV, ctx) if f.tipo == TIPO_EMPRESA]
    if not hay:
        assert empresa == []
        return
    assert [(f.codigo, f.variacion) for f in empresa] == [("MT-01", D("0.25"))]
    assert "precio propio de la instalación 8 USD del 2026-06-01" in empresa[0].mensaje


def test_precio_propio_en_otra_moneda_se_convierte_con_la_tasa_de_su_fecha(libro):
    """Propio 900 Bs del 01/06 a 100 Bs/USD = 9 USD; (10 − 9) ÷ 9 = 0,111…"""
    ctx = ContextoPrecios(
        tasa_en=_tasas({date(2026, 6, 1): D("100")}),
        precio_propio=lambda c: (D("900"), date(2026, 6, 1), "Bs") if c == "MT-01" else None,
    )
    empresa = [f for f in alertas_de_precios(libro, F_LIBRO, F_DEV, ctx) if f.tipo == TIPO_EMPRESA]
    assert len(empresa) == 1
    assert abs(empresa[0].variacion - (D("10") - D("9")) / D("9")) <= D("1e-20")
    assert "(9 USD a la tasa 100)" in empresa[0].mensaje


def test_precio_propio_sin_tasa_para_convertir_no_es_contrastable(libro):
    ctx = ContextoPrecios(
        tasa_en=_tasas({}),
        precio_propio=lambda c: (D("900"), date(2026, 6, 1), "Bs") if c == "MT-01" else None,
    )
    empresa = [f for f in alertas_de_precios(libro, F_LIBRO, F_DEV, ctx) if f.tipo == TIPO_EMPRESA]
    assert [(f.codigo, f.variacion) for f in empresa] == [("MT-01", None)]
    assert empresa[0].mensaje.startswith("no contrastable")
    assert "tasa del BCV de 2026-06-01" in empresa[0].mensaje


def test_otra_version_del_libro():
    """B-1 contra B-2: MT-01 pasa de 12 a 10 (−16,67 %); EQ-02 no estaba en la otra versión."""
    insumos_b1 = tuple(
        replace(i, precio=D("12")) if i.codigo == "MT-01" else i
        for i in INSUMOS
        if i.codigo != "EQ-02"
    )
    a1, a2, a3 = APUS_LIMPIOS
    apus_b1 = (a1, con(a2, equipos=()), a3)  # B-1 no usa EQ-02
    otro = leer_libro(construir_libro(apus_b1, Siembra(insumos=insumos_b1)).datos, "b1.xlsx")
    libro = leer_libro(libro_limpio().datos, "b2.xlsx")
    version = [
        f for f in alertas_de_precios(libro, F_LIBRO, F_DEV, None, otro) if f.tipo == TIPO_VERSION
    ]
    assert [(f.codigo, f.variacion) for f in version] == [
        ("EQ-02", None),
        ("MT-01", (D("10") - D("12")) / D("12")),
    ]
    assert "costaba 12 USD; en esta (INSUMOS!E5) 10" in version[1].mensaje
    assert version[0].mensaje == "EQ-02 no está en la otra versión (b1.xlsx)"


def test_alertas_deterministas(libro):
    ctx = ContextoPrecios(tasa_en=_tasas({F_LIBRO: D("100"), F_DEV: D("105")}))
    assert alertas_de_precios(libro, F_LIBRO, F_DEV, ctx) == alertas_de_precios(
        libro, F_LIBRO, F_DEV, ctx
    )


def test_cada_alerta_trae_codigo_moneda_precio_fecha_y_fuente(libro):
    filas = alertas_de_precios(libro, F_LIBRO, F_DEV, None)
    precios = {i.codigo: i.precio for i in INSUMOS}
    for f in filas:
        assert f.precio == precios[f.codigo]
        assert f.moneda == "USD"
        assert f.fecha == "2026-07-31"
    assert {f.codigo for f in filas} == set(CODIGOS)


def test_umbral_negativo_se_rechaza_antes_de_abrir_la_base():
    from fusion.servicios import servicios_desde_sesion

    with pytest.raises(ValueError, match="fracción no negativa"):
        servicios_desde_sesion(None, umbral=D("-0.0001"))  # type: ignore[arg-type]
