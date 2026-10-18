"""`aplicacion.entorno.modo_entrega_activo`: la API informa el modo entrega sin importar `ui/`
(punto 7 de la ola 0a, sesión 2b).

Duplica a propósito `ui.app.modo_entrega_activo` (que lee con `ui.entorno.leer_variable`, y
`ui/entorno.py` solo puede usar la biblioteca estándar: no puede importar `aplicacion`). El oráculo
es la función de Streamlit: las dos dicen lo mismo en cada entorno de la tabla, y la variable se
llama igual.
"""

from __future__ import annotations

import pytest

from aplicacion import entorno
from ui import entorno as entorno_ui
from ui.app import modo_entrega_activo as de_streamlit

ENTORNOS = [
    {},
    {"SILICE_MODO_ENTREGA": "1"},
    {"SILICE_MODO_ENTREGA": "0"},
    {"SILICE_MODO_ENTREGA": ""},
    {"SILICE_MODO_ENTREGA": "  "},
    {"SILICE_MODO_ENTREGA": " 1"},
    {"SILICE_MODO_ENTREGA": "si"},
    {"SILICE_MODO_ENTREGA": "true"},
    {"ARENIA_MODO_ENTREGA": "1"},  # el alias retirado en la 0.7.0 ya no cuenta
]


def test_la_variable_es_la_misma_que_lee_la_interfaz_clasica() -> None:
    assert entorno.VARIABLE_MODO_ENTREGA == entorno_ui.VARIABLE_MODO_ENTREGA


@pytest.mark.parametrize("variables", ENTORNOS, ids=repr)
def test_dice_lo_mismo_que_la_interfaz_clasica(variables: dict[str, str]) -> None:
    assert entorno.modo_entrega_activo(variables) is de_streamlit(variables)


def test_solo_el_valor_exacto_1_lo_enciende() -> None:
    assert entorno.modo_entrega_activo({"SILICE_MODO_ENTREGA": "1"}) is True
    assert entorno.modo_entrega_activo({}) is False


def test_sin_entorno_lee_el_del_proceso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILICE_MODO_ENTREGA", "1")
    assert entorno.modo_entrega_activo() is True
    monkeypatch.delenv("SILICE_MODO_ENTREGA")
    assert entorno.modo_entrega_activo() is False
