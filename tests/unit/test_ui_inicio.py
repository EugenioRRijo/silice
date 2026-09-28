"""La pantalla de Inicio (sprint de UI, RF-36 a RF-40), con `AppTest`.

Arnes heredado de `tests/unit/test_ui_componer.py`: la base se desvia parchando el **objeto
modulo** `sys.modules["ui.caso"]` (no una ruta de texto) y se comprueba antes de pulsar nada que
la desviacion surtio efecto. La salvaguarda de `tests/conftest.py` falla la sesion si algo llega a
`data/apu.db`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import ElementList

from ui.caso import CLAVE_CASO, CLAVE_RECORRIDO, estado_caso
from ui.paginas.inicio import ROTULO_ABRIR, ROTULO_ARCHIVO, ROTULO_RECORRIDO, ROTULO_SEMBRAR
from ui.recorridos import NOMBRE_PRECIOS, RECORRIDOS

SCRIPT = "from ui.paginas.inicio import render\nrender()\n"

#: La siembra completa (linea base + demostracion + presupuesto auditado) supera holgadamente los
#: 60 s del arnes de la pantalla de componer en una maquina lenta de CI.
TIEMPO_SIEMBRA = 300


def _por_rotulo(elementos: ElementList, rotulo: str):
    for elemento in elementos:
        if elemento.label == rotulo:
            return elemento
    raise AssertionError(f"ningun elemento {rotulo!r}: {[e.label for e in elementos]}")


def _inicio(monkeypatch, base: Path, *, tiempo: int = 60) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=tiempo)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert _por_rotulo(at.text_input, ROTULO_ARCHIVO).value == str(base), (
        "la desviacion de ui.caso.RUTA_BASE_POR_DEFECTO no surtio efecto"
    )
    return at


def test_el_inicio_ofrece_los_tres_recorridos(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    radio = _por_rotulo(at.radio, ROTULO_RECORRIDO)
    assert list(radio.options) == [r.nombre for r in RECORRIDOS]
    assert radio.value is None


def test_elegir_un_recorrido_lo_fija_en_la_clave_propia(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.radio, ROTULO_RECORRIDO).set_value(NOMBRE_PRECIOS).run()
    assert at.session_state[CLAVE_RECORRIDO] == NOMBRE_PRECIOS


def test_una_base_inexistente_muestra_el_estado_vacio_sin_crearla(
    monkeypatch, tmp_path: Path
) -> None:
    base = tmp_path / "nueva.db"
    at = _inicio(monkeypatch, base)
    assert any("no tiene partidas" in info.value for info in at.info)
    assert _por_rotulo(at.button, ROTULO_SEMBRAR)
    assert not base.exists()


def test_una_base_existente_sin_partidas_ofrece_sembrar(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "vacia.db"
    base.touch()
    at = _inicio(monkeypatch, base)
    assert any("no tiene partidas" in info.value for info in at.info)
    assert _por_rotulo(at.button, ROTULO_SEMBRAR)


def test_la_siembra_deja_la_base_utilizable(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "nueva.db"
    at = _inicio(monkeypatch, base, tiempo=TIEMPO_SIEMBRA)
    _por_rotulo(at.button, ROTULO_SEMBRAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    estado = estado_caso(base)
    assert estado.partidas > 0 and estado.lista_vigente
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]


def test_con_partidas_no_se_ofrece_sembrar(monkeypatch, tmp_path: Path) -> None:
    from core.catalog import abrir_sesion, crear_esquema, crear_motor
    from scripts.seed import sembrar

    base = tmp_path / "sembrada.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    at = _inicio(monkeypatch, base)
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]


def test_abrir_otro_caso_lo_fija_en_la_clave_propia(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    otra = tmp_path / "otra.db"
    _por_rotulo(at.text_input, ROTULO_ARCHIVO).set_value(str(otra))
    _por_rotulo(at.button, ROTULO_ABRIR).click().run()
    assert at.session_state[CLAVE_CASO] == str(otra)
    assert CLAVE_CASO not in {widget.key for widget in at.text_input}


def test_abrir_un_caso_vacio_avisa_y_conserva_el_anterior(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.text_input, ROTULO_ARCHIVO).set_value("   ")
    _por_rotulo(at.button, ROTULO_ABRIR).click().run()
    assert any("no puede quedar vacia" in error.value for error in at.error)
    assert CLAVE_CASO not in at.session_state


def test_un_archivo_ilegible_se_informa_sin_ofrecer_sembrar(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "notas.db"
    base.write_text("esto no es una base de datos\n" * 20, encoding="utf-8")
    at = _inicio(monkeypatch, base)
    assert any("No se pudo leer" in error.value for error in at.error)
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]
