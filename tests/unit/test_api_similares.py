"""`POST /v1/similares` (migracion de «Partidas similares», sesion 2b; UC-03, RF-15 y RF-16).

Paridad con `ui/paginas/similares.py`: mismos datos, validaciones y mensajes. El modelo real no se
carga nunca: `ml.normalization.normalizador._cargar_modelo` se sustituye (falla) o se sustituye la
propuesta de `aplicacion.similares` (exito). La base es la linea base sembrada en `tmp_path`.

Oraculos a mano, con `DECIMALES_PRESENTACION = 2`: el concreto LB-04-CON rinde 8 m3/dia; su primer
material es cemento, 7.5 sacos a 15 -> «7.50» y «15.00»; el equipo carretilla lleva 2 a 30 con
depreciacion 0.03; el ayudante de mano de obra, 4 a 3. Los puntajes viajan con 4 decimales.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from api import dependencias
from api.main import app
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from ml.normalization import PartidaSimilar, Propuesta
from operacion import config
from operacion.base_datos import Destino, preparar_base
from scripts.seed import sembrar
from seguridad import cuentas, sesiones
from seguridad.base import abrir_sesion as abrir_sesion_seg
from seguridad.base import crear_motor as crear_motor_seg
from seguridad.modelo import Usuario
from tests.fixtures.apu_linea_base import APU_CONCRETO, APU_EXCAVACION
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

RUTA = "/v1/similares"
COOKIE = "silice_sesion"
NUEVA = "otra contrasena larga de prueba"
CUENTAS = {"ana": NUEVA, "rita": NUEVA}
MENSAJE_SIN_EXTRA = (
    "Las propuestas de partidas similares necesitan el extra 'similitud' (sentence-transformers): "
    "instala con 'uv sync --extra similitud' y vuelve a intentar."
)
MENSAJE_SIN_UMBRAL = (
    "Ninguna partida del catalogo supera el umbral de similitud: la partida se crearia desde cero."
)
MENSAJE_PERMISO = "Su cuenta no tiene permiso para esta acción."
DESCRIPCION = "concreto para las paredes de una tanquilla"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    carpeta = tmp_path_factory.mktemp("plantilla_similares")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor_seg(plantilla)
    sesion = abrir_sesion_seg(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        for usuario in sesion.scalars(select(Usuario)):
            sesiones.cerrar_todas(sesion, usuario.id, "plantilla")
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> Iterator[None]:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_plantilla, destino)
    cuentas.FRENO.reiniciar()
    yield
    cuentas.FRENO.reiniciar()


@pytest.fixture
def base(tmp_path: Path, monkeypatch) -> Iterator[Path]:
    """La linea base sembrada, como el caso que la API abre (`APU_BASE`)."""
    ruta = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
    monkeypatch.setattr(dependencias, "_motor", None)
    yield ruta
    if dependencias._motor is not None:
        dependencias._motor.dispose()


def _cliente(**extra) -> TestClient:
    return TestClient(
        app, base_url=ANFITRION, client=IP_LOCAL, raise_server_exceptions=False, **extra
    )


def _con_clave() -> TestClient:
    return _cliente(headers={CABECERA: crear_clave_de_prueba()})


def _con_cuenta(login: str) -> tuple[TestClient, dict[str, str]]:
    cliente = _cliente()
    r = cliente.post("/v1/sesion", json={"login": login, "contrasena": CUENTAS[login]})
    assert r.status_code == 200, r.text
    ficha = r.cookies.get(COOKIE)
    csrf = hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()
    return cliente, {"X-Silice-CSRF": csrf, "Origin": ANFITRION}


def _doble_del_modelo(monkeypatch, llamadas: list | None = None) -> None:
    def _propuesta(partidas, descripcion) -> Propuesta:
        if llamadas is not None:
            llamadas.append((dict(partidas), descripcion))
        return Propuesta(
            (
                PartidaSimilar(APU_CONCRETO.codigo_partida, APU_CONCRETO.descripcion, 0.9137),
                PartidaSimilar(APU_EXCAVACION.codigo_partida, APU_EXCAVACION.descripcion, 0.6402),
            )
        )

    monkeypatch.setattr("aplicacion.similares.sugerir_partidas_similares", _propuesta)


def _falla_del_modelo(monkeypatch, falla: Exception) -> None:
    def _cargar_modelo(*_args, **_kwargs):
        raise falla

    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _cargar_modelo)


def test_propone_con_puntaje_de_cuatro_decimales_y_el_desglose(base, monkeypatch) -> None:
    llamadas: list = []
    _doble_del_modelo(monkeypatch, llamadas)
    r = _con_clave().post(RUTA, json={"descripcion": DESCRIPCION})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["falla"] is None
    assert [p["codigo"] for p in cuerpo["propuestas"]] == ["LB-04-CON", "LB-01-EXC"]
    concreto = cuerpo["propuestas"][0]
    assert concreto["descripcion"] == APU_CONCRETO.descripcion
    assert concreto["puntaje"] == "0.9137"
    assert cuerpo["propuestas"][1]["puntaje"] == "0.6402"
    # el titulo del desplegable lleva dos decimales (como la pagina de Streamlit)
    assert concreto["puntaje_corto"] == "0.91"
    assert cuerpo["propuestas"][1]["puntaje_corto"] == "0.64"
    assert concreto["aviso"] is None
    comp = concreto["composicion"]
    assert comp["unidad"] == "m3"
    assert comp["rendimiento"] == "8.00"
    assert comp["materiales"][0] == {
        "descripcion": "Cemento Portland",
        "unidad": "saco",
        "cantidad": "7.50",
        "precio": "15.00",
    }
    carretilla = next(e for e in comp["equipos"] if e["descripcion"] == "Carretilla")
    assert carretilla == {
        "descripcion": "Carretilla",
        "cantidad": "2.00",
        "precio": "30.00",
        "depreciacion": "0.03",
    }
    ayudante = next(m for m in comp["mano_obra"] if m["descripcion"] == "Ayudante")
    assert ayudante == {"descripcion": "Ayudante", "cantidad": "4.00", "sueldo": "3.00"}
    # el catalogo viaja como pares (codigo, descripcion) y la descripcion, tecleada
    partidas, descripcion = llamadas[0]
    assert partidas["LB-04-CON"] == APU_CONCRETO.descripcion
    assert descripcion == DESCRIPCION


def test_un_insumo_sin_precio_deja_el_aviso_y_no_el_desglose(base, monkeypatch) -> None:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ids = sesion.scalars(
                select(models.Insumo.id).where(models.Insumo.descripcion == "Cemento Portland")
            ).all()
            sesion.execute(
                delete(models.PrecioInsumo).where(models.PrecioInsumo.insumo_id.in_(ids))
            )
            sesion.commit()
    finally:
        motor.dispose()
    _doble_del_modelo(monkeypatch)
    cuerpo = _con_clave().post(RUTA, json={"descripcion": DESCRIPCION}).json()
    concreto, excavacion = cuerpo["propuestas"]
    assert concreto["composicion"] is None
    assert concreto["aviso"].startswith("Desglose incompleto en la lista vigente")
    assert "Cemento Portland" in concreto["aviso"]
    assert excavacion["aviso"] is None
    assert excavacion["composicion"] is not None


def test_sin_propuestas_sobre_el_umbral_el_mensaje_va_en_el_cuerpo(base, monkeypatch) -> None:
    monkeypatch.setattr(
        "aplicacion.similares.sugerir_partidas_similares", lambda *_a: Propuesta(())
    )
    cuerpo = _con_clave().post(RUTA, json={"descripcion": DESCRIPCION}).json()
    assert cuerpo == {"propuestas": [], "falla": None, "mensaje": MENSAJE_SIN_UMBRAL}


def test_sin_el_extra_el_mensaje_es_el_de_instalarlo(base, monkeypatch) -> None:
    _falla_del_modelo(monkeypatch, ModuleNotFoundError("No module named 'sentence_transformers'"))
    r = _con_clave().post(RUTA, json={"descripcion": DESCRIPCION})
    assert r.status_code == 200, r.text
    assert r.json() == {"propuestas": [], "falla": MENSAJE_SIN_EXTRA, "mensaje": None}


def test_el_modelo_roto_da_un_mensaje_y_nunca_una_traza(base, monkeypatch) -> None:
    _falla_del_modelo(monkeypatch, RuntimeError("pesos corruptos simulados"))
    r = _con_clave().post(RUTA, json={"descripcion": DESCRIPCION})
    assert r.status_code == 200, r.text
    falla = r.json()["falla"]
    assert falla.startswith("El modelo de similitud no esta disponible: ")
    assert "RuntimeError" in falla
    assert "Traceback" not in r.text


def test_descripcion_en_blanco_es_422_y_dice_que_escriba_una(base) -> None:
    r = _con_clave().post(RUTA, json={"descripcion": "  "})
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == "Escriba una descripción para buscar partidas similares."


def test_sin_el_campo_descripcion_es_422(base) -> None:
    assert _con_clave().post(RUTA, json={}).status_code == 422


def test_sin_sesion_ni_clave_es_401(base) -> None:
    assert _cliente().post(RUTA, json={"descripcion": DESCRIPCION}).status_code == 401


def test_una_cuenta_que_arma_puede_consultar(base, monkeypatch) -> None:
    _doble_del_modelo(monkeypatch)
    cliente, protegida = _con_cuenta("ana")
    r = cliente.post(RUTA, json={"descripcion": DESCRIPCION}, headers=protegida)
    assert r.status_code == 200, r.text


def test_una_cuenta_que_solo_revisa_es_403(base, monkeypatch) -> None:
    _doble_del_modelo(monkeypatch)
    cliente, protegida = _con_cuenta("rita")
    r = cliente.post(RUTA, json={"descripcion": DESCRIPCION}, headers=protegida)
    assert r.status_code == 403
    assert r.json()["detalle"] == MENSAJE_PERMISO


def test_sin_la_marca_anti_csrf_es_403(base, monkeypatch) -> None:
    _doble_del_modelo(monkeypatch)
    cliente, _ = _con_cuenta("ana")
    r = cliente.post(RUTA, json={"descripcion": DESCRIPCION})
    assert r.status_code == 403


def test_el_proponedor_inyectado_manda_sobre_el_enlace_real(base) -> None:
    """`proponer_similares` recibe el proponedor como dependencia (sin modelo, sin monkeypatch)."""
    from aplicacion.similares import proponer_similares

    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            falso = lambda _p, _d: Propuesta(  # noqa: E731
                (PartidaSimilar("LB-01-EXC", APU_EXCAVACION.descripcion, 0.5),)
            )
            resultado = proponer_similares(sesion, DESCRIPCION, falso)
            vacio = proponer_similares(sesion, DESCRIPCION, lambda _p, _d: Propuesta(()))
    finally:
        motor.dispose()
    assert [p.codigo for p in resultado.propuestas] == ["LB-01-EXC"]
    assert resultado.propuestas[0].puntaje == "0.5000"
    assert vacio.mensaje is not None and vacio.propuestas == ()
