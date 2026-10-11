"""Persistencia `esp_*` con clave de versión (spec §6.2). Siempre SQLite en archivo temporal."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from adapters.espacio import (
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Especialidad,
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

D = Decimal

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


def test_fr5_cargar_en_una_base_sin_tablas_esp_devuelve_vacio_y_no_escribe(tmp_path):
    """Una base de clinica o TI-001 no tiene esp_*: cargar no falla, no crea tablas ni escribe."""
    motor = create_engine(f"sqlite:///{tmp_path / 'sin_esp.db'}")
    try:
        with motor.begin() as con:
            con.execute(text("CREATE TABLE otra (x INTEGER)"))
        with Session(motor) as sesion:
            assert cargar_espacio(sesion, 1) == Espacio()
        assert not any(t.startswith("esp_") for t in inspect(motor).get_table_names())
    finally:
        motor.dispose()


def test_cargar_con_el_esquema_a_medias_tambien_devuelve_vacio(tmp_path):
    motor = create_engine(f"sqlite:///{tmp_path / 'medias.db'}")
    try:
        with motor.begin() as con:
            con.execute(text("CREATE TABLE esp_ambientes (version_id INTEGER, id TEXT)"))
        with Session(motor) as sesion:
            assert cargar_espacio(sesion, 1) == Espacio()
    finally:
        motor.dispose()


def test_ida_y_vuelta_de_of001_completa_con_recorrido_de_circuito(motor):
    """SF2: la oficina con las tres especialidades, un circuito con orden y un recorrido declarado
    de circuito, se guarda y se recarga identica; la derivacion no cambia con la recarga."""
    from adapters.espacio import ModoRecorrido, Recorrido, Tramo, derivar
    from tests.fixtures.espacio_of001 import espacio_of001

    base = espacio_of001()
    tramo = Tramo(
        orden=1,
        superficie="pared",
        vertices=(Coord(D("4"), D("1"), D("1.5")), Coord(D("4"), D("1"), D("2.5"))),
        empotrado=True,
    )
    original = replace(
        base,
        recorridos=(
            Recorrido(id="R-C2", circuito_id="C2", modo=ModoRecorrido.DECLARADO, tramos=(tramo,)),
        ),
    )
    with Session(motor) as sesion:
        guardar_espacio(sesion, 3, original)
        sesion.commit()
    with Session(motor) as sesion:
        recargado = cargar_espacio(sesion, 3)
    assert recargado == original
    assert recargado.circuitos[0].orden == ("TA1", "TA2", "TB1", "TB2")
    for especialidad in ("agua", "datos", "electricidad"):
        assert derivar(recargado, especialidad) == derivar(original, especialidad)


def test_el_esquema_se_crea_dentro_de_la_transaccion_de_una_sesion_con_escrituras(tmp_path):
    """SF3: la hoja guarda la version y sus filas esp_* en UNA sesion; las tablas se aseguran con
    la conexion de la sesion (una segunda conexion chocaria con su escritura: base bloqueada)."""
    motor = create_engine(f"sqlite:///{tmp_path / 'una_sesion.db'}", connect_args={"timeout": 0.2})
    try:
        with Session(motor) as sesion:
            sesion.execute(text("CREATE TABLE otra (x INTEGER)"))
            sesion.execute(text("INSERT INTO otra VALUES (1)"))  # la sesion ya escribe
            crear_esquema_espacio(sesion.connection())
            guardar_espacio(sesion, 5, espacio_bano())
            sesion.commit()
        with Session(motor) as sesion:
            assert cargar_espacio(sesion, 5) == espacio_bano()
    finally:
        motor.dispose()
