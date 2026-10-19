"""Administración, pestaña «Empresas registradas» por la API (UC-21; T5 de la migración final).

Contrato (paridad con `_pestana_registradas` y `_cambiar_registrada` de
`ui/paginas/administracion.py`, sobre `seguridad.empresas`), todo bajo
`/v1/admin/empresas-registradas`, solo con **sesión** de administrador (`ADMINISTRAR_EMPRESA`):

- `GET ""` → `{registradas: [{id, empresa, huella, estado, comprobada_con, metodo}], metodos}`.
- `POST "/leer"` (multipart `archivo`) → `{empresa, huella}`: lee y previsualiza un
  `.silice-clave` **sin guardar nada**.
- `POST ""` (multipart `archivo`, `huella`, `comprobada_con`, `metodo`) registra la clave ajena.
- `POST "/{id}/retirar"` `{fecha}` y `POST "/{id}/revocar"` (multipart `motivo`, `aviso?`).

Oráculos escritos a mano: los mensajes literales de la página clásica y de `seguridad.empresas` /
`seguridad.firma`; la huella de cada clave de prueba con `seguridad.firma` (no con la ruta); la base
de la instalación leída con `sqlite3` directo.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.rutas import admin_empresas_registradas as ruta
from operacion import config
from operacion.instalacion import sesion_de_instalacion
from seguridad import empresas, firma
from tests.fixtures.app_de_prueba import app_con
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

APP = app_con(ruta.router)
BASE = "/v1/admin/empresas-registradas"
AJENA = "Contratista Ajena Demo, C.A."
RIF = "J-00000001-0"
MENSAJE_CSRF = "Falta la comprobación anti-CSRF de la sesión o no coincide."


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("admin_registradas"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture(scope="module")
def par() -> firma.ParDeClaves:
    return firma.generar_par()


@pytest.fixture(scope="module")
def archivo_clave(par: firma.ParDeClaves) -> bytes:
    return firma.exportar_clave_publica(AJENA, RIF, par.publica, AHORA)


def _admin():
    navegador, ficha = con_cuenta(APP, "admin")
    return navegador, protegida(ficha)


def _filas(sql: str) -> list[tuple]:
    with closing(sqlite3.connect(config.ruta_instalacion())) as bd:
        return list(bd.execute(sql))


def _subir(contenido: bytes, nombre: str = "clave-publica.silice-clave") -> dict:
    return {"archivo": (nombre, contenido, "application/octet-stream")}


def _registrar(navegador, cab, contenido: bytes, huella: str, **extra):
    datos = {"huella": huella, "comprobada_con": "Pedro Pérez", "metodo": "telefono", **extra}
    return navegador.post(BASE, files=_subir(contenido), data=datos, headers=cab)


def _registrada(archivo_clave: bytes, par: firma.ParDeClaves) -> int:
    with sesion_de_instalacion() as bd:
        fila = empresas.registrar_empresa_ajena(
            bd, archivo_clave, firma.huella_corta(par.publica), "Pedro", "telefono", "admin", AHORA
        )
        return fila.id


# --- quién entra ---------------------------------------------------------------------------------


def test_sin_sesion_no_entra_nadie(archivo_clave: bytes) -> None:
    navegador = cliente(APP)
    assert navegador.get(BASE).status_code == 401
    assert navegador.post(f"{BASE}/leer", files=_subir(archivo_clave)).status_code == 401


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_quien_no_administra_recibe_403(login: str) -> None:
    navegador, _ = con_cuenta(APP, login)
    respuesta = navegador.get(BASE)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}


def test_la_clave_de_api_no_administra() -> None:
    secreto = crear_clave_de_prueba()
    assert cliente(APP).get(BASE, headers={CABECERA: secreto}).status_code == 403


def test_un_post_sin_csrf_se_rechaza_y_no_registra(archivo_clave: bytes, par) -> None:
    navegador, _ = _admin()
    respuesta = navegador.post(
        BASE,
        files=_subir(archivo_clave),
        data={"huella": firma.huella_corta(par.publica), "comprobada_con": "P", "metodo": "qr"},
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_CSRF}
    assert _filas("SELECT 1 FROM empresa_registrada") == []


# --- listar --------------------------------------------------------------------------------------


def test_sin_empresas_la_lista_esta_vacia_y_trae_los_metodos_con_su_rotulo() -> None:
    navegador, _ = _admin()
    respuesta = navegador.get(BASE)
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "registradas": [],
        "metodos": [
            {"valor": "telefono", "etiqueta": "teléfono"},
            {"valor": "en persona", "etiqueta": "en persona"},
            {"valor": "qr", "etiqueta": "código QR"},
        ],
    }


def test_la_lista_trae_las_columnas_de_la_clasica(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    navegador, _ = _admin()
    assert navegador.get(BASE).json()["registradas"] == [
        {
            "id": identificador,
            "empresa": AJENA,
            "huella": firma.huella_corta(par.publica),
            "estado": "activa",
            "comprobada_con": "Pedro",
            "metodo": "telefono",
        }
    ]


# --- leer y previsualizar ------------------------------------------------------------------------


def test_leer_previsualiza_la_clave_sin_guardar_nada(archivo_clave: bytes, par) -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(f"{BASE}/leer", files=_subir(archivo_clave), headers=cab)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {"empresa": AJENA, "huella": firma.huella_corta(par.publica)}
    assert _filas("SELECT 1 FROM empresa_registrada") == []
    assert _filas("SELECT 1 FROM evento_acceso WHERE tipo = 'clave registrada'") == []


def test_la_huella_es_la_calculada_no_la_que_declara_el_archivo(par) -> None:
    documento = json.loads(firma.exportar_clave_publica(AJENA, RIF, par.publica, AHORA))
    documento["huella"] = "0000-0000-0000-0000-0000"
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/leer", files=_subir(json.dumps(documento).encode()), headers=cab
    )
    assert respuesta.json()["huella"] == firma.huella_corta(par.publica)


def test_un_archivo_que_no_es_una_clave_se_rechaza_con_el_mensaje_de_la_clasica() -> None:
    navegador, cab = _admin()
    otro = json.dumps({"formato": "otra-cosa"}).encode()
    respuesta = navegador.post(f"{BASE}/leer", files=_subir(otro), headers=cab)
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "no es un archivo de clave publica de Silice"}


def test_un_archivo_que_no_es_json_se_rechaza_sin_repetir_su_contenido() -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/leer", files=_subir(b"contenido-secreto-ilegible"), headers=cab
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detalle"].startswith("no es un JSON valido")
    assert "contenido-secreto-ilegible" not in respuesta.text


def test_un_archivo_mayor_que_el_tope_se_rechaza_con_413() -> None:
    navegador, cab = _admin()
    grande = b" " * (64 * 1024 + 1)
    respuesta = navegador.post(f"{BASE}/leer", files=_subir(grande), headers=cab)
    assert respuesta.status_code == 413
    assert respuesta.json() == {"detalle": "El archivo supera el máximo de 64 KiB."}


def test_sin_archivo_el_422_no_repite_lo_enviado() -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(f"{BASE}/leer", data={"otro": "dato-enviado"}, headers=cab)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "Suba el archivo de la clave pública (.silice-clave)."}
    assert "dato-enviado" not in respuesta.text


# --- registrar -----------------------------------------------------------------------------------


def test_registrar_con_la_huella_correcta_aunque_se_escriba_en_minusculas(
    archivo_clave: bytes, par
) -> None:
    navegador, cab = _admin()
    tecleada = firma.huella_corta(par.publica).replace("-", " ").lower()
    respuesta = _registrar(navegador, cab, archivo_clave, tecleada)
    assert respuesta.status_code == 200, respuesta.text
    (fila,) = respuesta.json()["registradas"]
    assert fila["empresa"] == AJENA
    assert fila["estado"] == "activa"
    assert _filas(
        "SELECT empresa, rif, estado, comprobada_con, metodo, registrada_por "
        "FROM empresa_registrada"
    ) == [(AJENA, RIF, "activa", "Pedro Pérez", "telefono", "admin")]
    assert _filas("SELECT detalle FROM evento_acceso WHERE tipo = 'clave registrada'") == [
        (f"{AJENA}; {firma.huella_corta(par.publica)}",)
    ]


def test_una_huella_que_no_coincide_no_registra_nada(archivo_clave: bytes, par) -> None:
    navegador, cab = _admin()
    otra = firma.huella_corta(firma.generar_par().publica)
    respuesta = _registrar(navegador, cab, archivo_clave, otra)
    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "detalle": (
            f"La huella leída no coincide con la de la clave ({firma.huella_corta(par.publica)})."
            " No se registró nada."
        )
    }
    assert _filas("SELECT 1 FROM empresa_registrada") == []


def test_una_huella_mal_escrita_dice_como_es(archivo_clave: bytes) -> None:
    navegador, cab = _admin()
    respuesta = _registrar(navegador, cab, archivo_clave, "ABC")
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "la huella corta son 20 caracteres (sin I, L, O ni U)"}


def test_sin_con_quien_se_comprobo_no_registra(archivo_clave: bytes, par) -> None:
    navegador, cab = _admin()
    respuesta = _registrar(
        navegador, cab, archivo_clave, firma.huella_corta(par.publica), comprobada_con="  "
    )
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "Indique con quién se comprobó la huella."}


def test_la_misma_clave_no_se_registra_dos_veces(archivo_clave: bytes, par) -> None:
    _registrada(archivo_clave, par)
    navegador, cab = _admin()
    respuesta = _registrar(navegador, cab, archivo_clave, firma.huella_corta(par.publica))
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "Esa clave ya está registrada."}
    assert _filas("SELECT count(*) FROM empresa_registrada") == [(1,)]


def test_registrar_un_archivo_mayor_que_el_tope_se_rechaza(par) -> None:
    navegador, cab = _admin()
    respuesta = _registrar(navegador, cab, b" " * (64 * 1024 + 1), firma.huella_corta(par.publica))
    assert respuesta.status_code == 413
    assert _filas("SELECT 1 FROM empresa_registrada") == []


# --- retirar y revocar ---------------------------------------------------------------------------


def test_retirar_marca_la_fecha_del_retiro(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/{identificador}/retirar", json={"fecha": "2026-10-01"}, headers=cab
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["registradas"][0]["estado"] == "retirada"
    assert _filas("SELECT estado, fecha_estado FROM empresa_registrada") == [
        ("retirada", "2026-10-01 00:00:00.000000")
    ]


def test_retirar_con_una_fecha_ilegible_no_la_repite(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/{identificador}/retirar", json={"fecha": "fecha-rara-31"}, headers=cab
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "Indique la fecha del retiro como AAAA-MM-DD."}
    assert "fecha-rara-31" not in respuesta.text
    assert _filas("SELECT estado FROM empresa_registrada") == [("activa",)]


def test_retirar_una_empresa_que_no_existe() -> None:
    navegador, cab = _admin()
    respuesta = navegador.post(f"{BASE}/999/retirar", json={"fecha": "2026-10-01"}, headers=cab)
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "No hay una empresa registrada con ese número."}


def test_revocar_sin_motivo_ni_aviso_se_rechaza(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/{identificador}/revocar", data={"motivo": "   "}, headers=cab
    )
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "Escriba el motivo o suba el aviso de revocación."}
    assert _filas("SELECT estado FROM empresa_registrada") == [("activa",)]


def test_revocar_con_el_motivo_escrito(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/{identificador}/revocar", data={"motivo": "clave expuesta"}, headers=cab
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["registradas"][0]["estado"] == "revocada"
    assert _filas("SELECT estado, motivo FROM empresa_registrada") == [
        ("revocada", "clave expuesta")
    ]


def test_revocar_con_el_aviso_firmado_toma_su_motivo(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    aviso = firma.crear_aviso_revocacion(par.privada, "clave perdida", AHORA)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/{identificador}/revocar",
        data={"motivo": ""},
        files={"aviso": ("revocacion.silice-revocacion", aviso, "application/octet-stream")},
        headers=cab,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert _filas("SELECT estado, motivo FROM empresa_registrada") == [
        ("revocada", "clave perdida")
    ]


def test_un_aviso_de_otra_clave_no_revoca(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    ajeno = firma.crear_aviso_revocacion(firma.generar_par().privada, "otra", AHORA)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/{identificador}/revocar",
        files={"aviso": ("revocacion.silice-revocacion", ajeno, "application/octet-stream")},
        headers=cab,
    )
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "El aviso de revocación no es válido para esta clave."}
    assert _filas("SELECT estado FROM empresa_registrada") == [("activa",)]


def test_un_aviso_vacio_del_navegador_cuenta_como_ausente(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/{identificador}/revocar",
        data={"motivo": ""},
        files={"aviso": ("", b"", "application/octet-stream")},
        headers=cab,
    )
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "Escriba el motivo o suba el aviso de revocación."}


def test_un_aviso_mayor_que_el_tope_se_rechaza(archivo_clave: bytes, par) -> None:
    identificador = _registrada(archivo_clave, par)
    navegador, cab = _admin()
    respuesta = navegador.post(
        f"{BASE}/{identificador}/revocar",
        files={"aviso": ("aviso.silice-revocacion", b" " * (64 * 1024 + 1), "text/plain")},
        headers=cab,
    )
    assert respuesta.status_code == 413
    assert _filas("SELECT estado FROM empresa_registrada") == [("activa",)]
