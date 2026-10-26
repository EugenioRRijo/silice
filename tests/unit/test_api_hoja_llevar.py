"""Elaborar lleva sus ítems a la Hoja de la obra (Tarea 12 del plan de montar un presupuesto).

Contrato (plan `docs/planes/PLAN_MONTAR_PRESUPUESTO.md`, Tarea 12):

- `POST /v1/hoja/llevar` (`editar_hoja`, solo con una cuenta) cuerpo `{proyecto, partidas: [{codigo,
  cantidad, calculo: ""}]}` → 200 `{borrador_id}`: usa el borrador vivo de esa ficha y obra o abre
  uno sobre la versión vigente (o en blanco), y agrega cada ítem con `agregar` de la Tarea 9, todo
  o nada; no guarda versión.
- La cantidad viaja como sale del cómputo de Elaborar (texto de máquina con punto decimal, como
  `POST /presupuestos/calcular`): «1.125» es uno coma ciento veinticinco, nunca mil ciento
  veinticinco (bitácora de la coma decimal). En la Hoja se ve con coma.

Datos FICTICIOS: la carpeta en Bs de `tests/fixtures/carpeta_bs_con_obras.py` (OBRA-01 a OBRA-06,
la obra VIVIENDA en Bs y CASA_USD en USD). Oráculos a mano: los textos del plan y de la Tarea 9, las
claves `a-mano:n` de la Tarea 8 y los recuentos con `sqlite3`.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.rutas import hoja as rutas_hoja
from api.rutas import hoja_llevar as rutas_llevar
from aplicacion import hoja_borradores
from operacion import config
from tests.fixtures.app_de_prueba import app_con
from tests.fixtures.carpeta_bs_con_obras import CASA_USD, VIVIENDA, carpeta_en_bs
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

APP = app_con(rutas_hoja.router, rutas_llevar.router)
RUTA = "/v1/hoja/llevar"
HOY = date(2026, 10, 25)
ORIGEN = "http://127.0.0.1:8000"
CENTINELA = "VALOR-CENTINELA"

FUERA_DEL_CATALOGO = "La partida «OBRA-99» no está en el catálogo: compóngala primero en Componer."
SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar."
SOLO_CUENTA = "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."
SIN_OBRA = "Esa obra no está en esta carpeta de trabajo: elíjala de nuevo en el selector de obra."
FORMA_LLEVAR = (
    "Lo que se lleva a la Hoja no tiene la forma esperada: envíe la obra y de 1 a 2000 partidas, "
    "cada una con su código y su cantidad tal como salen del cómputo."
)


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_hoja_llevar")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "bs": carpeta_en_bs(carpeta / "bs.db", con_tasa=False),
        "bs_con_tasa": carpeta_en_bs(carpeta / "bs_con_tasa.db", con_tasa=True),
    }


@pytest.fixture(autouse=True)
def _entorno(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalación con cuentas y la carpeta en Bs con tasa como caso por defecto; hoy es el
    25/10/2026 para la Hoja y para llevar."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)
    monkeypatch.setattr(rutas_llevar, "_hoy", lambda: HOY)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["bs_con_tasa"], ruta)
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    dependencias.cerrar_motores()


def _poner(origen: Path) -> Path:
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(origen, ruta)
    return ruta


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _consulta(ruta: Path, sql: str, *parametros) -> list[tuple]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        return bd.execute(sql, parametros).fetchall()


def _codigo_de(ruta: Path, nombre: str) -> str:
    """El código de la obra que da `GET /v1/proyectos` (el que guarda el selector de obra)."""
    ((id_,),) = _consulta(ruta, "SELECT id FROM proyecto WHERE nombre = ?", nombre)
    return str(id_)


def _ana() -> tuple[TestClient, str]:
    return con_cuenta(APP, "ana")


def _llevar(navegador: TestClient, ficha: str, proyecto: str, partidas: list[dict]):
    return navegador.post(
        RUTA, json={"proyecto": proyecto, "partidas": partidas}, headers=protegida(ficha)
    )


def _partida(codigo: str, cantidad: str) -> dict:
    return {"codigo": codigo, "cantidad": cantidad, "calculo": ""}


def _borradores(navegador: TestClient) -> list[dict]:
    respuesta = navegador.get("/v1/hoja/borradores")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["borradores"]


def _filas(navegador: TestClient, id_: str) -> list[tuple[str, str]]:
    respuesta = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/presupuesto")
    assert respuesta.status_code == 200, respuesta.text
    return [(f["clave"], f["cantidad"]) for f in respuesta.json()["filas"]]


def _resumen(navegador: TestClient, id_: str) -> dict:
    respuesta = navegador.get(f"/v1/hoja/borradores/{id_}")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["resumen"]


def _abierto(navegador: TestClient, ficha: str, version: str | None = None) -> str:
    respuesta = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": VIVIENDA, "version": version},
        headers=protegida(ficha),
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _agregar(navegador: TestClient, ficha: str, id_: str, rev: int, codigo: str, cantidad: str):
    return navegador.post(
        f"/v1/hoja/borradores/{id_}/partidas",
        json={"rev": rev, "codigo": codigo, "cantidad": cantidad, "calculo": "", "nota": ""},
        headers=protegida(ficha),
    )


# --- lleva las partidas al borrador, sin guardar versión ----------------------------------------


def test_llevar_dos_partidas_a_una_obra_sin_versiones_abre_un_borrador_con_dos_altas(
    _entorno: Path,
) -> None:
    navegador, ficha = _ana()
    antes = _volcado(_entorno)

    respuesta = _llevar(
        navegador,
        ficha,
        _codigo_de(_entorno, VIVIENDA),
        [_partida("OBRA-04", "210"), _partida("OBRA-06", "1.125")],
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert list(cuerpo) == ["borrador_id"]
    id_ = cuerpo["borrador_id"]
    ((borrador,),) = [[b] for b in _borradores(navegador)]
    assert (borrador["id"], borrador["proyecto"], borrador["version"]) == (id_, VIVIENDA, None)
    assert (borrador["cambios"], borrador["rev"]) == (2, 2)
    # «1.125» del cómputo es uno coma ciento veinticinco: en la Hoja se ve con coma
    assert _filas(navegador, id_) == [("OBRA-04|a-mano:1", "210"), ("OBRA-06|a-mano:2", "1,125")]
    cambios = navegador.get(f"/v1/hoja/borradores/{id_}/cambios").json()["cambios"]
    assert [(c["objeto"], c["clave"], c["campo"]) for c in cambios] == [
        ("cantidad", "OBRA-04|a-mano:1", "alta"),
        ("cantidad", "OBRA-06|a-mano:2", "alta"),
    ]
    assert _resumen(navegador, id_)["moneda"] == "Bs"
    assert _volcado(_entorno) == antes  # ninguna versión, ninguna fila: solo el borrador en memoria


def test_llevar_usa_el_borrador_vivo_de_la_obra_y_sigue_su_numeracion() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, 0, "OBRA-01", "80").status_code == 200

    respuesta = _llevar(navegador, ficha, VIVIENDA, [_partida("OBRA-04", "140")])

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"borrador_id": id_}
    assert [b["id"] for b in _borradores(navegador)] == [id_]
    assert _filas(navegador, id_) == [("OBRA-01|a-mano:1", "80"), ("OBRA-04|a-mano:2", "140")]
    resumen = _resumen(navegador, id_)
    assert (resumen["rev"], resumen["cambios"]) == (2, 2)


def test_con_versiones_abre_la_vigente_y_no_guarda_otra(_entorno: Path) -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, 0, "OBRA-04", "140").status_code == 200
    guardado = navegador.post(
        f"/v1/hoja/borradores/{id_}/guardar",
        json={"rev": 1, "fuente": "Medición del 24/10/2026", "codigo": "VIV-001"},
        headers=protegida(ficha),
    )
    assert guardado.status_code == 200, guardado.text

    respuesta = _llevar(navegador, ficha, VIVIENDA, [_partida("OBRA-06", "280")])

    assert respuesta.status_code == 200, respuesta.text
    nuevo = respuesta.json()["borrador_id"]
    assert nuevo != id_
    ((borrador,),) = [[b] for b in _borradores(navegador)]
    assert (borrador["id"], borrador["version"], borrador["cambios"]) == (nuevo, "VIV-001", 1)
    assert [clave for clave, _ in _filas(navegador, nuevo)] == [
        "OBRA-04|a-mano:1",
        "OBRA-06|a-mano:2",
    ]
    assert _consulta(
        _entorno,
        "SELECT pr.codigo FROM presupuesto pr JOIN proyecto p ON p.id = pr.proyecto_id "
        "WHERE p.nombre = ?",
        VIVIENDA,
    ) == [("VIV-001",)]


# --- todo o nada --------------------------------------------------------------------------------


def test_un_codigo_que_no_esta_en_el_catalogo_es_404_y_no_deja_borrador(_entorno: Path) -> None:
    navegador, ficha = _ana()
    antes = _volcado(_entorno)

    respuesta = _llevar(
        navegador, ficha, VIVIENDA, [_partida("OBRA-04", "210"), _partida("OBRA-99", "1")]
    )

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": FUERA_DEL_CATALOGO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert _borradores(navegador) == []
    assert _volcado(_entorno) == antes


def test_un_codigo_que_no_esta_deja_el_borrador_vivo_como_estaba_y_con_su_rev() -> None:
    navegador, ficha = _ana()
    id_ = _abierto(navegador, ficha)
    assert _agregar(navegador, ficha, id_, 0, "OBRA-01", "80").status_code == 200

    respuesta = _llevar(
        navegador, ficha, VIVIENDA, [_partida("OBRA-04", "140"), _partida("OBRA-99", "1")]
    )

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": FUERA_DEL_CATALOGO}
    resumen = _resumen(navegador, id_)
    assert (resumen["rev"], resumen["cambios"]) == (1, 1)
    assert _filas(navegador, id_) == [("OBRA-01|a-mano:1", "80")]
    # la ventana que vio el rev 1 sigue pudiendo editar: nada cambió para ella
    siguiente = _agregar(navegador, ficha, id_, 1, "OBRA-06", "280")
    assert siguiente.status_code == 200, siguiente.text
    assert siguiente.json()["clave"] == "OBRA-06|a-mano:2"


def test_sin_tasa_una_obra_en_usd_es_409_y_no_deja_nada(_casos: dict[str, Path]) -> None:
    ruta = _poner(_casos["bs"])
    navegador, ficha = _ana()
    antes = _volcado(ruta)

    respuesta = _llevar(navegador, ficha, CASA_USD, [_partida("OBRA-04", "210")])

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": SIN_TASA}
    assert _borradores(navegador) == []
    assert _volcado(ruta) == antes


def test_una_obra_que_no_existe_es_404_sin_eco() -> None:
    navegador, ficha = _ana()

    respuesta = _llevar(navegador, ficha, CENTINELA, [_partida("OBRA-04", "210")])

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": SIN_OBRA}
    assert CENTINELA not in respuesta.text
    assert _borradores(navegador) == []


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"proyecto": VIVIENDA, "partidas": []},
        {"proyecto": "", "partidas": [_partida("OBRA-04", "1")], "x": CENTINELA},
        {"proyecto": VIVIENDA, "partidas": [_partida(CENTINELA, "2,5")]},
        {"proyecto": VIVIENDA, "partidas": [_partida(CENTINELA, "-1")]},
        {"proyecto": VIVIENDA, "partidas": [_partida(CENTINELA, "1e3")]},
        {"proyecto": VIVIENDA, "partidas": [_partida(CENTINELA, " 2")]},
        {"proyecto": VIVIENDA, "partidas": [_partida(CENTINELA, "")]},
        {"proyecto": VIVIENDA, "partidas": [{"codigo": CENTINELA, "cantidad": 2}]},
        {"proyecto": VIVIENDA, "partidas": [{**_partida("", "1"), "nota": CENTINELA}]},
        {"proyecto": CENTINELA, "partidas": [_partida("OBRA-04", "1")] * 2001},
    ],
    ids=[
        "sin_partidas",
        "sin_obra",
        "coma",
        "negativa",
        "exponente",
        "blanco",
        "vacia",
        "numero",
        "campo_de_mas",
        "demasiadas",
    ],
)
def test_la_forma_mala_es_422_sin_eco(cuerpo: dict) -> None:
    navegador, ficha = _ana()

    respuesta = navegador.post(RUTA, json=cuerpo, headers=protegida(ficha))

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": FORMA_LLEVAR}
    assert CENTINELA not in respuesta.text
    assert _borradores(navegador) == []


# --- acceso: solo una cuenta con editar_hoja, CSRF y Origin -------------------------------------

CUERPO = {"proyecto": VIVIENDA, "partidas": [_partida("OBRA-04", "210")]}


def test_sin_sesion_es_401_y_quien_revisa_no_puede() -> None:
    anonimo = cliente(APP).post(RUTA, json=CUERPO, headers={"Origin": ORIGEN})
    assert anonimo.status_code == 401
    rita, ficha = con_cuenta(APP, "rita")
    revisa = rita.post(RUTA, json=CUERPO, headers=protegida(ficha))
    assert revisa.status_code == 403 and revisa.json() == {"detalle": MENSAJE_PERMISO}


def test_la_clave_de_api_no_lleva_nada() -> None:
    respuesta = cliente(APP).post(
        RUTA, json=CUERPO, headers={CABECERA: crear_clave_de_prueba(), "Origin": ORIGEN}
    )
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": SOLO_CUENTA}


def test_llevar_exige_csrf_y_origen_propio() -> None:
    navegador, ficha = _ana()
    assert navegador.post(RUTA, json=CUERPO, headers={"Origin": ORIGEN}).status_code == 403
    ajeno = protegida(ficha, origen="http://evil.example")
    assert navegador.post(RUTA, json=CUERPO, headers=ajeno).status_code == 403
    assert navegador.post(RUTA, json=CUERPO, headers=protegida(ficha, None)).status_code == 403
    assert _borradores(navegador) == []
