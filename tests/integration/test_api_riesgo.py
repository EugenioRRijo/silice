"""`/v1/riesgo`: el informe de mejora de la estimación (Tarea 15 del plan vial). Datos FICTICIOS.

`ver_riesgo` es de arma, revisa y administrador: las tres cuentas pasan. Las cifras viajan como
texto con punto decimal (como en el resto de la API; la coma es cosa del front). Sin sesión ni clave
401. Oráculo a mano: real 130, original 100 y Sílice 125 dan 23,08 %, 3,85 % y 19,23 puntos.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seguridad import cuentas
from tests.fixtures.produccion_api import Web, cliente_con_clave
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

RUTA = "/v1/riesgo/mejora"


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_riesgo"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    copiar_instalacion(_instalacion_migrada)
    yield
    cuentas.FRENO.reiniciar()


def _cuerpo(**cambios) -> dict:
    base = {"costo_final_real": "130", "presupuesto_original": "100", "estimacion_silice": "125"}
    return {**base, **cambios}


@pytest.mark.parametrize("quien", ["ana", "rita", "admin"])
def test_los_tres_roles_ven_el_informe(quien: str) -> None:
    r = Web(quien).post(RUTA, json=_cuerpo())
    assert r.status_code == 200, r.text
    assert r.json() == {
        "error_original_pct": "23.08",
        "error_silice_pct": "3.85",
        "mejora_pp": "19.23",
    }


def test_con_clave_de_api_tambien() -> None:
    http: TestClient = cliente_con_clave()
    r = http.post(RUTA, json=_cuerpo())
    assert r.status_code == 200, r.text
    assert r.json()["mejora_pp"] == "19.23"


def test_sin_credenciales_401() -> None:
    from api.main import app
    from tests.fixtures.sesion_web import cliente

    assert cliente(app).post(RUTA, json=_cuerpo()).status_code == 401


def test_sin_ver_riesgo_403(monkeypatch: pytest.MonkeyPatch) -> None:
    """Una cuenta cuyo rol no tiene `ver_riesgo` recibe 403 (se quita la acción a `revisa`)."""
    from seguridad import permisos

    monkeypatch.setitem(
        permisos.PERMISOS,
        permisos.Accion.VER_RIESGO,
        frozenset({permisos.Rol.ARMA, permisos.Rol.ADMINISTRADOR}),
    )
    r = Web("rita").post(RUTA, json=_cuerpo())
    assert r.status_code == 403, r.text


def test_la_mejora_negativa_se_informa() -> None:
    r = Web("ana").post(
        RUTA, json=_cuerpo(costo_final_real="100", presupuesto_original="120", estimacion_silice="70")
    )
    assert r.status_code == 200, r.text
    assert r.json()["mejora_pp"] == "-10.00"


@pytest.mark.parametrize("campo", ["costo_final_real", "presupuesto_original", "estimacion_silice"])
@pytest.mark.parametrize("texto", ["abc", "1,5", "", "NaN", "Infinity", "1e3"])
def test_texto_no_decimal_422(campo: str, texto: str) -> None:
    r = Web("ana").post(RUTA, json=_cuerpo(**{campo: texto}))
    assert r.status_code == 422, r.text
    assert "detalle" in r.json()


def test_real_cero_422() -> None:
    r = Web("ana").post(RUTA, json=_cuerpo(costo_final_real="0"))
    assert r.status_code == 422, r.text
    assert "costo final real" in r.json()["detalle"]


def test_cuerpo_incompleto_o_con_numero_json_422() -> None:
    assert Web("ana").post(RUTA, json={"costo_final_real": "130"}).status_code == 422
    assert Web("ana").post(RUTA, json=_cuerpo(costo_final_real=130)).status_code == 422
