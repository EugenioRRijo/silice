"""El libro por frentes en la API (ola 2, línea 3, 2026-11-13; las reglas las prueba
`tests/unit/test_libro_por_frentes.py`).

- `POST /v1/libros/apu-por-hoja` acepta `hoja_presupuesto` (uno o varios, aparte del perfil) y el
  informe dice todas las hojas leídas (`hojas_presupuesto`).
- `POST /v1/libros/hojas`: las hojas de un libro subido, para elegirlas (no lee ninguna celda).
- `GET /v1/libros/perfiles-apu-por-hoja` dice todas las hojas de cada perfil.
- `POST /v1/admin/empresa/perfiles-libros`: quien administra pone un perfil local desde la
  interfaz (antes se copiaba a mano en `<carpeta de datos>/perfiles_libros/`).

Sobre `api.main.app` real, con la instalación de cuentas de `tests/fixtures/sesion_web.py`. Libros
y perfiles FICTICIOS.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from operacion import config
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.libro_apu_por_hoja import libro_apu, libro_presupuesto_por_hojas
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

RUTA_APU = "/v1/libros/apu-por-hoja"
RUTA_HOJAS = "/v1/libros/hojas"
RUTA_PERFILES = "/v1/libros/perfiles-apu-por-hoja"
RUTA_PONER = "/v1/admin/empresa/perfiles-libros"
PAQUETE = Path(__file__).resolve().parents[2] / "adapters/hoja_empresa/perfiles/apu_por_hoja.json"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("libros_frentes"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> Iterator[None]:
    copiar_instalacion(_plantilla)
    yield


def _con_clave() -> TestClient:
    return TestClient(
        app,
        base_url=ANFITRION,
        client=IP_LOCAL,
        raise_server_exceptions=False,
        headers={CABECERA: crear_clave_de_prueba()},
    )


def _auditar(cliente: TestClient, hojas: list[str] | None = None):
    return cliente.post(
        RUTA_APU,
        files={
            "libro": ("obra_a.xlsx", libro_apu()),
            "presupuesto": ("frentes.xlsx", libro_presupuesto_por_hojas()),
        },
        data={} if hojas is None else {"hoja_presupuesto": hojas},
    )


def test_las_hojas_elegidas_viajan_aparte_del_perfil():
    r = _auditar(_con_clave(), ["FRENTE A", "FRENTE B"])
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["perfil"], cuerpo["hoja_presupuesto"]) == ("apu_por_hoja", "FRENTE A")
    assert cuerpo["hojas_presupuesto"] == ["FRENTE A", "FRENTE B"]
    celdas = [h["celda"] for h in cuerpo["hallazgos"] if h["celda"].startswith("FRENTE")]
    assert celdas == ["FRENTE A!E6", "FRENTE A!F8", "FRENTE A!A9", "FRENTE B!F8", "FRENTE B!A9"]


def test_sin_elegir_hojas_vale_la_del_perfil():
    r = _auditar(_con_clave())
    assert r.status_code == 422
    assert r.json()["detalle"] == (
        "El libro «frentes.xlsx» no tiene la hoja PRESUPUESTO: sus hojas son FRENTE A y FRENTE B."
    )


def test_las_hojas_de_un_libro_subido():
    r = _con_clave().post(
        RUTA_HOJAS, files={"libro": ("frentes.xlsx", libro_presupuesto_por_hojas())}
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"hojas": ["FRENTE A", "FRENTE B"]}


def test_las_hojas_de_algo_que_no_es_un_xlsx_es_415_como_en_las_demas_subidas():
    r = _con_clave().post(RUTA_HOJAS, files={"libro": ("frentes.csv", b"a;b")})
    assert r.status_code == 415


def test_la_lista_de_perfiles_dice_todas_las_hojas():
    r = _con_clave().get(RUTA_PERFILES)
    assert r.status_code == 200, r.text
    assert r.json() == [
        {
            "nombre": "apu_por_hoja",
            "origen": "paquete",
            "hoja_presupuesto": "PRESUPUESTO",
            "hojas_presupuesto": ["PRESUPUESTO"],
            "motivo": None,
        }
    ]


def _perfil(nombre: str = "obra_local", **cambios) -> bytes:
    crudo = json.loads(PAQUETE.read_text(encoding="utf-8"))
    crudo.update(nombre=nombre, **cambios)
    crudo["presupuesto"] = {
        "hojas": ["FRENTE A", "FRENTE B"],
        "encabezado": crudo["presupuesto"]["encabezado"],
    }
    return json.dumps(crudo, ensure_ascii=False).encode("utf-8")


def _poner(cliente: TestClient, ficha: str, datos: bytes, reemplazar: bool = False):
    return cliente.post(
        RUTA_PONER,
        files={"perfil": ("obra_local.json", datos, "application/json")},
        data={"reemplazar": "true" if reemplazar else "false"},
        headers=protegida(ficha),
    )


def test_quien_administra_pone_un_perfil_y_se_puede_elegir():
    cliente, ficha = con_cuenta(app, "admin")
    r = _poner(cliente, ficha, _perfil())
    assert r.status_code == 201, r.text
    assert r.json() == {
        "nombre": "obra_local",
        "origen": "local",
        "hoja_presupuesto": "FRENTE A",
        "hojas_presupuesto": ["FRENTE A", "FRENTE B"],
        "motivo": None,
    }
    assert (config.carpeta_perfiles_libros() / "obra_local.json").is_file()
    nombres = [(p["nombre"], p["origen"]) for p in _con_clave().get(RUTA_PERFILES).json()]
    assert ("obra_local", "local") in nombres
    auditado = _con_clave().post(
        RUTA_APU,
        files={
            "libro": ("obra_a.xlsx", libro_apu()),
            "presupuesto": ("frentes.xlsx", libro_presupuesto_por_hojas()),
        },
        data={"perfil": "obra_local"},
    )
    assert auditado.status_code == 200, auditado.text
    assert auditado.json()["hojas_presupuesto"] == ["FRENTE A", "FRENTE B"]


def test_poner_uno_que_ya_esta_pide_reemplazar():
    cliente, ficha = con_cuenta(app, "admin")
    assert _poner(cliente, ficha, _perfil()).status_code == 201
    r = _poner(cliente, ficha, _perfil(prefijo_hoja="Partida"))
    assert r.status_code == 409
    assert r.json()["detalle"] == (
        "Ya hay un perfil «obra_local» en esta instalación: marque «Reemplazar» para cambiarlo."
    )
    otra = _poner(cliente, ficha, _perfil(prefijo_hoja="Partida"), reemplazar=True)
    assert otra.status_code == 200


def test_un_perfil_mal_escrito_es_422_y_no_se_escribe():
    cliente, ficha = con_cuenta(app, "admin")
    r = _poner(cliente, ficha, _perfil(prefijo_hoja=""))
    assert r.status_code == 422
    assert r.json()["detalle"] == "perfil 'obra_local': prefijo_hoja debe ser un texto no vacío"
    assert not (config.carpeta_perfiles_libros() / "obra_local.json").exists()


def test_quien_arma_no_pone_perfiles():
    cliente, ficha = con_cuenta(app, "ana")
    r = _poner(cliente, ficha, _perfil())
    assert r.status_code == 403
    assert r.json()["detalle"] == MENSAJE_PERMISO
