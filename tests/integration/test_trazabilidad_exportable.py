"""SF-E2 + SF-E4: los `RegistroCambio` de una version como hoja Trazabilidad del Excel (spec 9.5).

Oraculo: los valores con que se guardo la edicion (`tests/fixtures/versiones.py`) y el libro
releido.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from openpyxl import load_workbook

from core.budget import plan_secuencial
from core.budget.edicion import guardar_edicion, tabla_trazabilidad
from core.budget.excel import COLUMNAS_TRAZABILIDAD, exportar_hoja
from core.budget.instantanea import composiciones_de_presupuesto
from core.budget.persistencia import _buscar
from core.catalog import Catalogo
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.versiones import (
    CAMBIO_CEMENTO,
    CODIGO_CONCRETO,
    FUENTE,
    RESPONSABLE,
    con_cemento,
    elaborar_001,
    elaborar_editada,
    guardar_001,
)

AHORA = datetime(2026, 10, 5, 9, 30, 15)


@pytest.fixture
def version_002(sesion):
    guardar_001(sesion, sembrar(sesion), elaborar_001(sesion))
    sesion.commit()
    composiciones = composiciones_de_presupuesto(sesion, NOMBRE_PROYECTO, "001", Catalogo(sesion))
    composiciones[CODIGO_CONCRETO] = con_cemento(composiciones[CODIGO_CONCRETO])
    editada = elaborar_editada(sesion, composiciones, "002", plan_secuencial)
    nueva = guardar_edicion(
        sesion,
        NOMBRE_PROYECTO,
        "001",
        editada,
        linea_base.PARAMETROS_LINEA_BASE,
        [CAMBIO_CEMENTO],
        fuente=FUENTE,
        responsable=RESPONSABLE,
        ahora=AHORA,
    )
    sesion.commit()
    return editada, nueva


def test_la_tabla_de_trazabilidad_lleva_los_codigos_de_version_y_todos_los_campos(
    sesion, version_002
):
    _, nueva = version_002

    tabla = tabla_trazabilidad(sesion, nueva)

    assert tabla.titulo == "Trazabilidad"
    assert tabla.columnas == COLUMNAS_TRAZABILIDAD
    assert tabla.filas == (
        (
            "001",
            "002",
            "apu",
            CAMBIO_CEMENTO.clave,
            "cantidad",
            "7.5",
            "9",
            FUENTE,
            RESPONSABLE,
            AHORA,
        ),
    )


def test_la_hoja_trazabilidad_del_libro_muestra_el_registro_de_la_version(
    sesion, version_002, tmp_path
):
    editada, nueva = version_002

    ruta = exportar_hoja(
        editada.presupuesto,
        editada.informe,
        tmp_path / "t.xlsx",
        linea_base.PARAMETROS_LINEA_BASE,
        trazabilidad=tabla_trazabilidad(sesion, nueva),
    )

    hoja = load_workbook(ruta)["Trazabilidad"]
    assert [c.value for c in hoja[1]] == list(COLUMNAS_TRAZABILIDAD)
    fila = [c.value for c in hoja[2]]
    assert fila[:9] == [
        "001",
        "002",
        "apu",
        CAMBIO_CEMENTO.clave,
        "cantidad",
        "7.5",
        "9",
        FUENTE,
        RESPONSABLE,
    ]
    assert fila[9] == AHORA


def test_una_version_sin_registros_da_una_tabla_vacia(sesion):
    guardar_001(sesion, sembrar(sesion), elaborar_001(sesion))
    sesion.commit()

    tabla = tabla_trazabilidad(sesion, _buscar(sesion, NOMBRE_PROYECTO, "001"))

    assert tabla.filas == ()
