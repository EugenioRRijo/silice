"""Modalidad de mano de obra por linea: jornal frente a destajo.

El destajo es el salario por unidad de obra del articulo 114 de la LOTTT: entra completo al precio
unitario, sin factor de costos asociados al salario, sin bono de alimentacion y sin dividirse entre
el rendimiento. Ver docs/bitacora/2026-09-16-P0-hallazgo-destajo.md y la decision D9.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.contracts.apu import (
    ComposicionAPU,
    LineaManoObra,
    ModalidadManoObra,
    ParametrosCosto,
)
from core.costing import calcular_apu
from tests.fixtures import apu_linea_base as lb

#: Los cinco precios unitarios verificados de la linea base (CLAUDE.md SS4), con el mismo `Decimal`
#: exacto que produce el motor (comprobado contra `calcular_apu` antes de fijarlo aqui): comparar
#: por igualdad exacta, no por tolerancia prestada de `test_precio_unitario_reproduce_la_linea_base`
#: (`tests/unit/test_costing.py`), que existe para admitir redondeos de una fuente externa, no para
#: esta caracterizacion de que el motor no cambio ni un decimal.
PRECIO_UNITARIO_EXACTO = {
    "LB-01-EXC": Decimal("8.600418750"),
    "LB-02-TUB": Decimal("10.1933700"),
    "LB-03-ENC": Decimal("33.237875000"),
    "LB-04-CON": Decimal("242.63965000"),
    "LB-05-REL": Decimal("52.57656250"),
}


def _mixta() -> ComposicionAPU:
    """Una partida con un ayudante a jornal y un instalador a destajo."""
    return ComposicionAPU(
        codigo_partida="X-01",
        descripcion="Instalacion de piso ceramico",
        unidad="m2",
        rendimiento=Decimal("50"),
        mano_obra=(
            LineaManoObra("Ayudante", Decimal("2"), Decimal("3")),
            LineaManoObra(
                "Instalador a destajo",
                Decimal("1"),
                Decimal("6"),
                ModalidadManoObra.DESTAJO,
            ),
        ),
    )


def test_una_linea_sin_modalidad_es_jornal():
    linea = LineaManoObra("Albanil de 1ra", Decimal("1"), Decimal("5"))

    assert linea.modalidad is ModalidadManoObra.JORNAL


def test_modalidad_coacciona_desde_texto_valido():
    """Una modalidad que llega como str (p. ej. desde una columna de base de datos) se normaliza."""
    linea = LineaManoObra("Instalador", Decimal("1"), Decimal("6"), "destajo")

    assert linea.modalidad is ModalidadManoObra.DESTAJO


def test_modalidad_invalida_lanza_value_error():
    with pytest.raises(ValueError):
        LineaManoObra("Instalador", Decimal("1"), Decimal("6"), "cualquier_cosa")


def test_el_destajo_entra_completo():
    """6 USD por m2 instalado son 6 USD en el APU: ni FCAS, ni bono, ni division."""
    composicion = ComposicionAPU(
        codigo_partida="X-02",
        descripcion="Instalacion a destajo",
        unidad="m2",
        rendimiento=Decimal("50"),
        mano_obra=(
            LineaManoObra(
                "Instalador", Decimal("1"), Decimal("6"), ModalidadManoObra.DESTAJO
            ),
        ),
    )

    resultado = calcular_apu(composicion, ParametrosCosto())

    assert resultado.mano_obra == Decimal("6")


def test_total_obreros_excluye_el_destajo():
    """Un subcontratista que cobra por metro no devenga bono de alimentacion."""
    assert _mixta().total_obreros == Decimal("2")


def test_la_composicion_mixta_suma_los_dos_bloques():
    parametros = ParametrosCosto()
    composicion = _mixta()

    resultado = calcular_apu(composicion, parametros)

    jornal = (
        Decimal("2") * Decimal("3") * (1 + parametros.fcas)
        + parametros.bono_alimentacion * Decimal("2")
    ) / Decimal("50")
    destajo = Decimal("6")
    assert resultado.mano_obra == jornal + destajo

    # El destajo debe llegar hasta el costo directo, no quedarse contabilizado y sin facturar.
    assert resultado.costo_directo == resultado.materiales + resultado.equipos + resultado.mano_obra

    costo_directo_esperado = jornal + destajo
    con_administracion_esperado = costo_directo_esperado * (1 + parametros.administracion)
    precio_unitario_esperado = con_administracion_esperado * (1 + parametros.utilidad)
    assert resultado.precio_unitario == precio_unitario_esperado


def test_la_linea_base_no_se_mueve():
    """Caracterizacion: con todas las lineas en JORNAL, el resultado es el de siempre.

    Igualdad exacta de `Decimal` contra los cinco precios unitarios verificados por la auditoria
    (auditoria de la rama completa, 2026-09-23), no la tolerancia de +-0,01 que usa
    `tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base` para admitir un
    redondeo externo: aqui lo que se vigila es que agregar la modalidad de mano de obra (P1.1) no
    le movio ni un decimal al motor cuando todas las lineas siguen a JORNAL.
    """
    for apu in lb.APUS_LINEA_BASE:
        resultado = calcular_apu(apu, lb.PARAMETROS_LINEA_BASE)
        esperado = PRECIO_UNITARIO_EXACTO[apu.codigo_partida]
        assert resultado.precio_unitario == esperado, apu.codigo_partida
