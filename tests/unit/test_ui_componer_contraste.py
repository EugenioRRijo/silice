"""UC-07, flujo 3a, en la pantalla de componer (fase C5, pista U: INV-094).

La ayuda 4 contrasta el precio construido con la estimacion por reglas solo si la partida ya existe
(hay un PU anterior del que partir). Una partida nueva no tiene PU anterior: no se estima, y la
pantalla debe informar que el contraste no es posible en vez de callar.

Misma via que `tests/unit/test_ui_componer.py` (que no se importa: una prueba no importa de otra):
la base (la linea base sembrada, con su lista de precios) vive en `tmp_path`, desviada por el
objeto modulo `sys.modules["ui.caso"]`; las tablas se siembran por
`st.session_state[f"{clave}__filas"]` antes del primer `run()`, y la ayuda 1 se sustituye por un
doble que no sugiere nada. Caso de prueba, no ejecucion real (NORMAS.md §1).
"""

from __future__ import annotations

import dataclasses
import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import ElementList

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from ml.normalization import Propuesta
from scripts.seed import sembrar
from tests.fixtures.apu_linea_base import APU_TUBERIA
from tests.fixtures.filas_composicion import (
    filas_equipos,
    filas_mano_obra,
    filas_materiales,
    texto_tecleado,
)

SCRIPT = "from ui.paginas.componer import render\nrender()\n"
APU_NUEVO = dataclasses.replace(APU_TUBERIA, codigo_partida="UI-07-NUE")
AVISO = "el contraste no es posible"


def _por_rotulo(elementos: ElementList, rotulo: str):
    for elemento in elementos:
        if elemento.label == rotulo:
            return elemento
    raise AssertionError(f"ningun elemento {rotulo!r}: {[e.label for e in elementos]}")


def _avisos(at: AppTest) -> list[str]:
    return [aviso.value for aviso in at.info if AVISO in aviso.value]


def _base_sembrada(base: Path) -> Path:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return base


def test_una_partida_nueva_informa_que_el_contraste_no_es_posible(monkeypatch, tmp_path: Path):
    caso = importlib.import_module("ui.caso")
    base = _base_sembrada(tmp_path / "caso.db")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.componer")
    monkeypatch.setattr(pagina, "sugerir_partidas_similares", lambda *_: Propuesta(()))
    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.session_state["componer_materiales__filas"] = filas_materiales(APU_NUEVO)
    at.session_state["componer_equipos__filas"] = filas_equipos(APU_NUEVO)
    at.session_state["componer_mano_obra__filas"] = filas_mano_obra(APU_NUEVO)
    at.run()
    _por_rotulo(at.text_input, "Codigo").set_value(APU_NUEVO.codigo_partida)
    _por_rotulo(at.text_input, "Descripcion").set_value(APU_NUEVO.descripcion)
    _por_rotulo(at.text_input, "Unidad").set_value(APU_NUEVO.unidad)
    _por_rotulo(at.text_input, pagina.RENDIMIENTO_ETIQUETA).set_value(
        texto_tecleado(APU_NUEVO.rendimiento)
    )
    at.run()
    assert not at.exception, [e.value for e in at.exception]

    # Partida nueva: el desglose en vivo existe, pero no hay PU anterior del que estimar.
    assert _por_rotulo(at.metric, "Precio unitario")
    assert len(_avisos(at)) == 1, [aviso.value for aviso in at.info]

    # Guardada, la partida ya tiene un PU del que partir: el aviso de partida nueva desaparece.
    at.text_area[0].set_value("condiciones de prueba de UC-07 3a: no es una medicion real")
    at.run()
    _por_rotulo(at.button, "Guardar composicion").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert [s.value for s in at.success if APU_NUEVO.codigo_partida in s.value]
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert _avisos(at) == []
