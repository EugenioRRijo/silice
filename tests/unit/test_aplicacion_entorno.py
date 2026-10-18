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
from operacion import config
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


# --- url_clasica (la interfaz Streamlit, para enlazar las páginas aún no migradas) ------------


def test_url_clasica_por_defecto_es_el_bucle_local_con_el_puerto_de_los_ajustes() -> None:
    assert entorno.url_clasica({}) == "http://127.0.0.1:8501/"
    config.guardar_ajustes(config.ruta_ajustes(), config.Ajustes(puerto=8600))
    assert entorno.url_clasica({}) == "http://127.0.0.1:8600/"


def test_url_clasica_usa_la_ip_en_la_que_escuchan_las_dos_interfaces() -> None:
    """El lanzador arranca Streamlit y la API en la misma IP y se la pasa en `SILICE_DIRECCION`."""
    assert entorno.url_clasica({"SILICE_DIRECCION": "192.168.1.20"}) == "http://192.168.1.20:8501/"


@pytest.mark.parametrize(
    "direccion", ["0.0.0.0", "::", "8.8.8.8", "no-es-ip", "", "fe80::1", "127.0.0.2"]
)
def test_url_clasica_no_publica_una_ip_que_no_sea_privada(direccion: str) -> None:
    assert entorno.url_clasica({"SILICE_DIRECCION": direccion}) == "http://127.0.0.1:8501/"
