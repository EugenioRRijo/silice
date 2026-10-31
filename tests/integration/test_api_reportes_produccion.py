"""`GET /v1/produccion/reportes/produccion?periodo=`: el reporte de costo de producción en Excel
(Tarea 21 del plan vial, movido en las pantallas de informes, fila 112 y MENOR 1 del árbitro de la
fase D). Datos FICTICIOS.

El costo es el de noviembre de 2026 en USD de `tests/fixtures/costo_propio.py` (`AGR-12` a 5 USD/t,
`MZ-1` a 50,70). Acceso: `registrar_costos_produccion` (arma y administrador; rita 403; sin sesión
401) y DESPUÉS el módulo producción (apagado: 404 con el texto de D-V-4). Solo lee la instalación:
el administrador lo baja sin carpeta abierta. La ruta vieja `/v1/vial/reportes/produccion` ya no
existe (nadie la usaba fuera de las pruebas).
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from api import caso_web, dependencias
from api.main import app
from aplicacion.costo_propio import calcular_periodo
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from operacion.instalacion import sesion_de_instalacion
from tests.fixtures import costo_propio as cp
from tests.fixtures.carpeta_aprobaciones import sembrar_vivienda
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
ANA = "Ana <ana>"
RUTA = "/v1/produccion/reportes/produccion"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
APAGADO_PRODUCCION = "El módulo producción está apagado en esta instalación."


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_reporte_produccion")
    vivienda = carpeta / "vivienda.db"
    preparar_base(vivienda)
    motor = crear_motor(f"sqlite:///{vivienda.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            sembrar_vivienda(s, usuario=ANA)
    finally:
        motor.dispose()
    return {"instalacion": plantilla_con_cuentas(carpeta), "vivienda.db": vivienda}


@pytest.fixture(autouse=True)
def _entorno(_plantillas, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / "vivienda.db").write_bytes(_plantillas["vivienda.db"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def calculo() -> int:
    """El cálculo de noviembre de 2026 (USD), en la instalación y la carpeta de la prueba."""
    motor = crear_motor(f"sqlite:///{(config.carpeta_casos() / 'vivienda.db').as_posix()}")
    try:
        with abrir_sesion(motor) as caso, sesion_de_instalacion() as ins:
            cp.noviembre_usd(ins, caso)
            guardado = calcular_periodo(ins, caso, cp.PERIODO, "USD", usuario="ana", ahora=cp.AHORA)
            caso.commit()
            ins.commit()
            return guardado.id
    finally:
        motor.dispose()


@pytest.fixture
def ana() -> tuple[TestClient, str]:
    navegador, ficha = con_cuenta(app, "ana")
    elegida = navegador.post(
        "/v1/casos/actual", json={"nombre": "vivienda.db"}, headers=protegida(ficha)
    )
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


@pytest.fixture
def admin() -> tuple[TestClient, str]:
    return con_cuenta(app, "admin")


def _pedir(cuenta, **params):
    return cuenta[0].get(RUTA, params=params)


def _apagar_produccion(admin) -> None:
    navegador, ficha = admin
    r = navegador.put("/v1/modulos/produccion", json={"activo": False}, headers=protegida(ficha))
    assert r.status_code == 200, r.text


def _costos(respuesta) -> dict[str, tuple[int, Decimal]]:
    assert respuesta.status_code == 200, respuesta.text
    libro = load_workbook(BytesIO(respuesta.content))
    assert libro.sheetnames[:3] == ["Portada", "Cálculos", "Costo por tonelada"]
    filas = [f for f in libro["Costo por tonelada"].iter_rows(values_only=True) if any(f)]
    return {f[2]: (f[0], D(str(f[4]))) for f in filas[1:]}


def test_quien_registra_costos_baja_el_reporte_de_la_mano(ana, calculo) -> None:
    r = _pedir(ana, periodo=cp.PERIODO)
    assert _costos(r) == {"AGR-12": (calculo, D(5)), "MZ-1": (calculo, D("50.70"))}
    assert r.headers["content-type"] == XLSX
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["content-disposition"] == 'attachment; filename="produccion_2026-11.xlsx"'


def test_el_administrador_tambien_lo_baja_sin_carpeta_abierta(admin, calculo) -> None:
    """La alternativa de la fila 112: el administrador registra costos y publica, ahora lo ve."""
    assert _costos(_pedir(admin, periodo=cp.PERIODO))["MZ-1"] == (calculo, D("50.70"))


def test_un_periodo_sin_calculos_404_con_el_periodo(ana) -> None:
    r = _pedir(ana, periodo="2026-01")
    assert r.status_code == 404, r.text
    assert "2026-01" in r.json().get("detalle", "")


def test_sin_periodo_o_con_periodo_malo_422(ana) -> None:
    sin = _pedir(ana)
    assert sin.status_code == 422, sin.text
    assert sin.json() == {"detalle": "Envíe el período del reporte como AAAA-MM (periodo)."}
    assert _pedir(ana, periodo="2026-13").status_code == 422


def test_rita_no_lo_baja() -> None:
    rita = con_cuenta(app, "rita")
    r = _pedir(rita, periodo=cp.PERIODO)
    assert r.status_code == 403, r.text
    assert r.json() == {"detalle": MENSAJE_PERMISO}


def test_sin_credenciales_401() -> None:
    assert cliente(app).get(RUTA, params={"periodo": cp.PERIODO}).status_code == 401


def test_produccion_apagada_404_con_el_texto_de_dv4(ana, admin, calculo) -> None:
    """MENOR 2 del árbitro de la fase D, para el reporte de producción."""
    _apagar_produccion(admin)
    for cuenta in (ana, admin):
        r = _pedir(cuenta, periodo=cp.PERIODO)
        assert r.status_code == 404, r.text
        assert r.json() == {"detalle": APAGADO_PRODUCCION}


def test_produccion_apagada_no_adelanta_al_acceso(admin) -> None:
    """El módulo se comprueba DESPUÉS del acceso: rita sigue recibiendo 403 y el anónimo 401."""
    _apagar_produccion(admin)
    rita = con_cuenta(app, "rita")
    r = _pedir(rita, periodo=cp.PERIODO)
    assert r.status_code == 403 and r.json() == {"detalle": MENSAJE_PERMISO}
    assert cliente(app).get(RUTA, params={"periodo": cp.PERIODO}).status_code == 401


def test_la_ruta_vieja_bajo_vial_ya_no_existe(ana, calculo) -> None:
    r = ana[0].get("/v1/vial/reportes/produccion", params={"periodo": cp.PERIODO})
    assert r.status_code == 404, r.text
    assert r.json() == {"detalle": "No existe el reporte «produccion»."}
