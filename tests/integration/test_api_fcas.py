"""`/v1/fcas`: FCAS por componentes (Tarea 17 del plan vial). Datos FICTICIOS salvo el oráculo
publicado.

Cualquier rol con sesión (o la clave de API) calcula: es una cuenta pura, no toca la base. Las
cifras viajan como texto con punto decimal. Oráculo a mano (Dodi y Salas 2019): 365 días, 23,13 de
bonificación y 217,28 trabajados dan días pagados 388,13, FCAS 0,7863, «78,63 %» y «× 1,7863»; con
un aporte de 2 % del salario pagado, 0,8220."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seguridad import cuentas
from tests.fixtures.produccion_api import Web, cliente_con_clave
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

CALCULAR = "/v1/fcas/calcular"
COMPONENTES = "/v1/fcas/componentes"


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_fcas"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    copiar_instalacion(_instalacion_migrada)
    yield
    cuentas.FRENO.reiniciar()


BONIFICACION = {
    "id": "bonificaciones",
    "nombre": "Bonificaciones",
    "base": "dias",
    "valor": "23.13",
    "fuente": "Dodi y Salas (2019), caso 1",
}
APORTE_2 = {
    "id": "aporte_demo",
    "nombre": "Aporte de demostración",
    "base": "porcentaje",
    "valor": "2",
    "fuente": "ficticio",
}


def _cuerpo(*componentes: dict, **cambios) -> dict:
    base = {
        "dias_calendario": "365",
        "dias_trabajados": "217.28",
        "componentes": list(componentes or (BONIFICACION,)),
    }
    return {**base, **cambios}


@pytest.mark.parametrize("quien", ["ana", "rita", "admin"])
def test_los_tres_roles_calculan_el_oraculo(quien: str) -> None:
    r = Web(quien).post(CALCULAR, json=_cuerpo())
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["fcas"] == "0.7863"
    assert cuerpo["fcas_por_dias"] == "0.7863"
    assert cuerpo["dias_pagados"] == "388.13"
    assert cuerpo["porcentaje"] == "78.63"
    assert cuerpo["multiplicador"] == "1.7863"
    assert cuerpo["a_cotejar"] == []
    assert cuerpo["version"] is None


def test_con_un_aporte_de_2_por_ciento() -> None:
    r = Web("ana").post(CALCULAR, json=_cuerpo(BONIFICACION, APORTE_2))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["fcas"] == "0.8220"
    assert cuerpo["fcas_por_dias"] == "0.7863"
    assert cuerpo["porcentaje"] == "82.20"
    assert cuerpo["multiplicador"] == "1.8220"
    assert [fila["id"] for fila in cuerpo["desglose"]] == [
        "dias_no_trabajados",
        "bonificaciones",
        "aporte_demo",
    ]
    assert cuerpo["desglose"][0]["nombre"].startswith("Días pagados sin trabajar")
    assert cuerpo["desglose"][2]["nombre"] == "Aporte de demostración"


def test_el_fcas_de_la_version_va_al_lado_y_no_se_aplica_solo() -> None:
    r = Web("ana").post(CALCULAR, json=_cuerpo(fcas_version="6.00"))
    assert r.status_code == 200, r.text
    assert r.json()["version"] == {"fcas": "6.00", "porcentaje": "600.00", "multiplicador": "7.00"}
    # Calcular no guarda nada: la respuesta no trae «aplicado»
    assert "aplicado" not in r.json()


def test_un_componente_a_cotejar_se_avisa() -> None:
    dudoso = {
        **APORTE_2,
        "id": "ivss",
        "nombre": "Seguro social",
        "fuente": "Reglamento — a cotejar",
    }
    r = Web("ana").post(CALCULAR, json=_cuerpo(BONIFICACION, dudoso))
    assert r.json()["a_cotejar"] == [{"id": "ivss", "nombre": "Seguro social"}]


def test_el_bono_de_alimentacion_se_rechaza_422() -> None:
    bono = {**BONIFICACION, "id": "bono_alimentacion", "nombre": "Bono de alimentación"}
    r = Web("ana").post(CALCULAR, json=_cuerpo(BONIFICACION, bono))
    assert r.status_code == 422, r.text
    assert "bono de alimentación" in r.json()["detalle"]


def test_con_clave_de_api_tambien() -> None:
    http: TestClient = cliente_con_clave()
    r = http.post(CALCULAR, json=_cuerpo())
    assert r.status_code == 200, r.text
    assert r.json()["fcas"] == "0.7863"
    assert http.get(COMPONENTES).status_code == 200


def test_sin_credenciales_401() -> None:
    from api.main import app
    from tests.fixtures.sesion_web import cliente

    http = cliente(app)
    assert http.post(CALCULAR, json=_cuerpo()).status_code == 401
    assert http.get(COMPONENTES).status_code == 401


@pytest.mark.parametrize("campo", ["dias_calendario", "dias_trabajados", "fcas_version"])
@pytest.mark.parametrize("texto", ["abc", "217,28", "", "NaN", "1e3"])
def test_texto_no_decimal_422(campo: str, texto: str) -> None:
    r = Web("ana").post(CALCULAR, json=_cuerpo(**{campo: texto}))
    assert r.status_code == 422, r.text
    assert "detalle" in r.json()


def test_valor_de_componente_no_decimal_422() -> None:
    r = Web("ana").post(CALCULAR, json=_cuerpo({**BONIFICACION, "valor": "23,13"}))
    assert r.status_code == 422, r.text


def test_dias_imposibles_422() -> None:
    r = Web("ana").post(CALCULAR, json=_cuerpo(dias_trabajados="0"))
    assert r.status_code == 422, r.text
    assert "días trabajados" in r.json()["detalle"]
    assert Web("ana").post(CALCULAR, json=_cuerpo(dias_trabajados="400")).status_code == 422


def test_cuerpo_incompleto_o_con_numero_json_422() -> None:
    assert Web("ana").post(CALCULAR, json={"dias_calendario": "365"}).status_code == 422
    assert Web("ana").post(CALCULAR, json=_cuerpo(dias_trabajados=217.28)).status_code == 422


def test_la_lista_de_componentes_por_defecto() -> None:
    r = Web("rita").get(COMPONENTES)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["dias_calendario"] == "365"
    assert cuerpo["fcas_version"] == "6.00"  # el de una versión sin cambios (núcleo)
    por_id = {c["id"]: c for c in cuerpo["componentes"]}
    assert "bono_alimentacion" not in por_id
    assert por_id["pensiones"]["valor"] == "9"
    assert por_id["pensiones"]["a_cotejar"] is True
    assert por_id["ivss"]["valor"] == "11"
    assert por_id["ivss"]["a_cotejar"] is True
    for clave in ("paro_forzoso", "faov", "inces"):
        assert por_id[clave]["a_cotejar"] is True
        assert "a cotejar con el texto de la ley" in por_id[clave]["fuente"]
    assert por_id["utilidades"]["a_cotejar"] is False
    assert por_id["utilidades"]["base"] == "dias"
    assert por_id["utilidades"]["valor"] == "100"
    assert all(c["fuente"] for c in cuerpo["componentes"])
