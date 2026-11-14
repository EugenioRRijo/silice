"""F5 vial, tarea 2: VR4 con el transporte medido por banda de distancia.

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §5 (punto 2) y la
decisión provisional 2 del 2026-11-06 (fuera de la banda es ADVERTENCIA). Datos FICTICIOS; el
ejemplo es el del diseño. Oráculos a mano:

Tramo B1, de 0 a 1 km (1.000 m), ancho 5 m, carpeta e = 0,01 m y d = 2,4 t/m³: 1.000 × 5 × 0,01 =
50 m³; 50 × 2,4 = 120 t. La obra mide el transporte en t por banda: la partida en t vale 120 t,
no 120 × 9 = 1.080 t·km. La banda «8-10» es «más de 8 km y hasta 10 km»: 9 km cae dentro, 12 km y
8 km caen fuera.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, select

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Capa, Tramo
from adapters.vial.reglas import ESPEC_BANDA_KM, auditar_vial
from adapters.vial.tabular import leer_tramos
from api.esquemas_vial import TramoEntrada, a_tramos, tramo_a_respuesta
from aplicacion import vial
from core import models
from core.catalog import abrir_sesion, crear_motor
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, ResultadoAPU
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Severidad
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import sembrar_vivienda

D = Decimal
CAPA = "tramo:B1:capa:1"
BANDA = PARTIDAS_VIALES["transporte_mezcla_banda"][0]


def _tramo(distancia: str | None = "9", transporte: str | None = "banda") -> Tramo:
    return Tramo(
        "B1",
        D("0"),
        D("1"),
        D("5"),
        (Capa("carpeta", D("0.01"), D("2.4"), None),),
        distancia_planta_km=None if distancia is None else D(distancia),
        transporte=transporte,
    )


def _presupuesto(*items: ItemComputo) -> Presupuesto:
    cero = D("0")
    partidas = [
        PartidaPresupuestada(
            i,
            ComposicionAPU(i.codigo_partida, i.descripcion, i.unidad, D("1")),
            ResultadoAPU(cero, cero, cero, cero, cero, D("1")),
        )
        for i in items
    ]
    return Presupuesto("VIA-TEST", date(2026, 11, 6), "Bs", tuple(partidas))


def _transporte(cantidad: str = "120", banda: str | None = "8-10") -> ItemComputo:
    return ItemComputo(
        BANDA,
        "Transporte de mezcla, mayor de 8 km y hasta 10 km",
        "t",
        D(cantidad),
        CAPA,
        OrigenTipo.MANUAL,
        Dominio.CIVIL,
        especificaciones={} if banda is None else {ESPEC_BANDA_KM: banda},
    )


def _vr4(tramo: Tramo, item: ItemComputo) -> list[tuple[Severidad, str]]:
    return [
        (h.severidad, h.descripcion)
        for h in auditar_vial([tramo], _presupuesto(item))
        if h.regla == "VR4"
    ]


def test_la_partida_por_banda_va_en_toneladas_con_codigo_correlativo():
    assert PARTIDAS_VIALES["transporte_mezcla_banda"] == (
        "C-000.000.024",
        "Transporte de mezcla asfáltica desde la planta, por banda de distancia",
        "t",
    )


def test_con_banda_el_tramo_deriva_toneladas_y_no_t_km():
    items = derivar_tramos([_tramo()])
    transporte = [i for i in items if "transporte" in i.descripcion.casefold()]
    assert [(i.codigo_partida, i.unidad, i.cantidad) for i in transporte] == [
        (BANDA, "t", D("120"))
    ]
    assert transporte[0].regla == "longitud*ancho*espesor*densidad"


def test_con_banda_y_sin_distancia_tambien_deriva_las_toneladas():
    items = derivar_tramos([_tramo(distancia=None)])
    assert [(i.codigo_partida, i.cantidad) for i in items if i.codigo_partida == BANDA] == [
        (BANDA, D("120"))
    ]


def test_la_convencion_de_siempre_es_t_km_y_se_guarda_vacia():
    assert _tramo(transporte="t·km") == _tramo(transporte=None)
    t_km = PARTIDAS_VIALES["transporte_mezcla"][0]
    items = derivar_tramos([_tramo(transporte=None)])
    assert [
        (i.codigo_partida, i.cantidad) for i in items if "transporte" in i.descripcion.casefold()
    ] == [(t_km, D("1080"))]
    with pytest.raises(ValueError, match="transporte"):
        _tramo(transporte="km")


def test_vr4_por_banda_sin_hallazgo_si_las_toneladas_y_la_banda_cuadran():
    assert _vr4(_tramo(), _transporte()) == []


def test_vr4_por_banda_error_si_las_toneladas_no_cuadran():
    assert _vr4(_tramo(), _transporte("130")) == [
        (
            Severidad.ERROR,
            "transporte por banda de tramo:B1:capa:1: 130 t en el presupuesto y 120 t por "
            "longitud*ancho*espesor*densidad (tolerancia 0,5 %)",
        )
    ]


@pytest.mark.parametrize("distancia", ["12", "8"])
def test_vr4_por_banda_advertencia_si_la_distancia_cae_fuera(distancia: str):
    assert _vr4(_tramo(distancia), _transporte()) == [
        (
            Severidad.ADVERTENCIA,
            f"tramo:B1:capa:1: el tramo está a {distancia} km de la planta y la partida {BANDA} "
            "cobra la banda de más de 8 km y hasta 10 km",
        )
    ]


def test_vr4_por_banda_lee_la_coma_decimal():
    assert _vr4(_tramo("9.5"), _transporte(banda="8,5-10")) == []


def test_vr4_por_banda_info_si_la_partida_no_dice_su_banda():
    # prueba de punta a punta del 2026-11-13, D3: sin lector de la descripción el mensaje ya no
    # dice que la descripción «no dice la banda» (la descripción dice «mayor de 8 km y hasta 10
    # km»); con lector, `test_vial_banda_descripcion.py`
    assert _vr4(_tramo(), _transporte(banda=None)) == [
        (
            Severidad.INFO,
            f"tramo:B1:capa:1: transporte por banda no evaluable: la partida {BANDA} no declara "
            "su banda de distancia y esta revisión no lee su descripción",
        )
    ]


def test_vr4_por_banda_info_si_el_tramo_no_dice_su_distancia():
    assert _vr4(_tramo(distancia=None), _transporte()) == [
        (
            Severidad.INFO,
            "tramo:B1:capa:1: la banda de más de 8 km y hasta 10 km no se compara: el tramo no "
            "declara la distancia a la planta",
        )
    ]


@pytest.mark.parametrize("banda", ["8 a 10", "10-8", "-10", "8-"])
def test_vr4_por_banda_advertencia_si_la_banda_no_se_entiende(banda: str):
    assert _vr4(_tramo(), _transporte(banda=banda)) == [
        (
            Severidad.ADVERTENCIA,
            f"tramo:B1:capa:1: la banda de distancia {banda!r} de la partida {BANDA} no se "
            "entiende: escríbala «mínimo-máximo» en km, con el mínimo menor que el máximo",
        )
    ]


def test_vr7_marca_t_km_en_un_tramo_por_banda():
    t_km = replace(
        _transporte(), codigo_partida=PARTIDAS_VIALES["transporte_mezcla"][0], unidad="t·km"
    )
    hallazgos = auditar_vial([_tramo()], _presupuesto(t_km))
    assert [(h.regla, h.severidad) for h in hallazgos] == [("VR7", Severidad.ERROR)]


# --- CSV, guardado, API ---------------------------------------------------------------------------


def test_el_csv_lee_la_convencion_del_tramo(tmp_path: Path):
    ruta = tmp_path / "via.csv"
    ruta.write_text(
        "tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;"
        "espesor_m;densidad_t_m3;dosis_l_m2;lineas;transporte\n"
        "B1;0;1;5;9;capa;carpeta;0,01;2,4;;;banda\n",
        encoding="utf-8",
    )
    assert leer_tramos(ruta) == [_tramo()]


def test_el_csv_rechaza_una_convencion_desconocida(tmp_path: Path):
    ruta = tmp_path / "via.csv"
    ruta.write_text(
        "tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;"
        "espesor_m;densidad_t_m3;dosis_l_m2;lineas;transporte\n"
        "B1;0;1;5;9;capa;carpeta;0,01;2,4;;;por viaje\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"fila 2\b.*transporte"):
        leer_tramos(ruta)


@pytest.fixture
def motor(tmp_path: Path) -> Iterator[Engine]:
    ruta = tmp_path / "caso.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            sembrar_vivienda(s, usuario="Ana <ana>")
        yield motor
    finally:
        motor.dispose()


def test_la_migracion_agrega_la_columna_del_transporte(motor: Engine):
    with closing(sqlite3.connect(motor.url.database)) as conexion:
        columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(vial_tramo)")}
    assert "transporte" in columnas


def test_lo_guardado_se_lee_igual(motor: Engine):
    with abrir_sesion(motor) as sesion:
        version = sesion.scalars(
            select(models.Presupuesto.id).where(models.Presupuesto.codigo == "VIV-001")
        ).one()
        tramos = [_tramo(), replace(_tramo(transporte=None), id="B2")]
        vial.guardar_tramos(
            sesion, version, tramos, usuario="Ana <ana>", ahora=datetime(2026, 11, 6)
        )
        assert vial.tramos_de_version(sesion, version) == tramos


def test_la_api_recibe_y_devuelve_la_convencion():
    respuesta = tramo_a_respuesta(_tramo())
    assert respuesta.transporte == "banda"
    assert tramo_a_respuesta(_tramo(transporte=None)).transporte is None
    assert a_tramos([TramoEntrada.model_validate(respuesta.model_dump())]) == [_tramo()]
