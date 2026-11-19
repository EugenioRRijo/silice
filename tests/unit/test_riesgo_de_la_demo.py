"""Riesgo en la demo de Control (prueba en vivo del 2026-11-18): la obra corría pero salía plana.

Diagnóstico: la obra de la demo (`start.sembrar_obra_control`) está en USD, sus insumos eran
genéricos («Material G-0001», …) y la base solo traía la tasa ficticia. En un presupuesto en USD
solo mueven el precio las series viales (`proyeccion.py`, punto 4), que no estaban: sin mapa, P50 =
P80 = total base, reserva 0 y contribución vacía; con mapa, «0 meses completos».

La demo siembra ahora las dos series viales **ficticias** de
`data/samples/vial/series_ficticias.csv` corridas en el tiempo para que su último mes sea el
anterior al de `hoy` (cubren de sobra el mínimo de historia para proyectar, con cualquier fecha de
siembra) y la obra trae dos insumos que las siguen: el mapa lo declara la persona en la página, como
en cualquier obra (decisión D1 del encargo). Datos ficticios (NORMAS §1).

Oráculos a mano (no salen del motor):

- Obra sin lo vial: total 132.852,520075 (el de siempre, el que miden RNF-15 y la identidad CV).
- Lo vial añade 0,01 t de asfalto a 600 USD/t a G-0001 (349 m³) y 1 l de gasoil a 0,35 USD/l a
  G-0002 (282 m³): (349 × 6 + 282 × 0,35) × 1,15 × 1,10 (administración y utilidad) =
  2.192,70 × 1,265 = **2.773,7655**, un 2,09 % del total: el avance en dinero de Control de obra
  casi no cambia.
  Total con lo vial: **135.626,285575**.
"""

from __future__ import annotations

import csv
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
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "series_ficticias.csv"
#: El último mes de la muestra versionada (09/2026), base del corrimiento.
ULTIMO_DE_LA_MUESTRA = date(2026, 9, 1)
TOTAL_SIN_VIALES = Decimal("132852.520075")
INCREMENTO_VIAL = Decimal("2773.7655")
TOTAL_CON_VIALES = Decimal("135626.285575")
CANTIDADES = {"G-0001": Decimal(349), "G-0002": Decimal(282)}


def _mes_anterior(dia: date) -> date:
    return (dia.replace(day=1) - timedelta(days=1)).replace(day=1)


def _mas_meses(dia: date, meses: int) -> date:
    indice = dia.year * 12 + dia.month - 1 + meses
    return date(indice // 12, indice % 12 + 1, 1)


def _meses_entre(desde: date, hasta: date) -> int:
    return (hasta.year - desde.year) * 12 + hasta.month - desde.month


def _muestra_corrida(hoy: date) -> dict[str, list[tuple[date, Decimal]]]:
    """La muestra versionada, por serie y en orden, con cada fecha corrida los meses que van de
    09/2026 al mes anterior al de `hoy`."""
    corrimiento = _meses_entre(ULTIMO_DE_LA_MUESTRA, _mes_anterior(hoy))
    esperado: dict[str, list[tuple[date, Decimal]]] = {}
    with MUESTRA.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            fecha = _mas_meses(date.fromisoformat(fila["fecha"]), corrimiento)
            esperado.setdefault(fila["serie"], []).append((fecha, Decimal(fila["valor"])))
    return esperado


def _guardado(caso: Session) -> dict[str, list[tuple[date, Decimal]]]:
    filas = caso.execute(
        select(models.SerieIndice.codigo, models.ValorIndice.fecha, models.ValorIndice.valor)
        .join(models.ValorIndice, models.ValorIndice.serie_id == models.SerieIndice.id)
        .where(models.SerieIndice.codigo.in_(CODIGOS_VIALES))
        .order_by(models.SerieIndice.codigo, models.ValorIndice.fecha)
    ).all()
    guardado: dict[str, list[tuple[date, Decimal]]] = {}
    for codigo, fecha, valor in filas:
        guardado.setdefault(codigo, []).append((fecha, valor))
    return guardado


def _cuantos(caso: Session, modelo) -> int:
    return caso.scalar(select(func.count()).select_from(modelo))


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
    assert p.total_base == TOTAL_CON_VIALES
    # dispersión, no solo deriva: si todas las trayectorias fueran iguales, P80 = P50
    assert p.percentiles[80] > p.percentiles[50] > p.total_base
    # intervalo independiente: el asfalto y el gasoil son el 2 % de la obra y sus series ficticias
    # varían menos de un 3 % al mes, así que la reserva es positiva y menor que el 1 % de la base
    assert Decimal(0) < p.reserva < TOTAL_CON_VIALES / 100
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
    [
        date(2026, 3, 2),
        date(2026, 11, 19),
        date(2027, 1, 1),
        date(2027, 1, 31),
        date(2027, 3, 31),
        date(2027, 6, 15),
        date(2028, 2, 29),
        date(2028, 3, 1),
        date(2029, 2, 1),
    ],
    ids=[
        "antes-de-la-muestra",
        "hoy",
        "primero-de-año",
        "fin-de-enero",
        "fin-de-marzo",
        "en-siete-meses",
        "bisiesto",
        "despues-del-bisiesto",
        "en-dos-años",
    ],
)
def test_las_series_ficticias_cubren_la_ventana_con_cualquier_fecha(tmp_path, hoy) -> None:
    # La muestra versionada termina en 09/2026: sin correrla, en un año la demo volvería a quedar
    # sin meses completos y, antes de 09/2026, la importación rechazaría las fechas futuras.
    motor = _sembrada(tmp_path, hoy)
    try:
        with abrir_sesion(motor) as caso, cp.instalacion_en_memoria() as ins:
            guardado = _guardado(caso)
            assert set(guardado) == CODIGOS_VIALES
            for codigo, valores in guardado.items():
                fechas = [fecha for fecha, _ in valores]
                # 36 meses seguidos, sin huecos, que terminan el mes anterior al de hoy
                assert fechas[-1] == _mes_anterior(hoy) and max(fechas) <= hoy
                assert _meses_entre(fechas[0], fechas[-1]) == 35
                assert fechas == [_mas_meses(fechas[0], i) for i in range(36)]
                # el corrimiento no toca los valores: los de la muestra, en orden
                assert valores == _muestra_corrida(hoy)[codigo]
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
    assert len(importaciones) == len(CODIGOS_VIALES)
    for _, importacion in importaciones:
        assert "ficticias" in importacion.fuente and "didácticas" in importacion.fuente
        assert "FICTICIAS" in importacion.archivo
    assert all(v.fecha <= HOY for v in caso.scalars(select(models.ValorIndice)))


@pytest.mark.parametrize("dia", [HOY, date(2026, 11, 30)], ids=["el-mismo-dia", "fin-de-mes"])
def test_volver_a_sembrar_las_series_en_el_mismo_mes_no_reimporta(demo, dia) -> None:
    # Dentro del mismo mes el archivo corrido es el mismo (misma huella); `--reiniciar-demo` siembra
    # además sobre una base limpia.
    caso, _ = demo
    valores = _cuantos(caso, models.ValorIndice)
    importaciones = _cuantos(caso, models.ImportacionIndice)
    assert start.sembrar_series_viales_didacticas(caso, dia) == [None, None]
    assert _cuantos(caso, models.ValorIndice) == valores
    assert _cuantos(caso, models.ImportacionIndice) == importaciones


def test_sin_los_insumos_viales_la_obra_del_generador_es_la_de_siempre() -> None:
    # RNF-15 y las pruebas de la identidad CV miden la obra de siempre: lo vial es opcional.
    base = generador.generar(12, 10, 5, semilla=7)
    vial = generador.generar(12, 10, 5, semilla=7, insumos_viales=True)
    assert base.presupuesto.total == TOTAL_SIN_VIALES
    descripciones = {
        linea.descripcion for apu in base.composiciones.values() for linea in apu.materiales
    }
    assert ASFALTO not in descripciones and GASOIL not in descripciones
    # mismas cantidades, mismas valuaciones y las otras diez composiciones idénticas
    cantidades = [(i.codigo_partida, i.cantidad) for i in base.items]
    assert [(i.codigo_partida, i.cantidad) for i in vial.items] == cantidades
    assert {c: q for c, q in cantidades if c in CANTIDADES} == CANTIDADES
    assert [v.lineas for v in vial.valuaciones] == [v.lineas for v in base.valuaciones]
    otras = [f"G-{n:04d}" for n in range(3, 13)]
    assert [vial.composiciones[c] for c in otras] == [base.composiciones[c] for c in otras]
    # G-0001 y G-0002: lo de antes más una sola línea, la del asfalto y la del gasoil
    for codigo, insumo in (("G-0001", ASFALTO), ("G-0002", GASOIL)):
        antes, ahora = base.composiciones[codigo], vial.composiciones[codigo]
        assert ahora.materiales[:-1] == antes.materiales
        assert ahora.materiales[-1].descripcion == insumo
        assert (ahora.equipos, ahora.mano_obra) == (antes.equipos, antes.mano_obra)
    # el total sube exactamente lo de las dos líneas (oráculo a mano, arriba)
    assert vial.presupuesto.total - base.presupuesto.total == INCREMENTO_VIAL
    assert vial.presupuesto.total == TOTAL_CON_VIALES
