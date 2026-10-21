"""`aplicacion.entorno.modo_entrega_activo`: la API informa el modo entrega sin importar `ui/`
(punto 7 de la ola 0a, sesión 2b).

Duplicaba a propósito `ui.app.modo_entrega_activo` (retirada con Streamlit, F4). El oráculo son los
valores literales de la tabla `ENTORNOS`, que eran los que devolvía la función de Streamlit: solo
el valor exacto `1` de `SILICE_MODO_ENTREGA` lo enciende.
"""

from __future__ import annotations

import pytest

from aplicacion import entorno
from operacion import config

ENTORNOS = [
    ({}, False),
    ({"SILICE_MODO_ENTREGA": "1"}, True),
    ({"SILICE_MODO_ENTREGA": "0"}, False),
    ({"SILICE_MODO_ENTREGA": ""}, False),
    ({"SILICE_MODO_ENTREGA": "  "}, False),
    ({"SILICE_MODO_ENTREGA": " 1"}, False),
    ({"SILICE_MODO_ENTREGA": "si"}, False),
    ({"SILICE_MODO_ENTREGA": "true"}, False),
    ({"ARENIA_MODO_ENTREGA": "1"}, False),  # el alias retirado en la 0.7.0 ya no cuenta
]


def test_la_variable_del_modo_entrega_es_la_documentada() -> None:
    assert entorno.VARIABLE_MODO_ENTREGA == "SILICE_MODO_ENTREGA"


@pytest.mark.parametrize(("variables", "esperado"), ENTORNOS, ids=lambda v: repr(v))
def test_dice_lo_que_dice_la_tabla(variables: dict[str, str], esperado: bool) -> None:
    assert entorno.modo_entrega_activo(variables) is esperado


def test_solo_el_valor_exacto_1_lo_enciende() -> None:
    assert entorno.modo_entrega_activo({"SILICE_MODO_ENTREGA": "1"}) is True
    assert entorno.modo_entrega_activo({}) is False


def test_sin_entorno_lee_el_del_proceso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILICE_MODO_ENTREGA", "1")
    assert entorno.modo_entrega_activo() is True
    monkeypatch.delenv("SILICE_MODO_ENTREGA")
    assert entorno.modo_entrega_activo() is False


def test_url_clasica_ya_no_existe() -> None:
    """Streamlit se retiro (F10): `aplicacion.entorno` no calcula su direccion."""
    assert not hasattr(entorno, "url_clasica")


def test_modo_entrega_solo_se_activa_con_el_valor_exacto_1() -> None:
    """Movida de `tests/unit/test_ui_app.py` (retiro de Streamlit, F3): la prueba de `ui.app`
    con los cuatro valores literales, sobre `aplicacion.entorno` (el objeto que sobrevive)."""
    variable = entorno.VARIABLE_MODO_ENTREGA
    assert entorno.modo_entrega_activo({variable: "1"}) is True
    assert entorno.modo_entrega_activo({}) is False
    assert entorno.modo_entrega_activo({variable: "0"}) is False
    assert entorno.modo_entrega_activo({variable: "si"}) is False
