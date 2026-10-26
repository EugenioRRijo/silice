"""`POST /v1/composicion/prever` y el 409 de `POST /v1/composicion/guardar` (MP-1, Tarea 3).

Contrato del plan (`docs/planes/PLAN_MONTAR_PRESUPUESTO.md`, Tarea 3): `prever` (quien arma)
recibe el mismo cuerpo que `guardar` y responde `{lista: {nombre, moneda, fecha}, lista_nueva,
variantes: [{descripcion, unidad, precio_en_lista, precio_tecleado, codigo_variante}]}` sin dejar
nada escrito; `guardar` y `prever` responden 409 con el mensaje de `SinListaParaArmar` (sin lista
para armar, o la vigente en otra moneda que la carpeta: el foco 1 del plan). Los montos viajan como
texto con punto; un 422 de forma no repite lo enviado.

El router se monta aquí en una aplicación propia con el de la sesión y el manejador de errores de
`api.main` (como `tests/unit/test_api_busqueda.py`): la cadena de acceso de la aplicación real la
vigila `tests/unit/test_api_acceso_por_ruta.py` cuando gana su fila. El caso es una base temporal
en `tmp_path` (nunca `data/`), preparada con `preparar_base` y sembrada con los datos ficticios de
`tests/fixtures/lista_de_julio.py`. Oráculos escritos a mano.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import manejar_http_exception
from api.proteccion import proteger
from api.rutas import composicion, sesion
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures.lista_de_julio import (
    CONDICIONES,
    DE_HOY,
    MAPREX,
    OTRA_MONEDA,
    PRECIOS_DE_JULIO,
    SIN_LISTA,
    codigos_de_insumos,
    cuentas,
    nombres_de_listas,
    precios_de,
    sembrar,
)
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

PREVER = "/v1/composicion/prever"
GUARDAR = "/v1/composicion/guardar"
MURO = "PRU-01-MUR"
MENSAJE_FORMA = (
    "La composición enviada no tiene la forma esperada: revise la cabecera, las tres tablas, la "
    "fecha y las condiciones."
)


def _aplicacion() -> FastAPI:
    """El router de Componer y el de la sesión para entrar, con el mismo formato de error
    (`{"detalle": ...}`) y la misma protección que `api.main.app`."""
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(HTTPException, manejar_http_exception)
    aplicacion.include_router(sesion.router)
    aplicacion.include_router(composicion.router)
    proteger(aplicacion)
    return aplicacion


APLICACION = _aplicacion()


def _caso(ruta: Path, moneda_declarada: str | None = None) -> Path:
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            sembrar(s, moneda_declarada=moneda_declarada)
            s.commit()
    finally:
        motor.dispose()
    return ruta


def _leer(ruta: Path, consulta):
    """Lo que hay confirmado en el caso, leído con un motor propio."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            return consulta(s)
    finally:
        motor.dispose()


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("api_composicion_prever"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> Iterator[None]:
    copiar_instalacion(_plantilla)
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


def _usar(ruta: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
    return ruta


@pytest.fixture
def caso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return _usar(_caso(tmp_path / "caso.db"), monkeypatch)


@pytest.fixture
def caso_usd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Foco 1: la carpeta trabaja en USD y su lista vigente está en Bs."""
    return _usar(_caso(tmp_path / "caso.db", moneda_declarada="USD"), monkeypatch)


@pytest.fixture
def ana() -> tuple[TestClient, dict[str, str]]:
    navegador, ficha = con_cuenta(APLICACION, "ana")
    return navegador, protegida(ficha)


def _cuerpo(precio: str = "20,00", fecha: str = "2026-10-25", **extra) -> dict:
    return {
        "codigo": MURO,
        "descripcion": "Muro ficticio de bloques",
        "unidad": "m2",
        "dominio": "civil",
        "rendimiento": "10",
        "materiales": [
            {"descripcion": "Cemento gris", "unidad": "saco", "cantidad": "0,25", "precio": precio}
        ],
        "equipos": [],
        "mano_obra": [],
        "fecha": fecha,
        "condiciones": CONDICIONES,
        **extra,
    }


VARIANTE_DEL_CEMENTO = {
    "descripcion": "Cemento gris",
    "unidad": "saco",
    "precio_en_lista": "18.00",
    "precio_tecleado": "20.00",
    "codigo_variante": "MAT-001-B",
}


# --- prever ---------------------------------------------------------------------------------------


def test_prever_avisa_la_variante_y_la_lista_de_hoy_sin_escribir(caso: Path, ana) -> None:
    navegador, cabeceras = ana
    antes = _leer(caso, cuentas)

    respuesta = navegador.post(PREVER, json=_cuerpo(), headers=cabeceras)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "lista": {"nombre": DE_HOY, "moneda": "Bs", "fecha": "2026-10-25"},
        "lista_nueva": True,
        "variantes": [VARIANTE_DEL_CEMENTO],
    }
    assert _leer(caso, cuentas) == antes
    assert _leer(caso, nombres_de_listas) == [MAPREX]
    assert "MAT-001-B" not in _leer(caso, codigos_de_insumos)
    # prever dos veces dice lo mismo: la primera no dejó nada
    assert navegador.post(PREVER, json=_cuerpo(), headers=cabeceras).json() == respuesta.json()


def test_prever_sin_variante_en_la_lista_de_hoy_que_ya_existe(caso: Path, ana) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(
        PREVER, json=_cuerpo(precio="18,00", fecha="2026-07-01"), headers=cabeceras
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "lista": {"nombre": MAPREX, "moneda": "Bs", "fecha": "2026-07-01"},
        "lista_nueva": False,
        "variantes": [],
    }


def test_guardar_deja_el_precio_en_la_lista_de_hoy(caso: Path, ana) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(GUARDAR, json=_cuerpo(), headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert _leer(caso, nombres_de_listas) == [MAPREX, DE_HOY]
    assert _leer(caso, lambda s: precios_de(s, MAPREX)) == PRECIOS_DE_JULIO
    hoy = _leer(caso, lambda s: precios_de(s, DE_HOY))
    assert hoy == {**PRECIOS_DE_JULIO, "MAT-001-B": Decimal("20.00")}
    assert str(hoy["MAT-001-B"]) == "20.00"  # la escala tecleada se conserva


@pytest.mark.parametrize("ruta", [GUARDAR, PREVER])
def test_foco_1_carpeta_en_usd_con_la_vigente_en_bs_es_409_y_nada_escrito(
    caso_usd: Path, ana, ruta: str
) -> None:
    navegador, cabeceras = ana
    antes = _leer(caso_usd, cuentas)
    respuesta = navegador.post(ruta, json=_cuerpo(), headers=cabeceras)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": OTRA_MONEDA}
    assert _leer(caso_usd, cuentas) == antes


@pytest.mark.parametrize("ruta", [GUARDAR, PREVER])
def test_sin_lista_para_armar_es_409_con_su_mensaje(caso: Path, ana, ruta: str) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(ruta, json=_cuerpo(fecha="2026-06-30"), headers=cabeceras)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": SIN_LISTA}


def test_prever_sin_condiciones_es_422_con_el_mensaje_de_guardar(caso: Path, ana) -> None:
    navegador, cabeceras = ana
    respuesta = navegador.post(PREVER, json=_cuerpo(condiciones="  "), headers=cabeceras)
    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detalle": (
            "Las condiciones del rendimiento son obligatorias para guardar: Sílice no guarda una "
            "composición sin decir en qué condiciones se obtuvo su rendimiento."
        )
    }


def test_prever_un_cuerpo_sin_forma_es_422_sin_eco(caso: Path, ana) -> None:
    navegador, cabeceras = ana
    secreto = "dominio-inventado-que-no-debe-volver"
    respuesta = navegador.post(PREVER, json=_cuerpo(dominio=secreto), headers=cabeceras)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_FORMA}
    assert secreto not in respuesta.text


# --- acceso ---------------------------------------------------------------------------------------


def test_quien_revisa_no_puede_prever(caso: Path) -> None:
    navegador, ficha = con_cuenta(APLICACION, "rita")
    respuesta = navegador.post(PREVER, json=_cuerpo(), headers=protegida(ficha))
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}


def test_prever_sin_csrf_con_la_cookie_es_403(caso: Path) -> None:
    navegador, _ = con_cuenta(APLICACION, "ana")
    respuesta = navegador.post(PREVER, json=_cuerpo(), headers={"Origin": "http://127.0.0.1:8000"})
    assert respuesta.status_code == 403
