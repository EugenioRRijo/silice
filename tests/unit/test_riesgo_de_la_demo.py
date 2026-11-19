"""Riesgo en la demo de Control (prueba en vivo del 2026-11-18): la obra corría pero salía plana.

Diagnóstico: la obra de la demo (`start.sembrar_obra_control`) está en USD, sus insumos eran
genéricos («Material G-0001», …) y la base solo traía la tasa ficticia. En un presupuesto en USD
solo mueven el precio las series viales (`proyeccion.py`, punto 4), que no estaban: sin mapa, P50 =
P80 = total base, reserva 0 y contribución vacía; con mapa, «0 meses completos».

La demo siembra ahora las dos series viales **ficticias** de
`data/samples/vial/series_ficticias.csv` corridas en el tiempo para que su último mes sea el
anterior al de `hoy` (cubren la ventana de 36 meses con cualquier fecha) y la obra trae dos insumos
que las siguen: el mapa lo declara la persona en la página, como en cualquier obra (decisión D1 del
encargo). Datos ficticios (NORMAS §1).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import start
from aplicacion.riesgo.obra import comprobar_obra, insumos_de_la_obra, proyectar_obra
from aplicacion.riesgo.proyeccion import MINIMO_DE_MESES
from aplicacion.riesgo.series import CEMENTO_ASFALTICO_PPI, GASOIL_USD, SERIES_VIALES
from core import models
from core.catalog import abrir_sesion, crear_motor
from scripts import generar_obra_control as generador
from tests.fixtures import costo_propio as cp

#: Los nombres que la guía del manual (§10.6) cita para la demo.
ASFALTO = "Cemento asfáltico CA-30 (ficticio)"
GASOIL = "Gasoil para equipos (ficticio)"
MAPA = {ASFALTO: CEMENTO_ASFALTICO_PPI.codigo, GASOIL: GASOIL_USD.codigo}
HOY = date(2026, 11, 19)
CODIGOS_VIALES = {s.codigo for s in SERIES_VIALES}


def _mes_anterior(dia: date) -> date:
    return (dia.replace(day=1) - timedelta(days=1)).replace(day=1)


def _sembrada(tmp_path: Path, hoy: date):
    destino = tmp_path / "obra_control.db"
    start.sembrar_obra_control(destino, hoy=hoy)
    return crear_motor(f"sqlite:///{destino.as_posix()}")


@pytest.fixture
def demo(tmp_path: Path) -> Iterator[tuple[Session, Session]]:
    motor = _sembrada(tmp_path, HOY)
    try:
        with abrir_sesion(motor) as caso, cp.instalacion_en_memoria() as ins:
            yield caso, ins
    finally:
        motor.dispose()


def test_la_obra_de_la_demo_ofrece_el_asfalto_y_el_gasoil_con_sus_series(demo) -> None:
    caso, ins = demo
    ofrecido = insumos_de_la_obra(caso, ins, generador.NOMBRE, generador.CODIGO)
    assert ofrecido.moneda == "USD"
    assert {ASFALTO, GASOIL} <= set(ofrecido.insumos)
    assert {s.codigo for s in ofrecido.series} == CODIGOS_VIALES


def test_la_demo_recien_sembrada_proyecta_con_dispersion_y_contribucion(demo) -> None:
    caso, ins = demo
    resultado = proyectar_obra(
        caso, ins, generador.NOMBRE, generador.CODIGO, MAPA, trayectorias=500
    )
    p = resultado.proyeccion
    assert resultado.inicio_de == "linea_base"
    assert p.meses_usados >= int(MINIMO_DE_MESES.valor)
    assert p.percentiles[80] > p.total_base
    assert p.percentiles[50] != p.total_base
    assert p.reserva == p.percentiles[80] - p.total_base > Decimal(0)
    assert {insumo for insumo, _ in p.contribucion} == {ASFALTO, GASOIL}
    assert all(monto > 0 for _, monto in p.contribucion)


def test_la_comprobacion_hacia_atras_corre_en_la_demo(demo) -> None:
    caso, ins = demo
    resultado = comprobar_obra(
        caso, ins, generador.NOMBRE, generador.CODIGO, MAPA, hoy=HOY, trayectorias=50
    )
    assert resultado.comprobacion.n_cortes > 0


@pytest.mark.parametrize(
    "hoy",
    [date(2026, 3, 2), date(2026, 11, 19), date(2027, 6, 15), date(2029, 2, 1)],
    ids=["antes-de-la-muestra", "hoy", "en-siete-meses", "en-dos-años"],
)
def test_las_series_ficticias_cubren_la_ventana_con_cualquier_fecha(tmp_path, hoy) -> None:
    # La muestra versionada termina en 09/2026: sin correrla, en un año la demo volvería a quedar
    # sin meses completos y, antes de 09/2026, la importación rechazaría las fechas futuras.
    motor = _sembrada(tmp_path, hoy)
    try:
        with abrir_sesion(motor) as caso, cp.instalacion_en_memoria() as ins:
            filas = caso.execute(
                select(models.SerieIndice.codigo, func.min(models.ValorIndice.fecha),
                       func.max(models.ValorIndice.fecha), func.count())
                .join(models.ValorIndice, models.ValorIndice.serie_id == models.SerieIndice.id)
                .where(models.SerieIndice.codigo.in_(CODIGOS_VIALES))
                .group_by(models.SerieIndice.codigo)
            ).all()  # fmt: skip
            assert {codigo for codigo, *_ in filas} == CODIGOS_VIALES
            for _codigo, _primera, ultima, cuantas in filas:
                assert ultima == _mes_anterior(hoy) and cuantas == 36
            p = proyectar_obra(
                caso, ins, generador.NOMBRE, generador.CODIGO, MAPA, trayectorias=200
            ).proyeccion
            assert p.meses_usados >= int(MINIMO_DE_MESES.valor)
            assert p.percentiles[80] > p.total_base
    finally:
        motor.dispose()


def test_las_series_de_la_demo_dicen_que_son_ficticias_y_no_pasan_de_hoy(demo) -> None:
    caso, _ = demo
    importaciones = caso.execute(
        select(models.SerieIndice.codigo, models.ImportacionIndice)
        .join(models.ImportacionIndice, models.ImportacionIndice.serie_id == models.SerieIndice.id)
        .where(models.SerieIndice.codigo.in_(CODIGOS_VIALES))
    ).all()
    assert {codigo for codigo, _ in importaciones} == CODIGOS_VIALES
    for _, importacion in importaciones:
        assert "ficticias" in importacion.fuente and "didácticas" in importacion.fuente
        assert "FICTICIAS" in importacion.archivo
    assert all(v.fecha <= HOY for v in caso.scalars(select(models.ValorIndice)))


def test_volver_a_sembrar_las_series_con_la_misma_huella_no_reimporta(demo) -> None:
    caso, _ = demo
    antes = caso.scalar(select(func.count()).select_from(models.ValorIndice))
    assert start.sembrar_series_viales_didacticas(caso, HOY) == [None, None]
    assert caso.scalar(select(func.count()).select_from(models.ValorIndice)) == antes


def test_sin_los_insumos_viales_la_obra_del_generador_es_la_de_siempre() -> None:
    # RNF-15 y las pruebas de la identidad CV miden la obra de siempre: lo vial es opcional.
    base = generador.generar(12, 10, 5, semilla=7)
    vial = generador.generar(12, 10, 5, semilla=7, insumos_viales=True)
    descripciones = {
        linea.descripcion for apu in base.composiciones.values() for linea in apu.materiales
    }
    assert ASFALTO not in descripciones and GASOIL not in descripciones
    assert [v.lineas for v in vial.valuaciones] == [v.lineas for v in base.valuaciones]
    assert vial.presupuesto.total > base.presupuesto.total
