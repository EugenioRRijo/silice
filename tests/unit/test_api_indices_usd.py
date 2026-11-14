"""Índices del BCV en USD por la API, de punta a punta hasta el reajuste (RF-214).

Contrato (bitácora `2026-11-13-ola2-pdf-e-indices.md` §2), con `ADMINISTRAR_PRECIOS` como el resto
de `/v1/indices`:

- `GET /v1/indices/en-usd/origenes` → los índices mensuales en Bs que se pueden expresar en USD.
- `POST /v1/indices/en-usd/ver` `{serie, lado}` → la serie nueva, sus meses, una muestra con la
  cuenta (primer y último mes, en es-VE), los meses que no se pueden y la huella. No escribe.
- `POST /v1/indices/en-usd/confirmar` `{serie, lado, huella}` → la guarda (solo una cuenta; el
  responsable es la persona de la sesión). Con otra huella, 409 y nada escrito.

De punta a punta: el administrador importa por CSV el índice y las tasas FICTICIOS de
`tests/fixtures/reajuste_usd.py`, lo expresa en USD y quien arma calcula el reajuste del contrato
en USD citando la serie nueva: 18.000,00 USD sin la advertencia; con el índice en Bs, 34.200,00 USD
y la advertencia con la salida. Las cuentas están escritas a mano en la fixture.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from api.rutas import reajuste as ruta_reajuste
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures import reajuste_usd as rz
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

CIERRE = datetime(2027, 3, 5, 10, 0)
REMEDIO = (
    "Para un contrato en USD, exprese el índice en USD en «Índices del BCV» y cite esa serie en "
    "la cláusula."
)


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("indices_usd"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr(ruta_reajuste, "ahora", lambda: CIERRE)
    copiar_instalacion(_plantilla)
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            rz.sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _importar_csv(navegador, ficha: str, contenido: bytes, definicion: dict) -> None:
    respuesta = navegador.post(
        "/v1/indices/confirmar",
        data={
            "tipo": "csv",
            "fuente": rz.FUENTE,
            "fecha_descarga": "2027-03-01",
            "definiciones": json.dumps([definicion]),
        },
        files={"archivo": ("ficticio.csv", contenido, "text/csv")},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 200, respuesta.text


def _admin_con_datos():
    navegador, ficha = con_cuenta(app, "admin")
    _importar_csv(navegador, ficha, rz.CSV_INDICES, rz.DEFINICION_INDICE)
    _importar_csv(navegador, ficha, rz.CSV_TASAS, rz.DEFINICION_TASA)
    return navegador, ficha


def _ver(navegador, ficha, serie="FIC-INPC", lado="venta"):
    return navegador.post(
        "/v1/indices/en-usd/ver", json={"serie": serie, "lado": lado}, headers=protegida(ficha)
    )


def _confirmar(navegador, ficha, huella, serie="FIC-INPC", lado="venta"):
    return navegador.post(
        "/v1/indices/en-usd/confirmar",
        json={"serie": serie, "lado": lado, "huella": huella},
        headers=protegida(ficha),
    )


def _reajuste(serie: str) -> dict:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = navegador.post(
        "/v1/reajuste/calcular",
        json={
            "proyecto": rz.NOMBRE,
            "version": "001",
            "clausula": dict(rz.CAMPOS),
            "componentes": rz.componentes(serie),
            "periodos": [dict(p) for p in rz.PERIODOS],
            "ejecutado": [dict(e) for e in rz.EJECUTADO],
        },
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_los_origenes_son_los_indices_mensuales_en_bolivares() -> None:
    navegador, ficha = _admin_con_datos()
    respuesta = navegador.get("/v1/indices/en-usd/origenes")
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert [s["clave"] for s in cuerpo["series"]] == ["FIC-INPC"]
    assert cuerpo["series"][0]["nombre"] == "INPC ficticio"
    assert cuerpo["lados"] == ["venta", "compra"] and cuerpo["lado_por_omision"] == "venta"


def test_ver_muestra_la_cuenta_con_coma_decimal_y_no_escribe(_entorno: Path) -> None:
    navegador, ficha = _admin_con_datos()
    respuesta = _ver(navegador, ficha)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["serie_nueva"] == "FIC-INPC-USD"
    assert cuerpo["meses"] == 2 and (cuerpo["desde"], cuerpo["hasta"]) == ("01/2026", "02/2027")
    assert cuerpo["muestra"] == [
        {"mes": "01/2026", "indice_bs": "200", "tasa_promedio": "40,0000", "valor": "5,000000"},
        {"mes": "02/2027", "indice_bs": "276", "tasa_promedio": "46,0000", "valor": "6,000000"},
    ]
    assert cuerpo["omitidos"] == [] and cuerpo["ya_guardada"] is False
    assert len(cuerpo["huella"]) == 64
    motor = crear_motor(f"sqlite:///{_entorno.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            nuevas = sesion.scalars(
                select(models.SerieIndice).where(models.SerieIndice.codigo == "FIC-INPC-USD")
            ).all()
    finally:
        motor.dispose()
    assert nuevas == []


def test_de_punta_a_punta_el_reajuste_con_el_indice_en_usd_da_18000_sin_advertencia() -> None:
    navegador, ficha = _admin_con_datos()
    huella = _ver(navegador, ficha).json()["huella"]
    confirmado = _confirmar(navegador, ficha, huella)
    assert confirmado.status_code == 200, confirmado.text
    assert confirmado.json() == {"mensajes": ["FIC-INPC-USD: guardada con 2 meses en USD."]}
    otra_vez = _confirmar(navegador, ficha, huella)
    assert otra_vez.json() == {
        "mensajes": [
            "FIC-INPC-USD: ya estaba guardada con estos mismos valores; no se escribió nada."
        ]
    }

    en_usd = _reajuste("FIC-INPC-USD")
    assert en_usd["moneda"] == "USD"
    periodo = en_usd["filas"][0]
    assert periodo["Escalatoria"] == "18000.00"
    assert periodo["Escalatoria (otra)"] == "828000.00"
    assert not any("cuenta dos veces" in a for a in en_usd["avisos"])

    en_bs = _reajuste("FIC-INPC")
    assert en_bs["filas"][0]["Escalatoria"] == "34200.00"
    aviso = next(a for a in en_bs["avisos"] if "cuenta dos veces" in a)
    assert aviso.endswith(REMEDIO)


def test_con_otra_huella_es_409_y_no_escribe() -> None:
    navegador, ficha = _admin_con_datos()
    respuesta = _confirmar(navegador, ficha, "0" * 64)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detalle": "Los índices o las tasas cambiaron desde que lo revisó: revíselo de nuevo."
    }
    origenes = navegador.get("/v1/indices/en-usd/origenes").json()
    assert [s["clave"] for s in origenes["series"]] == ["FIC-INPC"]


def test_una_serie_que_no_existe_es_404_y_una_que_no_es_indice_en_bs_422() -> None:
    navegador, ficha = _admin_con_datos()
    no_hay = _ver(navegador, ficha, serie="NO-HAY")
    assert no_hay.status_code == 404
    assert no_hay.json() == {"detalle": "No hay una serie «NO-HAY» importada."}
    tasa = _ver(navegador, ficha, serie="BCV-USD-VENTA")
    assert tasa.status_code == 422
    assert "no es un índice mensual en bolívares" in tasa.json()["detalle"]
    sin_compra = _ver(navegador, ficha, lado="compra")
    assert sin_compra.status_code == 422
    assert "No hay tasa compra del BCV importada" in sin_compra.json()["detalle"]


def test_un_cuerpo_mal_formado_es_422_sin_eco() -> None:
    navegador, ficha = _admin_con_datos()
    centinela = "CENTINELA-" * 10
    respuesta = navegador.post(
        "/v1/indices/en-usd/ver", json={"serie": centinela, "lado": 7}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422
    assert "CENTINELA" not in respuesta.text


# --- acceso: el de /v1/indices ------------------------------------------------------------------


def test_sin_sesion_es_401_y_quien_arma_no_entra() -> None:
    assert cliente(app).get("/v1/indices/en-usd/origenes").status_code == 401
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _ver(navegador, ficha)
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_PERMISO}


def test_la_clave_de_api_ve_pero_no_confirma() -> None:
    navegador, ficha = _admin_con_datos()
    huella = _ver(navegador, ficha).json()["huella"]
    clave = {CABECERA: crear_clave_de_prueba()}
    anonimo = cliente(app)
    vista = anonimo.post(
        "/v1/indices/en-usd/ver", json={"serie": "FIC-INPC", "lado": "venta"}, headers=clave
    )
    assert vista.status_code == 200
    confirmar = anonimo.post(
        "/v1/indices/en-usd/confirmar",
        json={"serie": "FIC-INPC", "lado": "venta", "huella": huella},
        headers=clave,
    )
    assert confirmar.status_code == 403
