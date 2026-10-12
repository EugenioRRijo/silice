"""Esquemas de las 13 herramientas (S4 §6, §7.1, RF-91; plan 0.9.0, tarea 5)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from asistente.herramientas import (
    CAMPOS_PROHIBIDOS,
    HERRAMIENTAS,
    POR_NOMBRE,
    ProponerAmbiente,
    a_decimal,
)

AMBIENTE = {
    "id": "BAN-01",
    "nombre": "Bano",
    "x0": "0",
    "y0": "0",
    "largo": "2,4",
    "ancho": "1.5",
    "alto": "2.5",
    "citas": [{"campo": "largo", "texto": "2,4"}],
    "supuestos": [],
}


def _objetos(esquema):
    """Todo sub-esquema que declara propiedades (los objetos del esquema JSON)."""
    if isinstance(esquema, dict):
        if "properties" in esquema:
            yield esquema
        for valor in esquema.values():
            yield from _objetos(valor)
    elif isinstance(esquema, list):
        for valor in esquema:
            yield from _objetos(valor)


def test_son_trece_herramientas_en_el_orden_fijo_del_spec():
    assert [h.nombre for h in HERRAMIENTAS] == [
        "consultar_borrador",
        "buscar_partidas",
        "consultar_partida",
        "proponer_ambiente",
        "proponer_fuente",
        "proponer_punto",
        "proponer_recorrido",
        "proponer_partida",
        "declarar_sin_partida",
        "retirar_propuesta",
        "pedir_informe_auditoria",
        "preguntar_al_usuario",
        "terminar",
    ]
    assert len(POR_NOMBRE) == 13


def test_todo_objeto_del_esquema_prohibe_campos_extra_y_exige_todos_sus_campos():
    for herramienta in HERRAMIENTAS:
        for objeto in _objetos(herramienta.esquema()):
            assert objeto["additionalProperties"] is False, herramienta.nombre
            assert set(objeto.get("required", [])) == set(objeto["properties"]), herramienta.nombre


def test_ninguna_herramienta_tiene_campo_de_precio_total_o_cantidad_derivada():
    for herramienta in HERRAMIENTAS:
        for objeto in _objetos(herramienta.esquema()):
            assert not CAMPOS_PROHIBIDOS & set(objeto["properties"]), herramienta.nombre


def test_el_esquema_exportado_es_estable():
    primero = json.dumps([h.esquema() for h in HERRAMIENTAS], sort_keys=True)
    segundo = json.dumps([h.esquema() for h in HERRAMIENTAS], sort_keys=True)
    assert primero == segundo


@pytest.mark.parametrize("campo", ["largo", "ancho", "alto", "x0", "y0"])
@pytest.mark.parametrize("malo", ["2.4000", "dos", "2.", "", "12345", "1e3", "2,4,1"])
def test_un_numero_mal_formado_se_rechaza(campo, malo):
    with pytest.raises(ValidationError):
        ProponerAmbiente.model_validate({**AMBIENTE, campo: malo})


@pytest.mark.parametrize("bueno", ["0", "-1.5", "2,4", "2.400", "1234", "-1234,567"])
def test_un_numero_bien_formado_pasa(bueno):
    assert ProponerAmbiente.model_validate({**AMBIENTE, "largo": bueno}).largo == bueno


def test_un_float_se_rechaza_y_un_campo_extra_tambien():
    with pytest.raises(ValidationError):
        ProponerAmbiente.model_validate({**AMBIENTE, "largo": 2.4})
    with pytest.raises(ValidationError):
        ProponerAmbiente.model_validate({**AMBIENTE, "precio": "10"})


def test_un_campo_opcional_es_requerido_pero_admite_null():
    esquema = POR_NOMBRE["proponer_punto"].modelo.model_json_schema()
    assert "fuente_id" in esquema["required"]


def test_a_decimal_acepta_coma_y_punto():
    assert str(a_decimal("2,40")) == "2.40"
    assert str(a_decimal("-0.005")) == "-0.005"
