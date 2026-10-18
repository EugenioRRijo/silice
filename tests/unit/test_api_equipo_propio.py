"""«Solo desde el propio equipo» en la API (RM-4; ola 0a de la sesión 2b).

`exigir_equipo_propio(sensible)` es `exigir_clave_o_sesion` con el rol de lo sensible
(`ROL_DE_LO_SENSIBLE`: firmar es de quien entrega, es decir, arma) más el criterio de
`ui.sesion.exigir_local`: el cliente es el bucle local o, con la red local encendida en
`silice.toml`, la IP elegida del servidor; y no hay eventos de seguridad perdidos sin revisar.
Ninguna ruta la usa todavía (la usarán las olas 4 y 5): se ejerce sobre una aplicación de prueba.

Oráculos: los mensajes son los literales de la interfaz clásica escritos aquí a mano; la IP del
cliente la fija `TestClient(client=...)`; la red local se enciende escribiendo `silice.toml` por
`operacion.config` como hace `tests/unit/test_ui_cliente.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException

from api.main import manejar_http_exception
from api.rutas import sesion as rutas_sesion
from api.sesion_web import exigir_equipo_propio
from operacion import config
from seguridad.permisos import Sensible
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

REMOTO = (
    "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."
)
PENDIENTE = (
    "Se restauró un respaldo y hay eventos de seguridad perdidos sin revisar. El administrador "
    "debe revisarlos (Administración, pestaña Instalación) antes de esta operación."
)
PROPIA = "192.168.1.20"  # la IP de la interfaz elegida al encender la red local
VECINA = "192.168.1.30"  # otro equipo de la red local


def _app_de_prueba() -> FastAPI:
    prueba = FastAPI()
    prueba.add_exception_handler(HTTPException, manejar_http_exception)
    prueba.include_router(rutas_sesion.router)
    firmar = [Depends(exigir_equipo_propio(Sensible.FIRMAR))]
    clave_api = [Depends(exigir_equipo_propio(Sensible.CLAVE_DE_API))]

    @prueba.get("/firmar", dependencies=firmar)
    def leer() -> dict[str, bool]:
        return {"ok": True}

    @prueba.post("/firmar", dependencies=firmar)
    def escribir() -> dict[str, bool]:
        return {"ok": True}

    @prueba.get("/clave-de-api", dependencies=clave_api)
    def crear() -> dict[str, bool]:
        return {"ok": True}

    return prueba


PRUEBA = _app_de_prueba()


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("equipo_propio"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path) -> None:
    copiar_instalacion(_plantilla)


def _encender_red_local() -> None:
    config.guardar_ajustes(config.ruta_ajustes(), config.Ajustes(red_local=True, direccion=PROPIA))


def _eventos_sin_revisar() -> None:
    pendiente = config.carpeta_datos() / "eventos_perdidos_20261011-090000.json"
    pendiente.parent.mkdir(parents=True, exist_ok=True)
    pendiente.write_text('{"revisado": false}', encoding="utf-8")


def _firmar_desde(ip: str):
    navegador, _ = con_cuenta(PRUEBA, "ana", ip=ip)
    return navegador.get("/firmar")


def test_desde_el_bucle_local_pasa_con_la_red_apagada_y_encendida() -> None:
    assert _firmar_desde("127.0.0.1").json() == {"ok": True}
    _encender_red_local()
    assert _firmar_desde("127.0.0.1").json() == {"ok": True}
    assert _firmar_desde("::1").json() == {"ok": True}


def test_con_la_red_apagada_otra_ip_no_es_el_propio_equipo() -> None:
    for ip in (VECINA, PROPIA):
        respuesta = _firmar_desde(ip)
        assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": REMOTO}), ip


def test_con_la_red_encendida_solo_la_ip_elegida_del_servidor_cuenta() -> None:
    _encender_red_local()
    assert _firmar_desde(PROPIA).json() == {"ok": True}
    respuesta = _firmar_desde(VECINA)
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": REMOTO})


def test_el_rol_se_exige_antes_que_el_equipo() -> None:
    """Firmar es de quien entrega (arma): revisa recibe el 403 del rol aunque esté en el equipo."""
    navegador, _ = con_cuenta(PRUEBA, "rita")
    respuesta = navegador.get("/firmar")
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_PERMISO})
    admin, _ = con_cuenta(PRUEBA, "admin")
    assert admin.get("/clave-de-api").json() == {"ok": True}  # la clave de API es del admin
    ana, _ = con_cuenta(PRUEBA, "ana")
    assert ana.get("/clave-de-api").status_code == 403


def test_eventos_sin_revisar_bloquean_aun_desde_el_equipo() -> None:
    _eventos_sin_revisar()
    respuesta = _firmar_desde("127.0.0.1")
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": PENDIENTE})


def test_remoto_y_con_pendientes_manda_el_motivo_remoto() -> None:
    _encender_red_local()
    _eventos_sin_revisar()
    respuesta = _firmar_desde(VECINA)
    assert respuesta.json() == {"detalle": REMOTO}


def test_sin_sesion_da_401_y_con_cookie_un_post_sigue_exigiendo_csrf() -> None:
    assert cliente(PRUEBA).get("/firmar").status_code == 401
    navegador, ficha = con_cuenta(PRUEBA, "ana")
    assert navegador.post("/firmar", headers={"Origin": "http://127.0.0.1:8000"}).status_code == 403
    assert navegador.post("/firmar", headers=protegida(ficha)).json() == {"ok": True}


def test_con_clave_de_api_tambien_se_exige_el_propio_equipo() -> None:
    clave = {CABECERA: crear_clave_de_prueba()}
    assert cliente(PRUEBA).get("/firmar", headers=clave).json() == {"ok": True}
    _encender_red_local()
    respuesta = cliente(PRUEBA, ip=VECINA).get("/firmar", headers=clave)
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": REMOTO})
    malo = cliente(PRUEBA).get("/firmar", headers={CABECERA: "x.y"})
    assert malo.status_code == 401
