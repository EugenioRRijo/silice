"""Entregar el paquete por la API (ola 4 de la sesión 2b; UC-22, RF-85; RM-3, RM-4).

Contrato de `api/rutas/entregas.py` (paridad con `ui/paginas/entregar.py`):

- `GET /v1/entregas/versiones?proyecto=` → `[{codigo, moneda}]`, la más nueva primero.
- `GET /v1/entregas/resumen?proyecto=&version=` → lo que la pantalla muestra antes de pedir la
  contraseña: total (exacto y como lo escribe la pantalla clásica), hallazgos por severidad,
  cadena, empresa, si hay clave de firma y lo que viaja.
- `POST /v1/entregas` `{proyecto, version, destinatario?, contrasena_clave?}` → el `.silice`
  (`application/zip`) con `Content-Disposition`, `X-Silice-SHA256` y `X-Silice-Firmado`.
- `ENTREGAR_PAQUETE` (rol arma) en las tres; firmar exige además el propio equipo
  (`Sensible.FIRMAR`, RM-4). La contraseña de la clave no se guarda, no se registra y no vuelve en
  ningún cuerpo (ni en un 422).

Oráculos: el total de la memoria de MIN-001 (`836.79750000`), los mensajes literales de la
pantalla clásica y de `core.budget.cadena`, el contenido del `.silice` leído con `zipfile`, la
huella con `hashlib` y las filas de los eventos con `sqlite3` directo.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import sqlite3
import zipfile
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from aplicacion.entrega import anexos_de_cadena
from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from operacion.instalacion import sesion_de_instalacion
from seguridad import empresas
from tests.fixtures.canonico_minimo import guardar_otra, sembrar_minimo
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

CLAVE_DE_FIRMA = "frase de firma larga y propia"
EMPRESA = "Contratista Demo, C.A."
TOTAL_MEMORIA = "836.79750000"  # 20 m3 x 41,83987500 USD/m3 (tests/fixtures/canonico)
REMOTO = (
    "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."
)
CLAVE_INCORRECTA = "La contraseña de la clave no es correcta."
CADENA_ROTA = (
    "Cadena rota en la versión 001: no tiene eslabón; alguien cambió la base fuera del sistema. "
    "Revíselo con el administrador antes de entregar un paquete."
)
PRIVADO = "frase-que-nunca-debe-volver-ni-registrarse"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("entregas"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """La instalación con cuentas y el caso por defecto con MIN-001 v001 ya sellada."""
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as caso:
            sembrar_minimo(caso, anexos_de=anexos_de_cadena)
            caso.commit()  # sella la v001
    finally:
        motor.dispose()
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _con_empresa_y_clave() -> None:
    with sesion_de_instalacion() as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-00000000-0", "", "ana", AHORA)
        empresas.generar_clave(bd, CLAVE_DE_FIRMA, "ana", AHORA)


def _segunda_version(caso: Path) -> None:
    motor = crear_motor(f"sqlite:///{caso.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            proyecto = sesion.scalars(select(models.Proyecto)).one()
            lista = sesion.scalars(select(models.ListaPrecios)).one()
            guardar_otra(sesion, proyecto, lista, "002", "25", anexos_de=anexos_de_cadena)
            sesion.commit()
    finally:
        motor.dispose()


def _eventos() -> list[tuple[str, str]]:
    with closing(sqlite3.connect(config.ruta_instalacion())) as bd:
        return list(bd.execute("SELECT tipo, detalle FROM evento_acceso ORDER BY id"))


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    """Todas las filas de todas las tablas del caso, leídas con `sqlite3` directo."""
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _ana(ip: str = "127.0.0.1") -> tuple[TestClient, str]:
    return con_cuenta(app, "ana", ip=ip)


def _pedir(navegador: TestClient, ficha: str, **cuerpo):
    cuerpo.setdefault("proyecto", "MIN-001")
    cuerpo.setdefault("version", "001")
    return navegador.post("/v1/entregas", json=cuerpo, headers=protegida(ficha))


# --- acceso (RM-3) --------------------------------------------------------------------------


def test_sin_sesion_es_401_y_con_clave_de_api_pasa() -> None:
    sin = cliente(app)
    assert sin.get("/v1/entregas/versiones", params={"proyecto": "MIN-001"}).status_code == 401
    assert (
        sin.post("/v1/entregas", json={"proyecto": "MIN-001", "version": "001"}).status_code == 401
    )
    clave = {CABECERA: crear_clave_de_prueba()}
    r = sin.get("/v1/entregas/versiones", params={"proyecto": "MIN-001"}, headers=clave)
    assert r.status_code == 200


@pytest.mark.parametrize("login", ["rita", "admin"])
def test_solo_quien_arma_entrega(login: str) -> None:
    """ENTREGAR_PAQUETE es de arma: revisa y el administrador reciben el 403 del rol."""
    navegador, ficha = con_cuenta(app, login)
    pedidos = [
        navegador.get("/v1/entregas/versiones", params={"proyecto": "MIN-001"}),
        navegador.get("/v1/entregas/resumen", params={"proyecto": "MIN-001", "version": "001"}),
        _pedir(navegador, ficha),
    ]
    for r in pedidos:
        assert (r.status_code, r.json()) == (403, {"detalle": MENSAJE_PERMISO})
    assert _eventos() == [] or all(t != "paquete exportado" for t, _ in _eventos())


def test_el_post_exige_csrf() -> None:
    navegador, _ = _ana()
    r = navegador.post(
        "/v1/entregas",
        json={"proyecto": "MIN-001", "version": "001"},
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    assert r.status_code == 403


# --- versiones y resumen --------------------------------------------------------------------


def test_las_versiones_van_de_la_mas_nueva_a_la_mas_vieja(_entorno: Path) -> None:
    _segunda_version(_entorno)
    navegador, _ = _ana()
    r = navegador.get("/v1/entregas/versiones", params={"proyecto": "MIN-001"})
    assert r.status_code == 200
    assert r.json() == [{"codigo": "002", "moneda": "USD"}, {"codigo": "001", "moneda": "USD"}]


def test_un_proyecto_o_una_version_que_no_existe_es_404() -> None:
    navegador, _ = _ana()
    assert navegador.get("/v1/entregas/versiones", params={"proyecto": "NO"}).status_code == 404
    r = navegador.get("/v1/entregas/resumen", params={"proyecto": "MIN-001", "version": "009"})
    assert r.status_code == 404
    assert "009" in r.json()["detalle"]


def test_el_resumen_sin_empresa_ni_clave() -> None:
    navegador, _ = _ana()
    r = navegador.get("/v1/entregas/resumen", params={"proyecto": "MIN-001", "version": "001"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["proyecto"] == "MIN-001" and cuerpo["version"] == "001"
    assert cuerpo["moneda"] == "USD"
    assert cuerpo["total"] == TOTAL_MEMORIA  # exacto, como texto
    assert cuerpo["total_texto"] == "836.8"  # como la pantalla clásica: 2 decimales y sin ceros
    assert cuerpo["hallazgos_total"] == 0 and cuerpo["hallazgos_por_severidad"] == {}
    assert cuerpo["cadena_integra"] is True
    assert cuerpo["empresa"] is None and cuerpo["firma_disponible"] is False
    assert cuerpo["viaja_con"] == ["presupuesto", "informe", "cadena"]


def test_el_resumen_con_empresa_y_clave_de_firma() -> None:
    _con_empresa_y_clave()
    navegador, _ = _ana()
    cuerpo = navegador.get(
        "/v1/entregas/resumen", params={"proyecto": "MIN-001", "version": "001"}
    ).json()
    assert cuerpo["empresa"] == EMPRESA and cuerpo["firma_disponible"] is True


def test_una_cadena_rota_se_dice_y_no_deja_entregar() -> None:
    with closing(sqlite3.connect(config.ruta_caso_por_defecto())) as bd:
        bd.execute("DELETE FROM eslabon_version")
        bd.commit()
    navegador, ficha = _ana()
    cuerpo = navegador.get(
        "/v1/entregas/resumen", params={"proyecto": "MIN-001", "version": "001"}
    ).json()
    assert cuerpo["cadena_integra"] is False and cuerpo["mensaje_de_cadena"] == CADENA_ROTA
    r = _pedir(navegador, ficha)
    assert (r.status_code, r.json()) == (409, {"detalle": CADENA_ROTA})
    assert all(t != "paquete exportado" for t, _ in _eventos())


# --- entregar -------------------------------------------------------------------------------


def test_sin_clave_de_firma_el_paquete_sale_sin_firma_y_queda_registrado() -> None:
    navegador, ficha = _ana()
    antes = _volcado(config.ruta_caso_por_defecto())
    r = _pedir(navegador, ficha, destinatario="  Cliente S.A.  ")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert 'filename="MIN-001-001.silice"' in r.headers["content-disposition"]
    assert r.headers["x-silice-firmado"] == "0"
    assert r.headers["x-silice-sha256"] == hashlib.sha256(r.content).hexdigest()
    assert r.headers["cache-control"] == "no-store"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        nombres = set(z.namelist())
        manifiesto = json.loads(z.read("manifiesto.json"))
    assert {"manifiesto.json", "presupuesto.json", "informe.json", "cadena.json"} <= nombres
    assert "firma.ed25519" not in nombres
    assert manifiesto["destinatario"] == "Cliente S.A."
    eventos = _eventos()
    assert [t for t, _ in eventos if t == "paquete exportado"] == ["paquete exportado"]
    detalle = next(d for t, d in eventos if t == "paquete exportado")
    assert manifiesto["paquete_id"] in detalle and r.headers["x-silice-sha256"] in detalle
    assert "<ana>" in detalle  # el responsable es la persona de la sesión
    assert _volcado(config.ruta_caso_por_defecto()) == antes  # la base del caso no cambia


def test_con_clave_de_firma_y_contrasena_correcta_el_paquete_sale_firmado() -> None:
    _con_empresa_y_clave()
    navegador, ficha = _ana()
    r = _pedir(navegador, ficha, contrasena_clave=CLAVE_DE_FIRMA)
    assert r.status_code == 200, r.text
    assert r.headers["x-silice-firmado"] == "1"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert "firma.ed25519" in z.namelist()
    tipos = [t for t, _ in _eventos()]
    assert "firma" in tipos and "paquete exportado" in tipos


@pytest.mark.parametrize("contrasena", ["otra frase", "", None])
def test_contrasena_incorrecta_o_ausente_no_entrega_ni_registra(contrasena) -> None:
    _con_empresa_y_clave()
    navegador, ficha = _ana()
    antes = len(_eventos())  # ya con el evento de entrada de esta sesión
    cuerpo = {} if contrasena is None else {"contrasena_clave": contrasena}
    r = _pedir(navegador, ficha, **cuerpo)
    assert (r.status_code, r.json()) == (400, {"detalle": CLAVE_INCORRECTA})
    assert _eventos()[antes:] == [], _eventos()[antes:]


def test_sin_clave_de_firma_se_ignora_la_contrasena_que_llegue() -> None:
    """La pantalla clásica deshabilita el campo sin clave: el paquete sale sin firma."""
    navegador, ficha = _ana()
    r = _pedir(navegador, ficha, contrasena_clave=PRIVADO)
    assert r.status_code == 200 and r.headers["x-silice-firmado"] == "0"


def test_firmar_desde_otra_maquina_es_403_pero_entregar_sin_firma_no_lo_exige() -> None:
    navegador, ficha = _ana(ip="192.168.1.30")
    assert _pedir(navegador, ficha).status_code == 200  # sin clave: no hay nada que firmar
    _con_empresa_y_clave()
    r = _pedir(navegador, ficha, contrasena_clave=CLAVE_DE_FIRMA)
    assert (r.status_code, r.json()) == (403, {"detalle": REMOTO})
    assert [t for t, _ in _eventos() if t == "firma"] == []


def test_un_cuerpo_invalido_es_422_y_no_devuelve_lo_enviado() -> None:
    navegador, ficha = _ana()
    r = navegador.post(
        "/v1/entregas",
        json={"version": "001", "contrasena_clave": PRIVADO},
        headers=protegida(ficha),
    )
    assert r.status_code == 422
    assert PRIVADO not in r.text
    r = navegador.post(
        "/v1/entregas",
        json={"proyecto": "MIN-001", "version": 1, "contrasena_clave": PRIVADO},
        headers=protegida(ficha),
    )
    assert r.status_code == 422 and PRIVADO not in r.text


def test_la_contrasena_no_queda_en_los_registros_ni_en_los_eventos(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _con_empresa_y_clave()
    navegador, ficha = _ana()
    with caplog.at_level(logging.DEBUG):
        _pedir(navegador, ficha, contrasena_clave=CLAVE_DE_FIRMA)
        _pedir(navegador, ficha, contrasena_clave=PRIVADO)
    assert CLAVE_DE_FIRMA not in caplog.text and PRIVADO not in caplog.text
    assert all(CLAVE_DE_FIRMA not in d and PRIVADO not in d for _, d in _eventos())


def test_un_proyecto_o_version_inexistente_no_se_entrega() -> None:
    navegador, ficha = _ana()
    assert _pedir(navegador, ficha, proyecto="NO").status_code == 404
    assert _pedir(navegador, ficha, version="009").status_code == 404
