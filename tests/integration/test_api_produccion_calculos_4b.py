"""`/v1/produccion/calculos` tras las respuestas de Eugenio (plan vial, Tarea 4b: P16 y P22).

Datos FICTICIOS: la planta de noviembre de 2026 de `tests/fixtures/costo_propio.py`, sembrada en la
instalacion con los servicios, y una lista en USD en la carpeta del caso. Oraculos a mano: el
calculo da `AGR-12` 5, `AGR-34` 5 y `MZ-1` 50,70. Un mes con costos y sin produccion se calcula
(201, ningun producto) y no se publica (422). Cada calculo se publica una sola vez: el segundo
intento es 409 y no escribe nada; si la carpeta no se puede confirmar, la instalacion tampoco
guarda la publicacion.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api import dependencias
from core import models
from operacion.base_datos import preparar_base
from operacion.config import ruta_caso_por_defecto
from operacion.instalacion import sesion_de_instalacion
from produccion.modelo import PublicacionRegistrada
from seguridad import cuentas, empresas
from tests.fixtures import costo_propio as cp
from tests.fixtures.hoja_versiones_api import base
from tests.fixtures.produccion_api import Web, cliente_con_clave, contar
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

CALCULOS = "/v1/produccion/calculos"
HORA_DEL_SERVIDOR = datetime(2026, 12, 1, 7, 30, 0)
EMPRESA = ("Constructora Ejemplo, C.A.", "J-00000000-0")


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_produccion"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    copiar_instalacion(_instalacion_migrada)
    yield
    cuentas.FRENO.reiniciar()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


@pytest.fixture
def http() -> TestClient:
    return cliente_con_clave()


def _sembrar(*, produccion: bool = True) -> None:
    """Costos (y, si `produccion`, la planta) en la instalacion, la empresa en Administracion y la
    lista en USD en la carpeta del caso."""
    with sesion_de_instalacion() as ins:
        if produccion:
            cp.planta(ins)
        else:
            cp.materiales(ins)
        cp.costos_usd(ins)
        ins.commit()
        empresas.guardar_empresa_propia(ins, *EMPRESA, "Ciudad ficticia", "admin", cp.AHORA)
    ruta = ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    with base(ruta) as caso:
        cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
        caso.commit()


def _calcular(http, periodo: str = "2026-11") -> dict:
    r = http.post(CALCULOS, json={"periodo": periodo, "moneda": "USD"})
    assert r.status_code == 201, r.text
    return r.json()


def _listas() -> int:
    with base(ruta_caso_por_defecto()) as caso:
        return caso.scalar(select(func.count()).select_from(models.ListaPrecios)) or 0


# --- P16: un mes sin produccion se calcula y no se publica ----------------------------------------


def test_mes_sin_produccion_se_calcula_y_no_se_publica(http) -> None:
    _sembrar(produccion=False)
    calculo = _calcular(http)
    assert calculo["productos"] == []
    pasa = calculo["instantanea"]["resultado"]["pasa_al_mes_siguiente"]
    assert (pasa["cantera"]["total"], pasa["planta"]["total"]) == ("1000", "1200")
    antes = _listas()
    r = Web("admin").post(f"{CALCULOS}/{calculo['id']}/publicar", json={})
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == "Este cálculo no tiene costos por tonelada que publicar."
    assert _listas() == antes and contar(PublicacionRegistrada) == 0


# --- P22: una sola publicacion --------------------------------------------------------------------


def test_publicar_dos_veces_da_409_y_no_crea_otra_lista(http) -> None:
    _sembrar()
    calculo = _calcular(http)["id"]
    admin = Web("admin")
    primera = admin.post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert primera.status_code == 201, primera.text
    lista = primera.json()["id"]
    antes = _listas()
    segunda = admin.post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert segunda.status_code == 409, segunda.text
    assert segunda.json()["detalle"] == (
        f"El cálculo n.º {calculo} ya se publicó en la lista n.º {lista}."
    )
    assert _listas() == antes and contar(PublicacionRegistrada) == 1


def test_si_falla_la_lista_no_queda_publicacion(http, monkeypatch) -> None:
    """Fallo forzado al confirmar la carpeta del caso: la instalacion se confirma despues, asi que
    tampoco guarda la publicacion; el calculo se puede publicar luego."""
    _sembrar()
    calculo = _calcular(http)["id"]
    antes = _listas()
    carpeta = ruta_caso_por_defecto().resolve()
    confirmar = Session.commit

    def commit_que_falla_en_la_carpeta(sesion: Session) -> None:
        archivo = sesion.get_bind().url.database or ""
        if archivo and Path(archivo).resolve() == carpeta:
            raise RuntimeError("fallo forzado al confirmar la carpeta del caso")
        confirmar(sesion)

    monkeypatch.setattr(Session, "commit", commit_que_falla_en_la_carpeta)
    r = Web("admin").post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert r.status_code == 500, r.text
    monkeypatch.undo()
    assert _listas() == antes and contar(PublicacionRegistrada) == 0
    otra_vez = Web("admin").post(f"{CALCULOS}/{calculo}/publicar", json={})
    assert otra_vez.status_code == 201, otra_vez.text
    assert contar(PublicacionRegistrada) == 1


# --- La lista de calculos y su publicacion --------------------------------------------------------


def test_lista_de_calculos_por_periodo_y_su_publicacion(http, monkeypatch) -> None:
    monkeypatch.setattr("api.rutas.produccion._ahora", lambda: HORA_DEL_SERVIDOR)
    _sembrar()
    primero = _calcular(http)
    segundo = _calcular(http)
    lista = Web("admin").post(f"{CALCULOS}/{primero['id']}/publicar", json={}).json()["id"]
    r = http.get(CALCULOS, params={"periodo": "2026-11"})
    assert r.status_code == 200, r.text
    filas = r.json()
    assert [f["id"] for f in filas] == [segundo["id"], primero["id"]]  # la mas reciente primero
    assert filas[0]["publicado"] is None
    assert filas[1]["publicado"] == {
        "lista_id": lista,
        "caso": ruta_caso_por_defecto().name,
        "registrado": "2026-12-01T07:30:00",
    }
    assert {k: filas[1][k] for k in ("periodo", "moneda", "usuario", "huella", "registrado")} == {
        k: primero[k] for k in ("periodo", "moneda", "usuario", "huella", "registrado")
    }
    assert [f["id"] for f in http.get(CALCULOS).json()] == [segundo["id"], primero["id"]]
    assert http.get(CALCULOS, params={"periodo": "2026-10"}).json() == []
    detalle = http.get(f"{CALCULOS}/{primero['id']}").json()
    assert detalle["publicado"] == filas[1]["publicado"]
    assert http.get(f"{CALCULOS}/{segundo['id']}").json()["publicado"] is None


def test_la_lista_con_un_periodo_invalido_es_422(http) -> None:
    r = http.get(CALCULOS, params={"periodo": "2026-13"})
    assert r.status_code == 422, r.text


def test_quien_solo_revisa_recibe_403(http) -> None:
    _sembrar()
    _calcular(http)
    r = Web("rita").get(CALCULOS)
    assert r.status_code == 403, r.text
    assert Web("ana").get(CALCULOS).status_code == 200
