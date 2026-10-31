"""`GET /v1/riesgo/reportes/{tipo}`: los reportes de riesgo y de mejora (Tarea 21 del plan vial).

Datos FICTICIOS de `tests/fixtures/riesgo_obra.py`; mismo acceso que las vecinas (`ver_riesgo`: las
tres cuentas; sin sesión 401). Oráculos a mano, los de `test_api_riesgo.py`: total base 1.000 USD,
P50 = P80 = 1.248,7171 y reserva 248,7171; con «hoy» el 31/10/2026 la comprobación tiene 7 cortes y
cobertura 100,00 %. Mejora: real 130, original 100 y Sílice 125 dan 23,08 %, 3,85 % y 19,23 puntos.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook

from api import caso_web, dependencias
from api.rutas import riesgo as rutas
from operacion import config
from seguridad import cuentas
from tests.fixtures.produccion_api import Web, cliente_con_clave
from tests.fixtures.riesgo_obra import ARCHIVO, CON_LINEA_BASE, MAPA, OBRA, crear_via
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

D = Decimal
RAIZ = "/v1/riesgo/reportes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
P80 = D("1248.7171")


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantilla_reportes_riesgo")
    return {"instalacion": plantilla_con_cuentas(carpeta), "via": crear_via(carpeta / ARCHIVO)}


@pytest.fixture(autouse=True)
def _entorno(_plantillas, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / ARCHIVO).write_bytes(_plantillas["via"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    monkeypatch.setattr(rutas, "hoy", lambda: date(2026, 10, 31))
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()
    cuentas.FRENO.reiniciar()


def _en_la_via(quien: str = "ana") -> Web:
    web = Web(quien)
    assert web.post("/v1/casos/actual", json={"nombre": ARCHIVO}).status_code == 200
    return web


def _riesgo(**cambios) -> dict:
    base = {
        "proyecto": OBRA,
        "version": CON_LINEA_BASE,
        "meses": 6,
        "trayectorias": 50,
        "trayectorias_por_corte": 20,
        "mapa": json.dumps(MAPA),
    }
    return {**base, **cambios}


def _mejora(**cambios) -> dict:
    base = {"costo_final_real": "130", "presupuesto_original": "100", "estimacion_silice": "125"}
    return {**base, **cambios}


def _libro(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    return load_workbook(BytesIO(respuesta.content))


def _valor(libro, hoja: str, rotulo: str):
    for fila in libro[hoja].iter_rows(values_only=True):
        if fila[0] == rotulo:
            return fila[1]
    raise AssertionError(f"no hay {rotulo!r} en {hoja}")


@pytest.mark.parametrize("quien", ["ana", "rita", "admin"])
def test_los_tres_roles_descargan_el_riesgo(quien: str) -> None:
    r = _en_la_via(quien).get(f"{RAIZ}/riesgo", params=_riesgo())
    libro = _libro(r)
    assert r.headers["content-type"] == XLSX
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["content-disposition"].startswith('attachment; filename="riesgo_')
    assert libro.sheetnames[:2] == ["Portada", "Proyección"]
    assert D(str(_valor(libro, "Proyección", "Total base"))) == D(1000)
    assert D(str(_valor(libro, "Proyección", "P80"))) == P80
    assert D(str(_valor(libro, "Proyección", "Reserva (P80 − total base)"))) == D("248.7171")
    assert _valor(libro, "Proyección", "Origen del inicio") == "línea base de la versión"
    assert "Comprobación" not in libro.sheetnames


def test_el_riesgo_con_comprobacion_trae_siete_cortes_y_cobertura_total() -> None:
    libro = _libro(_en_la_via().get(f"{RAIZ}/riesgo", params=_riesgo(comprobar="true")))
    assert libro.sheetnames[-1] == "Comprobación"
    assert _valor(libro, "Comprobación", "Cortes") == 7
    assert D(str(_valor(libro, "Comprobación", "Cobertura (%)"))) == D("100.00")


def test_el_mapa_y_las_mezclas_quedan_en_el_libro() -> None:
    libro = _libro(_en_la_via().get(f"{RAIZ}/riesgo", params=_riesgo()))
    declarado = {f[0]: f[1] for f in list(libro["Mapa de series"].iter_rows(values_only=True))[1:]}
    assert declarado == MAPA


def test_la_mejora_de_la_mano() -> None:
    r = _en_la_via().get(f"{RAIZ}/mejora", params=_mejora())
    libro = _libro(r)
    assert libro.sheetnames == ["Portada", "Mejora"]
    assert D(str(_valor(libro, "Mejora", "Error del presupuesto original (%)"))) == D("23.08")
    assert D(str(_valor(libro, "Mejora", "Error de la estimación de Sílice (%)"))) == D("3.85")
    assert D(str(_valor(libro, "Mejora", "Mejora (puntos porcentuales)"))) == D("19.23")


def test_la_mejora_con_clave_de_api() -> None:
    r = cliente_con_clave().get(f"{RAIZ}/mejora", params=_mejora())
    assert load_workbook(BytesIO(r.content)).sheetnames == ["Portada", "Mejora"], r.text


def test_sin_credenciales_401() -> None:
    from api.main import app
    from tests.fixtures.sesion_web import cliente

    assert cliente(app).get(f"{RAIZ}/mejora", params=_mejora()).status_code == 401


def test_tipo_desconocido_404() -> None:
    r = _en_la_via().get(f"{RAIZ}/inventado", params=_mejora())
    assert r.status_code == 404, r.text


@pytest.mark.parametrize("campo", ["costo_final_real", "presupuesto_original", "estimacion_silice"])
def test_mejora_con_cifra_mala_422(campo: str) -> None:
    r = _en_la_via().get(f"{RAIZ}/mejora", params=_mejora(**{campo: "1,5"}))
    assert r.status_code == 422, r.text
    assert "detalle" in r.json()


def test_mejora_sin_las_tres_cifras_422_sin_eco() -> None:
    r = _en_la_via().get(f"{RAIZ}/mejora", params={"costo_final_real": "130987"})
    assert r.status_code == 422, r.text
    assert "130987" not in r.text


def test_riesgo_sin_obra_ni_version_422() -> None:
    r = _en_la_via().get(f"{RAIZ}/riesgo", params={"mapa": "{}"})
    assert r.status_code == 422, r.text


def test_riesgo_con_mapa_que_no_es_un_objeto_422() -> None:
    r = _en_la_via().get(f"{RAIZ}/riesgo", params=_riesgo(mapa="[1, 2]"))
    assert r.status_code == 422, r.text
    r = _en_la_via().get(f"{RAIZ}/riesgo", params=_riesgo(mapa="no es json"))
    assert r.status_code == 422, r.text


def test_riesgo_de_una_version_que_no_existe_404() -> None:
    r = _en_la_via().get(f"{RAIZ}/riesgo", params=_riesgo(version="NO-EXISTE"))
    assert r.status_code == 404, r.text
