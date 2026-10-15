"""La casilla «Tomar lo ejecutado de las valuaciones» de la pantalla de reajuste (UC-18 enmendado
por S2, RF-72): marcada, la tabla de lo ejecutado a mano desaparece y la pantalla avisa de dónde
sale lo ejecutado. `st.data_editor` no se teclea desde `AppTest`; el cálculo y el guardado con
valuaciones se prueban en `tests/integration/test_ui_reajuste_valuaciones.py`."""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from ui.caso import CLAVE_PROYECTO
from ui.paginas.reajuste import CLAVE_VALUACIONES

SCRIPT = "from ui.paginas.reajuste import render\n\nrender()\n"


def _pantalla(monkeypatch, tmp_path: Path, *, con_valuaciones: bool) -> AppTest:
    tmp_path.mkdir(exist_ok=True)
    ruta = tmp_path / "obra.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(ruta))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_PROYECTO] = ob.NOMBRE
    at.session_state[CLAVE_VALUACIONES] = con_valuaciones
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_sin_marcar_la_pantalla_pide_lo_ejecutado_a_mano(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, tmp_path, con_valuaciones=False)
    assert len(at.dataframe) == 3  # componentes, periodos y ejecutado
    assert any("valuaciones" in c.label for c in at.checkbox)


def test_marcada_la_tabla_de_lo_ejecutado_no_se_pide(monkeypatch, tmp_path):
    a_mano = len(_pantalla(monkeypatch, tmp_path / "a", con_valuaciones=False).dataframe)
    marcada = _pantalla(monkeypatch, tmp_path / "b", con_valuaciones=True)
    assert len(marcada.dataframe) == a_mano - 1
    assert any("valuaciones no anuladas" in c.value for c in marcada.caption)
