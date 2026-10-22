"""R8 y R9 dentro de `elaborar` y tras recargar (SF-E1 con las reglas del espacio, tarea 1.6).

Solo APIs publicas. El baño de OF-001 se deriva (agua fria), se elabora con
`REGLAS + reglas_espacio(espacio)` y se guarda en un SQLite de archivo temporal; recargar con las
mismas reglas devuelve el informe emitido. Nunca se toca `data/apu.db`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy.orm import Session

from adapters.espacio import (
    Coord,
    cargar_espacio,
    crear_esquema_espacio,
    derivar,
    guardar_espacio,
)
from adapters.espacio.reglas import reglas_espacio
from aplicacion import hoja
from core.budget import cargar_elaboracion, elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.contracts import Severidad
from core.verification import REGLAS
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.base_con_pendiente import url_sqlite
from tests.fixtures.computo_auditado import items_auditados
from tests.fixtures.espacio_bano import espacio_bano

CODIGO = linea_base.CODIGO_PRESUPUESTO


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(url_sqlite(tmp_path / "espacio_reglas.db"))
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        sesion.info["proyecto"] = sembrar(sesion)
        yield sesion
    motor.dispose()


def _elaborar(sesion, espacio):
    auditados = list(items_auditados())
    items = auditados + derivar(espacio, "agua")  # las del bano quedan pendientes: no hay APU
    composiciones = Catalogo(sesion).composiciones(
        dict.fromkeys(i.codigo_partida for i in auditados), fecha=linea_base.FECHA_LINEA_BASE
    )
    return elaborar(
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=CODIGO,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
        reglas=REGLAS + reglas_espacio(espacio),
    )


def _guardar(sesion, emitido):
    guardar_presupuesto(
        sesion,
        emitido.presupuesto,
        emitido.informe,
        proyecto=sesion.info["proyecto"],
        lista=Catalogo(sesion).lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
        pendientes=emitido.pendientes,
    )
    sesion.commit()
    sesion.expunge_all()


def _recargar(sesion, **kwargs):
    return cargar_elaboracion(sesion, NOMBRE_PROYECTO, CODIGO, Catalogo(sesion), **kwargs)


def _del_espacio(informe):
    return [h for h in informe.hallazgos if h.regla in ("R8", "R9")]


def test_el_informe_del_bano_incluye_r8_y_sobrevive_a_la_recarga(sesion):
    espacio = espacio_bano()
    emitido = _elaborar(sesion, espacio)

    # el bano limpio: 5 advertencias de R8 (4 filas con supuesto + 1 sobrescritura), ningun R9
    assert [(h.regla, h.severidad) for h in _del_espacio(emitido.informe)] == [
        ("R8", Severidad.ADVERTENCIA)
    ] * 5
    assert ("R8", "Origen de la medida") in emitido.informe.reglas_evaluadas
    assert ("R9", "Coherencia espacial") in emitido.informe.reglas_evaluadas

    _guardar(sesion, emitido)
    con_reglas = _recargar(sesion, reglas=REGLAS + reglas_espacio(espacio))
    sin_reglas = _recargar(sesion)

    for informe in (con_reglas.informe, sin_reglas.informe):  # con o sin reglas: igual al emitido
        assert informe.hallazgos == emitido.informe.hallazgos
        assert informe.cumple == emitido.informe.cumple
    assert con_reglas.informe.reglas_evaluadas == emitido.informe.reglas_evaluadas


def test_un_error_de_r9_hace_que_el_informe_no_cumpla_y_se_recarga_igual(sesion):
    espacio = espacio_bano()
    p1 = espacio.puntos[0]
    fuera = replace(p1, posicion=Coord(p1.posicion.x + 10, p1.posicion.y, p1.posicion.z))
    espacio = replace(espacio, puntos=(fuera, *espacio.puntos[1:]))
    emitido = _elaborar(sesion, espacio)

    assert [h.origen_ids for h in emitido.informe.hallazgos if h.regla == "R9"] == [
        ("esp_puntos:P1",)
    ]
    assert not emitido.informe.cumple

    _guardar(sesion, emitido)
    recargado = _recargar(sesion, reglas=REGLAS + reglas_espacio(espacio))
    assert recargado.informe.hallazgos == emitido.informe.hallazgos
    assert not recargado.informe.cumple


# --- RF-44 / UC-13a: la fila sin origen de medida se acepta y R8 la marca ERROR ------------------


def test_fila_sin_origen_de_medida_de_la_hoja_a_la_recarga_extremo_a_extremo(tmp_path):
    """Hoja (filas de texto) -> borrador -> base -> elaborar -> informe -> recarga, sin mutar nada.

    Un supuesto sin motivo, un punto con `origen_id` vacio y un ambiente que cita un origen que no
    existe: la hoja los deja pasar, se guardan y se recargan iguales, y R8 los marca ERROR (el
    informe no cumple); el resto del baño sigue limpio.
    """
    motor = crear_motor(url_sqlite(tmp_path / "hoja_sin_origen.db"))
    crear_esquema_espacio(motor)
    base = espacio_bano()
    filas = hoja.filas_desde_espacio(base)
    filas["origenes"][0]["referencia"] = ""  # supuesto sin motivo
    filas["puntos"][0]["origen_id"] = ""  # P1 sin origen
    filas["ambientes"][0]["origen_id"] = "FANTASMA"  # origen que no esta registrado
    borrador = hoja.espacio_desde_filas(filas, base=base)

    with Session(motor) as sesion:
        guardar_espacio(sesion, 1, borrador)
        sesion.commit()
    with Session(motor) as sesion:
        recargado = cargar_espacio(sesion, 1)
    assert recargado == borrador

    resultado = hoja.elaborar_hoja(recargado, {}, codigo="OF-001", fecha=date(2026, 10, 5))
    errores = [h for h in resultado.elaboracion.informe.hallazgos if h.severidad is Severidad.ERROR]
    assert {h.origen_ids for h in errores if h.regla == "R8"} == {
        ("esp_ambientes:BAN-01",),
        ("esp_fuentes:F1",),
        ("esp_puntos:P1",),
        ("esp_puntos:P2",),
    }
    assert not resultado.elaboracion.informe.cumple
    assert resultado.estado["esp_puntos:P1"].severidad is Severidad.ERROR
    assert "origen no registrado" in resultado.estado["esp_puntos:P1"].texto
    assert "origen no registrado" in resultado.estado["esp_ambientes:BAN-01"].texto
    assert "origen sin referencia" in resultado.estado["esp_puntos:P2"].texto
    motor.dispose()
