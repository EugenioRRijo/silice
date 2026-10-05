"""Persistencia `esp_*` con clave de versión (spec §6.2). Siempre SQLite en archivo temporal."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal as D

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from adapters.espacio import (
    Ambiente,
    Circuito,
    Coord,
    Especialidad,
    Espacio,
    OrigenMedida,
    Punto,
    SuperficiePunto,
    TipoOrigen,
    TipoPunto,
    cargar_espacio,
    crear_esquema_espacio,
    guardar_espacio,
)
from tests.fixtures.espacio_bano import espacio_bano

TABLAS = {
    "esp_ambientes",
    "esp_fuentes",
    "esp_circuitos",
    "esp_puntos",
    "esp_recorridos",
    "esp_tramos",
    "esp_sobrescrituras",
    "esp_origenes",
}


@pytest.fixture
def motor(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'espacio.db'}")
    crear_esquema_espacio(engine)
    yield engine
    engine.dispose()


def test_el_esquema_crea_las_tablas_esp_con_clave_de_version(motor):
    insp = inspect(motor)
    assert TABLAS <= set(insp.get_table_names())
    for tabla in TABLAS:
        columnas = {c["name"] for c in insp.get_columns(tabla)}
        assert "version_id" in columnas, tabla
        assert "version_id" in insp.get_pk_constraint(tabla)["constrained_columns"], tabla


def test_crear_el_esquema_dos_veces_es_inocuo(motor):
    crear_esquema_espacio(motor)
    crear_esquema_espacio(motor)


def test_ida_y_vuelta_es_identica(motor):
    original = espacio_bano()
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, original)
        sesion.commit()
    with Session(motor) as sesion:
        recargado = cargar_espacio(sesion, 1)
    assert recargado == original
    assert all(isinstance(p.posicion.x, D) for p in recargado.puntos)


def test_ida_y_vuelta_con_circuito_y_precision_decimal(motor):
    base = espacio_bano()
    punto = Punto(
        id="T1",
        nombre="tomacorriente",
        especialidad=Especialidad.ELECTRICIDAD,
        tipo=TipoPunto.TOMACORRIENTE,
        ambiente_id="BAN-01",
        superficie=SuperficiePunto.PARED,
        posicion=Coord(D("0.1234567890123456789"), D("0"), D("0.4")),
        circuito_id="C1",
        especificaciones={"calibre": "12 AWG"},
        origen_id="O1",
    )
    circuito = Circuito(
        id="C1",
        tablero="TAB",
        numero=1,
        conductores=(1, 1, 1),
        calibre="12 AWG",
        puntos_maximos=8,
        orden=("T1",),
    )
    original = replace(base, puntos=base.puntos + (punto,), circuitos=(circuito,))
    with Session(motor) as sesion:
        guardar_espacio(sesion, 7, original)
        sesion.commit()
    with Session(motor) as sesion:
        assert cargar_espacio(sesion, 7) == original


def test_versiones_independientes(motor):
    uno = espacio_bano()
    dos = replace(uno, ambientes=(replace(uno.ambientes[0], alto=D("2.700")),))
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, uno)
        guardar_espacio(sesion, 2, dos)
        sesion.commit()
    with Session(motor) as sesion:
        assert cargar_espacio(sesion, 1) == uno
        assert cargar_espacio(sesion, 2) == dos
        assert cargar_espacio(sesion, 1) != cargar_espacio(sesion, 2)


def test_guardar_dos_veces_la_misma_version_reemplaza_y_no_duplica(motor):
    original = espacio_bano()
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, original)
        guardar_espacio(sesion, 1, original)
        sesion.commit()
    with Session(motor) as sesion:
        assert cargar_espacio(sesion, 1) == original
        n = sesion.execute(text("SELECT COUNT(*) FROM esp_puntos")).scalar()
    assert n == 2


def test_guardar_otro_espacio_en_la_misma_version_reemplaza_al_anterior(motor):
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, espacio_bano())
        guardar_espacio(sesion, 1, Espacio())
        sesion.commit()
    with Session(motor) as sesion:
        assert cargar_espacio(sesion, 1) == Espacio()


def test_version_sin_espacio_carga_vacio(motor):
    with Session(motor) as sesion:
        assert cargar_espacio(sesion, 99) == Espacio()


def test_sin_commit_no_queda_nada(motor):
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, espacio_bano())
        sesion.rollback()
    with Session(motor) as sesion:
        assert cargar_espacio(sesion, 1).vacio


def test_las_dimensiones_se_guardan_como_texto_decimal_exacto(motor):
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, espacio_bano())
        sesion.commit()
        valor = sesion.execute(text("SELECT typeof(largo), largo FROM esp_ambientes")).one()
    assert valor[0] == "text"
    assert D(valor[1]) == D("2.000")


def test_filas_de_la_misma_clave_en_otra_version_no_se_mezclan(motor):
    otro_origen = OrigenMedida(
        id="O1",
        tipo=TipoOrigen.LEVANTAMIENTO,
        referencia={"fecha": "2026-10-05", "responsable": "Ana"},
    )
    uno = espacio_bano()
    dos = Espacio(
        origenes=(otro_origen,),
        ambientes=(
            Ambiente(
                id="BAN-01",
                nombre="Otro",
                x0=D("0"),
                y0=D("0"),
                largo=D("1"),
                ancho=D("1"),
                alto=D("2"),
                origen_id="O1",
            ),
        ),
    )
    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, uno)
        guardar_espacio(sesion, 2, dos)
        sesion.commit()
    with Session(motor) as sesion:
        assert cargar_espacio(sesion, 2) == dos
        assert cargar_espacio(sesion, 1) == uno


def test_la_prueba_usa_un_archivo_temporal_y_no_data_apu_db(motor, tmp_path):
    assert motor.url.database is not None
    assert str(tmp_path) in motor.url.database
    assert not motor.url.database.replace("\\", "/").endswith("data/apu.db")
