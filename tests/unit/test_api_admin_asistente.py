"""Administración, pestaña «Asistente de IA» por la API (S4 §3.1, §8.3, RV-15; T6, migración final).

Contrato (paridad con `pestana_asistente` de `ui/paginas/administracion.py`, sobre
`asistente.administracion`), todo bajo `/v1/admin/asistente`, solo con **sesión** de administrador:

- `GET ""` → el estado: configuración, proveedores con su rótulo, la clave registrada
  **enmascarada** (los 4 últimos caracteres), si hay una guardada sin cargar, si solo queda el
  respaldo cifrado, si falta el componente `ia` y si este equipo puede operar con la clave.
- `POST "/configuracion"` guarda activo, proveedor, modelos, dirección de Ollama y tope de costo.
- `POST "/clave"`, `"/clave/reactivar"` y `"/clave/olvidar"`: solo desde el propio equipo
  (`Sensible.CLAVE_DE_IA`). La clave y las contraseñas viajan solo en el cuerpo, nunca vuelven en
  una respuesta ni en un 422 y no se registran; un intento fallido de reactivar deja un evento de
  seguridad sin la contraseña.

Sin gasto real ni almacén verdadero: la clave de la instalación se sustituye por una `ClaveDeIA` con
`AlmacenFalso` y `SecretosFalsos` (`tests/fixtures/asistente_clave.py`). Oráculos: los mensajes
literales de la clásica y de `asistente`, el archivo `ia_config.json` leído con `json` y la base de
la instalación con `sqlite3` directo.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError

from api import caso_web, dependencias
from api.rutas import admin_asistente as ruta
from asistente.clave import SERVICIO, ClaveDeIA, es_bucle_local
from asistente.configuracion import ConfiguracionIA, guardar
from asistente.instalacion import EMPRESA_DE_LA_CLAVE, ruta_de_configuracion
from operacion import config
from seguridad import eventos
from tests.fixtures.app_de_prueba import app_con
from tests.fixtures.asistente_clave import AlmacenFalso, SecretosFalsos
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

APP = app_con(ruta.router)
BASE = "/v1/admin/asistente"
CLAVE = "sk-ant-api03-ABCD1234efgh5678"
RESPALDO = "contrasena del respaldo larga"
REMOTO = (
    "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."
)
SIN_EXTRA_IA = (
    "Falta el componente del asistente de IA en este equipo. Instálelo con «uv sync --extra ia» "
    "y vuelva a abrir Sílice."
)
AVISO_DE_NUBE = (
    "Con el modo en la nube activo, el pedido y el resumen del borrador viajan al proveedor "
    "(sin precios, montos ni nombres de proyecto, empresa o usuarios). Es una excepción declarada "
    "a la ejecución local; el modo local no envía nada fuera del equipo."
)
CONFIGURACION = {
    "activo": True,
    "proveedor": "claude",
    "modelo_claude": "claude-opus-5-5",
    "modelo_local": "",
    "anfitrion_ollama": "http://127.0.0.1:11434",
    "tope_usd": "2,50",
}


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("admin_asistente"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _clave(almacen: AlmacenFalso, respaldo: Path) -> ClaveDeIA:
    return ClaveDeIA(
        almacen=almacen, secretos=SecretosFalsos(), ruta_respaldo=respaldo, es_local=es_bucle_local
    )


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SimpleNamespace:
    """La clave de la instalación con el almacén en memoria (nada toca el almacén real)."""
    almacen = AlmacenFalso()
    respaldo = tmp_path / "ia.cifrada"
    vista = SimpleNamespace(almacen=almacen, respaldo=respaldo, clave=_clave(almacen, respaldo))
    monkeypatch.setattr(ruta, "clave_de_la_instalacion", lambda *a, **k: vista.clave)
    return vista


def _admin(ip: str = "127.0.0.1"):
    navegador, ficha = con_cuenta(APP, "admin", ip=ip)
    return navegador, protegida(ficha)


def _eventos() -> list[tuple]:
    with closing(sqlite3.connect(config.ruta_instalacion())) as bd:
        return list(
            bd.execute(
                "SELECT login_intentado, ip_cliente, detalle FROM evento_acceso "
                "WHERE tipo = 'clave de ia no reactivada'"
            )
        )


def _todo_el_registro() -> str:
    with closing(sqlite3.connect(config.ruta_instalacion())) as bd:
        return " ".join(str(f) for f in bd.execute("SELECT * FROM evento_acceso"))


def _activo() -> None:
    guardar(ruta_de_configuracion(), ConfiguracionIA(activo=True))


def _solo_el_respaldo(entorno: SimpleNamespace) -> None:
    """El almacén del sistema cae: la clave queda solo en el respaldo cifrado y fuera de memoria."""
    entorno.almacen.cae = True
    entorno.clave.registrar(
        EMPRESA_DE_LA_CLAVE, CLAVE, ip_cliente="127.0.0.1", contrasena_respaldo=RESPALDO
    )
    entorno.clave.desactivar()


# --- quién entra ---------------------------------------------------------------------------------


def test_sin_sesion_no_entra_nadie(entorno) -> None:
    navegador = cliente(APP)
    assert navegador.get(BASE).status_code == 401
    assert navegador.post(f"{BASE}/clave", json={"clave": CLAVE}).status_code == 401


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_quien_no_administra_recibe_403(entorno, login: str) -> None:
    navegador, _ = con_cuenta(APP, login)
    respuesta = navegador.get(BASE)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}


def test_la_clave_de_api_no_administra(entorno) -> None:
    secreto = crear_clave_de_prueba()
    assert cliente(APP).get(BASE, headers={CABECERA: secreto}).status_code == 403


def test_un_post_sin_csrf_se_rechaza_y_no_registra(entorno) -> None:
    navegador, _ = _admin()
    respuesta = navegador.post(
        f"{BASE}/clave", json={"clave": CLAVE}, headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert respuesta.status_code == 403
    assert entorno.almacen.datos == {}


# --- el estado -----------------------------------------------------------------------------------


def test_el_estado_de_fabrica(entorno) -> None:
    navegador, _ = _admin()
    respuesta = navegador.get(BASE)
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "activo": False,
        "proveedor": "claude",
        "proveedores": [
            {"valor": "claude", "etiqueta": "Claude (en la nube, con la clave de la empresa)"},
            {"valor": "ollama", "etiqueta": "Ollama (local, en este equipo)"},
        ],
        "modelo_claude": "claude-opus-5-5",
        "modelo_local": "",
        "anfitrion_ollama": "http://127.0.0.1:11434",
        "tope_usd": "2",
        "clave_registrada": None,
        "clave_guardada": False,
        "pide_contrasena": False,
        "falta_el_componente": None,
        "aviso_de_nube": AVISO_DE_NUBE,
        "sensible": {"permitida": True, "motivo": ""},
    }


def test_sin_el_componente_ia_lo_dice_y_no_hay_clave(monkeypatch) -> None:
    def sin_keyring(*args, **kwargs):
        raise ImportError("No module named 'keyring'")

    monkeypatch.setattr(ruta, "clave_de_la_instalacion", sin_keyring)
    navegador, cab = _admin()
    cuerpo = navegador.get(BASE).json()
    assert cuerpo["falta_el_componente"] == SIN_EXTRA_IA
    assert cuerpo["clave_registrada"] is None
    respuesta = navegador.post(f"{BASE}/clave", json={"clave": CLAVE}, headers=cab)
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": SIN_EXTRA_IA}
    assert CLAVE not in respuesta.text


def test_desde_otro_equipo_el_estado_dice_por_que_no_se_puede_operar(entorno) -> None:
    navegador, _ = _admin(ip="192.168.1.40")
    assert navegador.get(BASE).json()["sensible"] == {"permitida": False, "motivo": REMOTO}


def test_la_clave_registrada_se_ve_solo_enmascarada(entorno) -> None:
    _activo()
    entorno.almacen.datos[(SERVICIO, EMPRESA_DE_LA_CLAVE)] = CLAVE
    navegador, _ = _admin()
    respuesta = navegador.get(BASE)
    assert respuesta.json()["clave_registrada"] == "…5678"
    assert CLAVE not in respuesta.text
    assert "ABCD1234" not in respuesta.text


def test_apagado_la_clave_guardada_no_se_carga(entorno) -> None:
    entorno.almacen.datos[(SERVICIO, EMPRESA_DE_LA_CLAVE)] = CLAVE
    navegador, _ = _admin()
    cuerpo = navegador.get(BASE).json()
    assert cuerpo["clave_registrada"] is None
    assert cuerpo["clave_guardada"] is True
    assert entorno.clave.vigente is None


# --- la configuración ----------------------------------------------------------------------------


def test_guardar_la_configuracion_la_escribe_en_la_carpeta_de_datos(entorno) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(f"{BASE}/configuracion", json=CONFIGURACION, headers=cab)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["mensaje"] == "Configuración del asistente guardada."
    assert respuesta.json()["estado"]["activo"] is True
    assert respuesta.json()["estado"]["tope_usd"] == "2.50"
    guardada = json.loads(ruta_de_configuracion().read_text(encoding="utf-8"))
    assert guardada["activo"] is True
    assert guardada["tope_usd"] == "2.50"
    assert guardada["proveedor"] == "claude"


def test_un_tope_no_positivo_se_rechaza_y_no_toca_el_archivo(entorno) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/configuracion", json={**CONFIGURACION, "tope_usd": "0"}, headers=cab
    )
    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "detalle": "El tope de costo debe ser mayor que cero: escriba, por ejemplo, 2,50."
    }
    assert not ruta_de_configuracion().exists()


def test_un_proveedor_que_no_esta_en_la_lista_se_rechaza_sin_repetirlo(entorno) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/configuracion", json={**CONFIGURACION, "proveedor": "otro-x"}, headers=cab
    )
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "Elija un proveedor de la lista."}
    assert not ruta_de_configuracion().exists()


def test_un_cuerpo_invalido_de_configuracion_no_se_repite(entorno) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/configuracion", json={**CONFIGURACION, "activo": "quizas-x"}, headers=cab
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "Indique la configuración del asistente completa."}
    assert "quizas-x" not in respuesta.text


def test_apagar_el_asistente_saca_la_clave_de_la_memoria(entorno) -> None:
    _activo()
    entorno.clave.registrar(EMPRESA_DE_LA_CLAVE, CLAVE, ip_cliente="127.0.0.1")
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/configuracion", json={**CONFIGURACION, "activo": False}, headers=cab
    )
    assert respuesta.status_code == 200
    assert entorno.clave.vigente is None
    assert respuesta.json()["estado"]["clave_registrada"] is None
    assert respuesta.json()["estado"]["clave_guardada"] is True


# --- registrar, reactivar y olvidar la clave -----------------------------------------------------


def test_registrar_la_clave_la_guarda_y_solo_devuelve_sus_cuatro_ultimos(entorno) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(f"{BASE}/clave", json={"clave": CLAVE}, headers=cab)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json()["mensaje"] == "Clave de IA registrada (…5678)."
    assert CLAVE not in respuesta.text
    assert entorno.almacen.datos == {(SERVICIO, EMPRESA_DE_LA_CLAVE): CLAVE}
    assert CLAVE not in _todo_el_registro()


def test_la_clave_solo_se_registra_desde_el_propio_equipo(entorno) -> None:
    navegador, cab = _admin(ip="192.168.1.40")
    respuesta = navegador.post(f"{BASE}/clave", json={"clave": CLAVE}, headers=cab)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": REMOTO}
    assert CLAVE not in respuesta.text
    assert entorno.almacen.datos == {}


def test_una_clave_vacia_se_rechaza(entorno) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(f"{BASE}/clave", json={"clave": "   "}, headers=cab)
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "Escriba la clave de IA de la empresa."}


def test_un_cuerpo_invalido_de_la_clave_no_la_repite(entorno) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/clave", json={"clave": ["sk-ant-api03-repetida-9876"]}, headers=cab
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "Escriba la clave de IA como texto."}
    assert "repetida-9876" not in respuesta.text


def test_sin_almacen_pide_la_contrasena_del_respaldo(entorno) -> None:
    entorno.almacen.cae = True
    navegador, cab = _admin()
    sin = navegador.post(f"{BASE}/clave", json={"clave": CLAVE}, headers=cab)
    assert sin.status_code == 400
    assert sin.json() == {
        "detalle": (
            "El almacen de credenciales del sistema no esta disponible: indique una contrasena "
            "para guardar la clave cifrada."
        )
    }
    corta = navegador.post(
        f"{BASE}/clave", json={"clave": CLAVE, "contrasena_respaldo": "corta-77"}, headers=cab
    )
    assert corta.status_code == 400
    assert corta.json() == {
        "detalle": "La contraseña de la clave debe tener al menos 12 caracteres."
    }
    assert "corta-77" not in corta.text and CLAVE not in corta.text
    buena = navegador.post(
        f"{BASE}/clave", json={"clave": CLAVE, "contrasena_respaldo": RESPALDO}, headers=cab
    )
    assert buena.status_code == 200, buena.text
    assert RESPALDO not in buena.text and CLAVE not in buena.text
    assert entorno.respaldo.exists()
    assert CLAVE.encode() not in entorno.respaldo.read_bytes()


def test_con_solo_el_respaldo_el_estado_pide_la_contrasena(entorno) -> None:
    _activo()
    _solo_el_respaldo(entorno)
    navegador, _ = _admin()
    cuerpo = navegador.get(BASE).json()
    assert cuerpo["clave_registrada"] is None
    assert cuerpo["pide_contrasena"] is True


def test_reactivar_con_una_contrasena_equivocada_deja_un_evento_sin_ella(entorno) -> None:
    _activo()
    _solo_el_respaldo(entorno)
    navegador, cab = _admin()
    mala = navegador.post(
        f"{BASE}/clave/reactivar", json={"contrasena": "otra contrasena larga"}, headers=cab
    )
    assert mala.status_code == 400
    assert mala.json() == {"detalle": "La contraseña no abre el respaldo de la clave de IA."}
    assert entorno.clave.vigente is None
    assert _eventos() == [
        ("admin", "127.0.0.1", "la contraseña no abrió el respaldo cifrado de la clave de IA")
    ]
    assert "otra contrasena larga" not in _todo_el_registro()
    buena = navegador.post(f"{BASE}/clave/reactivar", json={"contrasena": RESPALDO}, headers=cab)
    assert buena.status_code == 200, buena.text
    assert buena.json()["mensaje"] == "Clave de IA reactivada (…5678)."
    assert RESPALDO not in buena.text and CLAVE not in buena.text
    assert entorno.clave.vigente == CLAVE
    assert len(_eventos()) == 1


def test_si_no_se_puede_anotar_el_intento_el_administrador_igual_ve_el_mensaje(
    entorno, monkeypatch, caplog
) -> None:
    _activo()
    _solo_el_respaldo(entorno)

    def base_caida(*args, **kwargs):
        raise OperationalError("INSERT INTO evento_acceso", {}, Exception("database is locked"))

    navegador, cab = _admin()  # entrar también anota un evento: la base cae después
    monkeypatch.setattr(eventos, "registrar", base_caida)
    with caplog.at_level(logging.WARNING, logger="api.rutas.admin_asistente"):
        respuesta = navegador.post(
            f"{BASE}/clave/reactivar", json={"contrasena": "otra contrasena larga"}, headers=cab
        )
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "La contraseña no abre el respaldo de la clave de IA."}
    avisos = [r.getMessage() for r in caplog.records if r.name == "api.rutas.admin_asistente"]
    assert avisos == ["No se pudo anotar el intento fallido de reactivar la clave de IA"]
    assert "otra contrasena larga" not in caplog.text


def test_apagado_no_se_reactiva_ni_deja_evento(entorno) -> None:
    _solo_el_respaldo(entorno)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/clave/reactivar", json={"contrasena": RESPALDO}, headers=cab
    )
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "Active el asistente antes de reactivar la clave de IA."}
    assert entorno.clave.vigente is None
    assert _eventos() == []


def test_reactivar_solo_desde_el_propio_equipo(entorno) -> None:
    _activo()
    _solo_el_respaldo(entorno)
    navegador, cab = _admin(ip="192.168.1.40")
    respuesta = navegador.post(
        f"{BASE}/clave/reactivar", json={"contrasena": RESPALDO}, headers=cab
    )
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": REMOTO}
    assert entorno.clave.vigente is None


def test_el_422_de_reactivar_no_repite_la_contrasena(entorno) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/clave/reactivar", json={"contrasena": {"x": "contrasena-eco-55"}}, headers=cab
    )
    assert respuesta.status_code == 422
    assert "contrasena-eco-55" not in respuesta.text


def test_olvidar_la_clave_la_borra_del_almacen_y_de_la_memoria(entorno) -> None:
    entorno.clave.registrar(EMPRESA_DE_LA_CLAVE, CLAVE, ip_cliente="127.0.0.1")
    navegador, cab = _admin()
    respuesta = navegador.post(f"{BASE}/clave/olvidar", headers=cab)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["mensaje"] == "La clave de IA se olvidó: ya no está en este equipo."
    assert entorno.almacen.datos == {}
    assert entorno.clave.vigente is None


def test_olvidar_solo_desde_el_propio_equipo(entorno) -> None:
    entorno.clave.registrar(EMPRESA_DE_LA_CLAVE, CLAVE, ip_cliente="127.0.0.1")
    navegador, cab = _admin(ip="192.168.1.40")
    respuesta = navegador.post(f"{BASE}/clave/olvidar", headers=cab)
    assert respuesta.status_code == 403
    assert entorno.almacen.datos == {(SERVICIO, EMPRESA_DE_LA_CLAVE): CLAVE}
