"""Pantalla «Hoja del proyecto» con un proyecto NUEVO, sin versiones (RI-7 de la integracion final).

`AppTest` no escribe en `st.data_editor`: el borrador se siembra en `st.session_state` con el mismo
camino que sigue la pantalla despues de leer el editor. Se prueba el aviso «Este proyecto aun no
tiene versiones», el formulario (fuente, responsable y Guardar primera version), el efecto en la
base y que la hoja abra la version creada. Lo que solo se ve en un navegador (escribir en una
celda) queda para la prueba manual CP-08 del guion.
"""

from __future__ import annotations

import importlib
import shutil
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from streamlit.testing.v1 import AppTest

from core import models
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from tests.fixtures import caso_of001
from tests.fixtures.espacio_bano import espacio_bano
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from ui import hoja
from ui.paginas.hoja import (
    CLAVE_ABIERTA,
    CLAVE_BORRADOR,
    CLAVE_FUENTE,
    CLAVE_PARTIDA,
    CLAVE_PESTANA,
    CLAVE_PROYECTO,
    CLAVE_RESPONSABLE,
    PESTANAS,
    SIN_PROYECTO,
)

SCRIPT = "from ui.paginas.hoja import render\nrender()\n"
D = Decimal
NUEVO = "Proyecto nuevo: bano"
GUARDAR = "Guardar primera versión"
AVISO = "Este proyecto aún no tiene versiones"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("ui_primera") / "of001.db")


@pytest.fixture
def base(_plantilla, tmp_path):
    copia = tmp_path / "caso.db"
    shutil.copy(_plantilla, copia)
    motor = crear_motor(f"sqlite:///{copia.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            crear_proyecto(sesion, NUEVO)
            sesion.commit()
    finally:
        motor.dispose()
    return copia


def _arrancar(monkeypatch, base: Path, borrador=None, **estado) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    if borrador is not None:
        at.session_state[CLAVE_BORRADOR] = borrador
        at.session_state[CLAVE_PARTIDA] = borrador
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _abierta(at: AppTest):
    try:
        return at.session_state[CLAVE_ABIERTA]
    except KeyError:
        return None


def _sembrar(at: AppTest, borrador: hoja.Borrador) -> AppTest:
    at.session_state[CLAVE_BORRADOR] = borrador
    at.session_state[CLAVE_PARTIDA] = borrador
    return at.run()


def _borrador(espacio) -> hoja.Borrador:
    return hoja.Borrador(fecha=caso_of001.FECHA, moneda=caso_of001.MONEDA, espacio=espacio)


def _boton(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def _contar(base: Path, entidad) -> int:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return sesion.scalar(select(func.count()).select_from(entidad))
    finally:
        motor.dispose()


def _llenar(at: AppTest, fuente="ficha del bano, acta 3", responsable="Ing. Prueba") -> AppTest:
    at.text_input(key=CLAVE_FUENTE).set_value(fuente)
    at.text_input(key=CLAVE_RESPONSABLE).set_value(responsable)
    at.run()
    return at


# --- el aviso y el formulario ---------------------------------------------------------------------


def test_un_proyecto_sin_versiones_lo_dice_y_ofrece_guardar_la_primera(monkeypatch, base):
    at = _arrancar(monkeypatch, base, **{CLAVE_PROYECTO: NUEVO})

    assert any(AVISO in i.value for i in at.info)
    assert _abierta(at) is None
    assert {b.label for b in at.button} >= {GUARDAR}
    assert [b for b in at.button if b.label == "Guardar version"] == []  # no se ofrecen los dos
    assert at.text_input(key=CLAVE_FUENTE) is not None
    assert at.text_input(key=CLAVE_RESPONSABLE) is not None


@pytest.mark.parametrize("pestana", PESTANAS)
def test_cada_pestana_arranca_con_un_proyecto_sin_versiones(monkeypatch, base, pestana):
    at = _arrancar(
        monkeypatch,
        base,
        _borrador(espacio_bano()),
        **{CLAVE_PROYECTO: NUEVO, CLAVE_PESTANA: pestana},
    )

    assert not at.exception and not at.error, [e.value for e in at.error]


def test_con_la_hoja_vacia_el_boton_esta_deshabilitado_y_dice_por_que(monkeypatch, base):
    at = _arrancar(monkeypatch, base, **{CLAVE_PROYECTO: NUEVO})
    _llenar(at)

    guardar = _boton(at, GUARDAR)
    assert guardar.disabled
    assert "vacia" in guardar.help


def test_sin_fuente_o_sin_responsable_el_boton_dice_cual_falta(monkeypatch, base):
    at = _arrancar(monkeypatch, base, _borrador(espacio_bano()), **{CLAVE_PROYECTO: NUEVO})
    assert _boton(at, GUARDAR).disabled and "fuente" in _boton(at, GUARDAR).help.lower()

    _llenar(at, fuente="acta 3", responsable="")
    assert _boton(at, GUARDAR).disabled and "responsable" in _boton(at, GUARDAR).help.lower()

    _llenar(at)
    assert not _boton(at, GUARDAR).disabled


def test_sin_proyecto_elegido_no_se_puede_guardar_y_dice_que_hacer(monkeypatch, base):
    at = _arrancar(monkeypatch, base, _borrador(espacio_bano()), **{CLAVE_PROYECTO: SIN_PROYECTO})

    guardar = _boton(at, "Guardar version")
    assert guardar.disabled
    assert "proyecto" in guardar.help.lower()
    assert not [i for i in at.info if AVISO in i.value]


# --- guardar --------------------------------------------------------------------------------------


def test_guardar_la_primera_version_crea_la_001_y_la_hoja_la_abre(monkeypatch, base):
    at = _arrancar(monkeypatch, base, _borrador(espacio_of001()), **{CLAVE_PROYECTO: NUEVO})
    _llenar(at)
    versiones, registros = _contar(base, models.Presupuesto), _contar(base, models.RegistroCambio)

    _boton(at, GUARDAR).click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("Se guardo la primera version 001" in s.value for s in at.success)
    assert _contar(base, models.Presupuesto) == versiones + 1
    assert _contar(base, models.RegistroCambio) == registros + 1
    abierta = at.session_state[CLAVE_ABIERTA]
    assert (abierta.proyecto, abierta.codigo) == (NUEVO, "001")
    assert abierta.borrador.espacio == espacio_of001()
    # los parametros por defecto del contrato (no los de OF-001): el 2577.59 del guion (CP-09)
    assert abs(abierta.guardada.presupuesto.total - D("2577.59")) <= D("0.01")
    assert not [i for i in at.info if AVISO in i.value]  # ya tiene version
    assert not at.warning  # nada sin guardar
    # ahora el flujo es el normal: Guardar version, no Guardar primera version
    assert [b for b in at.button if b.label == GUARDAR] == []
    assert _boton(at, "Guardar version").disabled  # sin cambios nuevos


def test_despues_de_la_primera_editar_y_guardar_produce_la_002(monkeypatch, base):
    at = _arrancar(monkeypatch, base, _borrador(espacio_of001()), **{CLAVE_PROYECTO: NUEVO})
    _llenar(at)
    _boton(at, GUARDAR).click().run()
    borrador = at.session_state[CLAVE_BORRADOR]
    editado = replace(borrador, parametros=replace(borrador.parametros, fcas=D("7")))
    at.session_state[CLAVE_BORRADOR] = editado
    at.session_state[CLAVE_PARTIDA] = editado
    at.run()
    _llenar(at, fuente="la convencion fija el FCAS")

    _boton(at, "Guardar version").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("Se guardo la version 002 con 1 cambios" in s.value for s in at.success)
    assert at.session_state[CLAVE_ABIERTA].codigo == "002"


def test_un_guardado_que_falla_dice_que_paso_y_no_deja_nada(monkeypatch, base):
    at = _arrancar(monkeypatch, base, _borrador(espacio_of001()), **{CLAVE_PROYECTO: NUEVO})
    _llenar(at)
    # la fecha del borrador queda antes de toda lista de precios: el catalogo no tiene vigente
    sin_lista = replace(at.session_state[CLAVE_BORRADOR], fecha=date(2000, 1, 1))
    at.session_state[CLAVE_BORRADOR] = sin_lista
    at.session_state[CLAVE_PARTIDA] = sin_lista
    at.run()
    versiones = _contar(base, models.Presupuesto)

    _boton(at, GUARDAR).click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("lista de precios" in e.value for e in at.error)
    assert _contar(base, models.Presupuesto) == versiones
    assert _abierta(at) is None
    assert at.session_state[CLAVE_BORRADOR] == sin_lista  # el borrador se conserva


def test_el_borrador_describido_sin_proyecto_sobrevive_al_elegir_un_proyecto_nuevo(
    monkeypatch, base
):
    """CP-08: se describe el bano y despues se abre/crea el proyecto en la barra."""
    at = _arrancar(monkeypatch, base, **{CLAVE_PROYECTO: SIN_PROYECTO})
    _sembrar(at, _borrador(espacio_bano()))
    proyecto = next(s for s in at.selectbox if s.label == "Proyecto")
    assert NOMBRE_OF001 in proyecto.options and NUEVO in proyecto.options

    proyecto.select(NUEVO).run()

    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[CLAVE_BORRADOR].espacio == espacio_bano()
    assert any(AVISO in i.value for i in at.info)
    _llenar(at)
    _boton(at, GUARDAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[CLAVE_ABIERTA].codigo == "001"
