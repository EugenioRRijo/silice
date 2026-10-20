"""AppTest de la pantalla «Reajuste de precios» (UC-18, S1, Tarea 13).

AppTest no escribe en `st.data_editor`: la clausula con sus componentes y los periodos se
prueban en `test_ui_reajuste.py`; aqui se prueba que la pantalla arranca, que dice que hacer sin
proyecto o con la clausula incompleta, y que pinta y guarda un calculo ya hecho.
"""

from __future__ import annotations

import importlib
from datetime import date
from pathlib import Path

from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from tests.fixtures.reajuste_pantalla import CAMPOS, COMPONENTES, EJECUTADO, PERIODOS
from tests.fixtures.reajuste_s1 import NOMBRE, sembrar
from ui import reajuste
from ui.caso import CLAVE_PROYECTO
from ui.paginas.reajuste import CLAVE_CALCULO

SCRIPT = "from ui.paginas.reajuste import render\nrender()\n"


def _base(tmp_path: Path) -> Path:
    ruta = tmp_path / "reajuste.db"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        sembrar(sesion)
        sesion.commit()
    motor.dispose()
    return ruta


def _abrir(monkeypatch, tmp_path: Path, *, proyecto: str | None = NOMBRE) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "reajuste.db"))
    _base(tmp_path)
    at = AppTest.from_string(SCRIPT, default_timeout=90)
    if proyecto is not None:
        at.session_state[CLAVE_PROYECTO] = proyecto
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_sin_proyecto_abierto_dice_que_hacer(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path, proyecto=None)
    assert any("Abra un proyecto" in i.value for i in at.info)


def test_arranca_con_su_clausula_y_sus_periodos(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path)
    assert not at.error
    subtitulos = [s.value for s in at.subheader]
    assert any(s.startswith("1. La clausula") for s in subtitulos)
    assert any(s.startswith("2. Periodos") for s in subtitulos)
    assert [b.label for b in at.button] == ["Calcular"]


def test_calcular_con_la_clausula_vacia_dice_que_campo_falta(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path)
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    mensajes = [e.value for e in at.error]
    assert any("Duración" in m and "entero" in m for m in mensajes), mensajes
    assert CLAVE_CALCULO not in at.session_state


def test_un_calculo_hecho_se_pinta_lado_a_lado_y_se_guarda(monkeypatch, tmp_path):
    at = _abrir(monkeypatch, tmp_path)
    clausula = reajuste.clausula_desde_textos(CAMPOS, COMPONENTES)
    periodos = reajuste.periodos_desde_filas(PERIODOS, EJECUTADO)
    motor = crear_motor(f"sqlite:///{(tmp_path / 'reajuste.db').as_posix()}")
    with abrir_sesion(motor) as sesion:
        resultado = reajuste.calcular(
            sesion, NOMBRE, "001", clausula, periodos, fecha_calculo=date(2027, 3, 5)
        )
    motor.dispose()
    at.session_state[CLAVE_CALCULO] = ("001", clausula, periodos, resultado)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    tabla = next(d.value for d in at.dataframe if "Escalatoria" in d.value.columns)
    assert tabla.iloc[0]["Escalatoria"] == "15300.00"
    assert tabla.iloc[0]["Comprobación"] == "16000.00"
    at.text_input(key="reajuste_fuente").set_value("estudio de prueba")
    at.text_input(key="reajuste_responsable").set_value("Ing. Prueba")
    next(b for b in at.button if b.label == "Guardar estudio").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("guardado" in s.value for s in at.success)
    motor = crear_motor(f"sqlite:///{(tmp_path / 'reajuste.db').as_posix()}")
    with abrir_sesion(motor) as sesion:
        assert len(sesion.scalars(select(models.EstudioReajuste)).all()) == 1
    motor.dispose()
