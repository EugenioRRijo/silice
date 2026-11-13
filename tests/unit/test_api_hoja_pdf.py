"""`GET /v1/hoja/borradores/{id}/pdf`: el presupuesto del borrador vivo en PDF (RF-213).

Contrato (bitácora `2026-11-13-ola2-pdf-e-indices.md` §1): sin `partida`, el presupuesto (encabezado,
partidas, subtotal, IVA y total) y después un APU por página; con `partida`, solo el APU de esa
partida. El mismo acceso que el Excel (X1): una cuenta con `LEER_PROYECTO` y SU borrador; la clave
de API recibe 403; `no-store`; no escribe nada.

Oráculos a mano: total de OF-001 2 703,86 USD (memoria) y con administración 0,20, 2 821,42; IVA
16 %: 432,62 y 3 136,48 (2 703,86 × 0,16 = 432,6176); AF-LLAVE PU 13,198738025 → 13,20 y 3 × PU →
39,60. El texto se extrae con pdfplumber.
"""

from __future__ import annotations

import io
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pdfplumber
import pytest
from fastapi import FastAPI

from api import caso_web, dependencias
from api.rutas import hoja as hoja_ruta
from api.rutas import hoja_exportar
from aplicacion import hoja_borradores
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from tests.fixtures.app_de_prueba import app_con
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

PDF = "application/pdf"
SOLO_CUENTA = "La hoja de la obra se edita y se guarda con una cuenta; la clave de API no sirve."
PROYECTO_NUEVO = "PR-PDF-SIN-VERSION (caso de prueba)"


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_pdf")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }


@pytest.fixture(autouse=True)
def _entorno(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def app() -> FastAPI:
    return app_con(hoja_ruta.router, hoja_exportar.router)


def _abrir(navegador, ficha: str, proyecto: str = NOMBRE_OF001, version: str | None = "001"):
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": proyecto, "version": version},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _pdf(navegador, id_: str, **params):
    return navegador.get(f"/v1/hoja/borradores/{id_}/pdf", params=params)


def _texto(contenido: bytes) -> list[str]:
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def test_el_pdf_de_of001_trae_las_partidas_el_iva_y_un_apu_por_pagina(app: FastAPI) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _pdf(navegador, _abrir(navegador, ficha))
    assert respuesta.status_code == 200, respuesta.text[:200]
    assert respuesta.headers["content-type"] == PDF
    assert (
        respuesta.headers["content-disposition"] == 'attachment; filename="presupuesto_001.pdf"'
    )
    assert respuesta.headers["cache-control"] == "no-store"
    paginas = _texto(respuesta.content)
    todo = "\n".join(paginas)
    for esperado in (
        NOMBRE_OF001,
        "Versión 001",
        "Moneda: USD",
        "AF-LLAVE",
        "13,20",
        "39,60",
        "Subtotal sin IVA",
        "2.703,86",
        "IVA (16 %)",
        "432,62",
        "Total con IVA",
        "3.136,48",
    ):
        assert esperado in todo, esperado
    apus = [p for p in paginas if "Análisis de precio unitario" in p]
    assert len(apus) == 30  # las 30 partidas de la memoria, una por página
    assert f"Página {len(paginas)} de {len(paginas)}" in paginas[-1]


def test_el_pdf_es_el_del_borrador_vivo_y_dice_que_tiene_cambios(app: FastAPI) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    id_ = _abrir(navegador, ficha)
    editado = navegador.put(
        f"/v1/hoja/borradores/{id_}/parametros",
        json={
            "rev": 0,
            "fcas": "6,00",
            "bono_alimentacion": "5,8100",
            "administracion": "0,20",
            "utilidad": "0,10",
        },
        headers=protegida(ficha),
    )
    assert editado.status_code == 200, editado.text
    todo = "\n".join(_texto(_pdf(navegador, id_).content))
    assert "2.821,42" in todo
    assert "Versión 001 con 1 cambio sin guardar." in todo


def test_con_partida_solo_va_su_apu(app: FastAPI) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _pdf(navegador, _abrir(navegador, ficha), partida="AF-LLAVE")
    assert respuesta.status_code == 200, respuesta.text[:200]
    assert (
        respuesta.headers["content-disposition"]
        == 'attachment; filename="apu_001_AF-LLAVE.pdf"'
    )
    paginas = _texto(respuesta.content)
    assert len(paginas) == 1
    assert "AF-LLAVE" in paginas[0] and "= Precio unitario" in paginas[0]
    assert "13,20" in paginas[0]
    assert "Total con IVA" not in paginas[0]


def test_una_partida_que_no_esta_valorada_es_404_con_su_mensaje(app: FastAPI) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _pdf(navegador, _abrir(navegador, ficha), partida="NO-EXISTE")
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "detalle": "La partida «NO-EXISTE» no tiene un APU valorado en este borrador."
    }
    assert respuesta.headers["cache-control"] == "no-store"


def test_un_borrador_sin_version_se_llama_presupuesto_borrador(app: FastAPI) -> None:
    dependencias.cerrar_motores()
    motor = crear_motor(f"sqlite:///{config.ruta_caso_por_defecto().as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            crear_proyecto(sesion, PROYECTO_NUEVO)
            sesion.commit()
    finally:
        motor.dispose()
    navegador, ficha = con_cuenta(app, "ana")
    respuesta = _pdf(navegador, _abrir(navegador, ficha, proyecto=PROYECTO_NUEVO, version=None))
    assert respuesta.status_code == 200, respuesta.text[:200]
    assert (
        respuesta.headers["content-disposition"]
        == 'attachment; filename="presupuesto_borrador.pdf"'
    )
    assert "Borrador sin guardar" in "\n".join(_texto(respuesta.content))


def test_el_pdf_no_escribe_nada_en_la_base(app: FastAPI, _entorno: Path) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    id_ = _abrir(navegador, ficha)
    dependencias.cerrar_motores()
    antes = _volcado(_entorno)
    assert _pdf(navegador, id_).status_code == 200
    dependencias.cerrar_motores()
    assert _volcado(_entorno) == antes


# --- acceso: el del Excel (X1) -------------------------------------------------------------------


def test_sin_sesion_es_401(app: FastAPI) -> None:
    respuesta = cliente(app).get(f"/v1/hoja/borradores/{'a' * 22}/pdf")
    assert respuesta.status_code == 401
    assert respuesta.headers["cache-control"] == "no-store"


def test_la_clave_de_api_no_saca_el_pdf(app: FastAPI) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    id_ = _abrir(navegador, ficha)
    respuesta = cliente(app).get(
        f"/v1/hoja/borradores/{id_}/pdf", headers={CABECERA: crear_clave_de_prueba()}
    )
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": SOLO_CUENTA}


def test_el_administrador_no_lo_saca_y_quien_revisa_saca_el_suyo_y_no_el_ajeno(
    app: FastAPI,
) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    id_ana = _abrir(navegador, ficha)
    admin, _ = con_cuenta(app, "admin")
    negado = _pdf(admin, id_ana)
    assert negado.status_code == 403 and negado.json() == {"detalle": MENSAJE_PERMISO}
    rita, ficha_rita = con_cuenta(app, "rita")
    assert _pdf(rita, id_ana).status_code == 404
    propio = _pdf(rita, _abrir(rita, ficha_rita))
    assert propio.status_code == 200 and propio.headers["content-type"] == PDF


def test_una_partida_demasiado_larga_es_422_sin_eco(app: FastAPI) -> None:
    navegador, ficha = con_cuenta(app, "ana")
    centinela = "CENTINELA-" * 30
    respuesta = _pdf(navegador, _abrir(navegador, ficha), partida=centinela)
    assert respuesta.status_code == 422
    assert "CENTINELA" not in respuesta.text
