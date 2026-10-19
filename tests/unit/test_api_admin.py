"""Administración por la API (migración de la página a la interfaz nueva): Empresa y clave de firma,
Claves de API e Instalación (UC-21; RF-80, RF-84, RF-88, RF-98; RM-3 y RM-4).

Contrato (paridad con `ui/paginas/administracion.py` y `ui/paginas/instalacion.py`), todo bajo
`/v1/admin`, solo con **sesión** de administrador (la clave de API no administra: 403):

- `GET /empresa` → `{empresa, clave, sensible}`; `POST /empresa` guarda nombre, RIF y ciudad.
- `POST /empresa/clave` genera la clave de firma; `GET /empresa/clave-publica` y
  `GET /empresa/respaldo-clave` la descargan; `POST /empresa/clave/retirar|revocar` la dan de baja.
- `GET /claves-api`, `POST /claves-api` (el secreto viaja una sola vez) y
  `POST /claves-api/{id}/revocar`.
- `GET /instalacion`, `POST /instalacion/respaldos`, `GET /instalacion/respaldos/{nombre}` (zip) y
  `POST /instalacion/eventos/{nombre}/revisar`.

Lo sensible (clave de firma, de API, descargar respaldos) exige además el propio equipo
(`Sensible`, RM-4). Ninguna contraseña ni secreto vuelve en un cuerpo, un error o un registro.

Oráculos: los mensajes literales de la página clásica y de `seguridad.empresas`, la huella con
`seguridad.firma`, la base de la instalación leída con `sqlite3` directo y el zip con `zipfile`.
"""

from __future__ import annotations

import base64
import io
import json
import sqlite3
import zipfile
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from operacion import config
from operacion.instalacion import sesion_de_instalacion
from seguridad import empresas
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

REMOTO = (
    "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."
)
FRASE = "frase de firma larga y propia"
PRIVADO = "frase-que-nunca-debe-volver-ni-registrarse"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("admin"))


@pytest.fixture(autouse=True)
def _entorno(_plantilla: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _admin(ip: str = "127.0.0.1") -> tuple[TestClient, dict[str, str]]:
    navegador, ficha = con_cuenta(app, "admin", ip=ip)
    return navegador, protegida(ficha)


def _filas(sql: str) -> list[tuple]:
    with closing(sqlite3.connect(config.ruta_instalacion())) as bd:
        return list(bd.execute(sql))


def _con_empresa(clave: bool = False) -> None:
    with sesion_de_instalacion() as bd:
        empresas.guardar_empresa_propia(
            bd, "Contratista Demo, C.A.", "J-00000000-0", "", "admin", AHORA
        )
        if clave:
            empresas.generar_clave(bd, FRASE, "admin", AHORA)


# --- quién entra ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("GET", "/v1/admin/empresa"),
        ("GET", "/v1/admin/claves-api"),
        ("GET", "/v1/admin/instalacion"),
    ],
)
def test_sin_sesion_no_entra_nadie(metodo: str, ruta: str) -> None:
    assert cliente(app).request(metodo, ruta).status_code == 401


@pytest.mark.parametrize("login", ["ana", "rita"])
@pytest.mark.parametrize(
    "ruta", ["/v1/admin/empresa", "/v1/admin/claves-api", "/v1/admin/instalacion"]
)
def test_quien_no_administra_recibe_403(login: str, ruta: str) -> None:
    navegador, _ = con_cuenta(app, login)
    respuesta = navegador.get(ruta)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}


@pytest.mark.parametrize(
    "ruta", ["/v1/admin/empresa", "/v1/admin/claves-api", "/v1/admin/instalacion"]
)
def test_la_clave_de_api_no_administra(ruta: str) -> None:
    secreto = crear_clave_de_prueba()
    respuesta = cliente(app).get(ruta, headers={CABECERA: secreto})
    assert respuesta.status_code == 403


# --- empresa y clave de firma --------------------------------------------------------------------


def test_la_empresa_sin_datos_ni_clave() -> None:
    navegador, _ = _admin()
    cuerpo = navegador.get("/v1/admin/empresa").json()
    assert cuerpo["empresa"] is None
    assert cuerpo["clave"] is None
    assert cuerpo["sensible"] == {"permitida": True, "motivo": ""}


def test_guardar_la_empresa_exige_nombre_y_rif() -> None:
    navegador, cab = _admin()
    mala = navegador.post(
        "/v1/admin/empresa", json={"nombre": " ", "rif": "J-1", "ciudad": ""}, headers=cab
    )
    assert mala.status_code == 400
    assert mala.json() == {"detalle": "La empresa necesita nombre y RIF."}
    buena = navegador.post(
        "/v1/admin/empresa",
        json={"nombre": " Contratista Demo, C.A. ", "rif": "J-00000000-0", "ciudad": "Caracas"},
        headers=cab,
    )
    assert buena.status_code == 200
    assert buena.json()["empresa"] == {
        "nombre": "Contratista Demo, C.A.",
        "rif": "J-00000000-0",
        "ciudad": "Caracas",
    }
    assert _filas("SELECT nombre, rif, ciudad FROM empresa_propia") == [
        ("Contratista Demo, C.A.", "J-00000000-0", "Caracas")
    ]


def test_generar_la_clave_pide_primero_la_empresa() -> None:
    navegador, cab = _admin()
    respuesta = navegador.post("/v1/admin/empresa/clave", json={"contrasena": FRASE}, headers=cab)
    assert respuesta.status_code == 400
    assert respuesta.json() == {"detalle": "Registre primero los datos de la empresa."}


def test_generar_la_clave_devuelve_la_huella_y_nunca_la_contrasena() -> None:
    _con_empresa()
    navegador, cab = _admin()
    respuesta = navegador.post("/v1/admin/empresa/clave", json={"contrasena": FRASE}, headers=cab)
    assert respuesta.status_code == 200, respuesta.text
    assert FRASE not in respuesta.text
    clave = respuesta.json()["clave"]
    assert clave["estado"] == "activa"
    assert len(clave["huella"]) > 0
    assert _filas("SELECT estado FROM clave_empresa") == [("activa",)]
    segunda = navegador.post("/v1/admin/empresa/clave", json={"contrasena": FRASE}, headers=cab)
    assert segunda.status_code == 400
    assert FRASE not in segunda.text


def test_una_contrasena_corta_se_rechaza_sin_repetirla() -> None:
    _con_empresa()
    navegador, cab = _admin()
    respuesta = navegador.post(
        "/v1/admin/empresa/clave", json={"contrasena": PRIVADO[:5]}, headers=cab
    )
    assert respuesta.status_code == 400
    assert PRIVADO[:5] not in respuesta.text


def test_un_cuerpo_invalido_no_repite_la_contrasena() -> None:
    navegador, cab = _admin()
    respuesta = navegador.post("/v1/admin/empresa/clave", json={"contrasena": 12345}, headers=cab)
    assert respuesta.status_code == 422
    assert "12345" not in respuesta.text


def test_la_clave_de_firma_solo_se_gestiona_desde_el_propio_equipo() -> None:
    _con_empresa()
    navegador, cab = _admin(ip="203.0.113.7")
    respuesta = navegador.post("/v1/admin/empresa/clave", json={"contrasena": FRASE}, headers=cab)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": REMOTO}
    assert _filas("SELECT 1 FROM clave_empresa") == []
    # ver el estado no es sensible: se puede, y avisa por qué no se puede operar
    estado = navegador.get("/v1/admin/empresa").json()["sensible"]
    assert estado == {"permitida": False, "motivo": REMOTO}


def test_la_clave_publica_se_descarga_y_el_respaldo_va_cifrado() -> None:
    _con_empresa(clave=True)
    navegador, _ = _admin()
    publica = navegador.get("/v1/admin/empresa/clave-publica")
    assert publica.status_code == 200
    assert "clave-publica.silice-clave" in publica.headers["content-disposition"]
    assert publica.headers["cache-control"] == "no-store"
    respaldo = navegador.get("/v1/admin/empresa/respaldo-clave")
    assert respaldo.status_code == 200
    assert "respaldo-clave.silice-respaldo" in respaldo.headers["content-disposition"]
    cuerpo = json.loads(respaldo.content)
    assert cuerpo["formato"] == "silice-clave-cifrada"
    assert FRASE.encode() not in respaldo.content


def test_el_respaldo_de_la_clave_no_sale_de_la_red() -> None:
    _con_empresa(clave=True)
    navegador, _ = _admin(ip="203.0.113.7")
    respuesta = navegador.get("/v1/admin/empresa/respaldo-clave")
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": REMOTO}


def test_sin_clave_no_hay_nada_que_descargar() -> None:
    _con_empresa()
    navegador, _ = _admin()
    assert navegador.get("/v1/admin/empresa/clave-publica").status_code == 400


def test_retirar_la_clave_destruye_la_privada() -> None:
    _con_empresa(clave=True)
    navegador, cab = _admin()
    respuesta = navegador.post(
        "/v1/admin/empresa/clave/retirar", json={"motivo": "cambio"}, headers=cab
    )
    assert respuesta.status_code == 200, respuesta.text
    assert _filas("SELECT estado, privada_cifrada FROM clave_empresa") == [("retirada", None)]
    assert navegador.get("/v1/admin/empresa").json()["clave"] is None


def test_revocar_pide_motivo_y_con_contrasena_trae_el_aviso() -> None:
    _con_empresa(clave=True)
    navegador, cab = _admin()
    sin_motivo = navegador.post(
        "/v1/admin/empresa/clave/revocar", json={"motivo": "  "}, headers=cab
    )
    assert sin_motivo.status_code == 400
    assert sin_motivo.json() == {"detalle": "Escriba el motivo de la revocación."}
    mala = navegador.post(
        "/v1/admin/empresa/clave/revocar",
        json={"motivo": "perdida", "contrasena": "equivocada larga!!"},
        headers=cab,
    )
    assert mala.status_code == 400
    assert mala.json() == {"detalle": "La contraseña de la clave no es correcta."}
    assert _filas("SELECT estado FROM clave_empresa") == [("activa",)]
    assert _filas("SELECT login_intentado, detalle FROM evento_acceso WHERE tipo = 'fallo'") == [
        ("admin", "clave de firma")
    ]
    buena = navegador.post(
        "/v1/admin/empresa/clave/revocar",
        json={"motivo": "perdida", "contrasena": FRASE},
        headers=cab,
    )
    assert buena.status_code == 200, buena.text
    assert FRASE not in buena.text
    aviso = base64.b64decode(buena.json()["aviso"])
    assert len(aviso) > 0
    assert _filas("SELECT estado FROM clave_empresa") == [("revocada",)]


def test_revocar_sin_contrasena_no_hay_aviso() -> None:
    _con_empresa(clave=True)
    navegador, cab = _admin()
    respuesta = navegador.post(
        "/v1/admin/empresa/clave/revocar", json={"motivo": "perdida"}, headers=cab
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["aviso"] is None


@pytest.mark.parametrize(
    "ruta", ["/v1/admin/empresa", "/v1/admin/claves-api", "/v1/admin/instalacion"]
)
def test_las_respuestas_de_administracion_no_se_guardan(ruta: str) -> None:
    navegador, _ = _admin()
    assert navegador.get(ruta).headers["cache-control"] == "no-store"


def test_un_post_sin_csrf_se_rechaza() -> None:
    navegador, _ = _admin()
    respuesta = navegador.post(
        "/v1/admin/empresa",
        json={"nombre": "X", "rif": "J-1", "ciudad": ""},
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    assert respuesta.status_code == 403


# --- claves de API -------------------------------------------------------------------------------


def test_crear_una_clave_de_api_muestra_el_secreto_una_vez() -> None:
    navegador, cab = _admin()
    creada = navegador.post("/v1/admin/claves-api", json={"nombre": "plugin ficticio"}, headers=cab)
    assert creada.status_code == 200, creada.text
    assert creada.headers["cache-control"] == "no-store"
    secreto = creada.json()["secreto"]
    identificador = secreto.split(".")[0]
    listado = navegador.get("/v1/admin/claves-api")
    assert secreto not in listado.text
    (fila,) = listado.json()
    assert fila["etiqueta"] == f"api:{identificador}"
    assert fila["nombre"] == "plugin ficticio"
    assert fila["estado"] == "vigente"
    assert fila["ultimo_uso"] is None
    assert secreto not in "".join(str(f) for f in _filas("SELECT * FROM clave_api"))


def test_una_clave_de_api_sin_nombre_se_rechaza() -> None:
    navegador, cab = _admin()
    respuesta = navegador.post("/v1/admin/claves-api", json={"nombre": " "}, headers=cab)
    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "detalle": "La clave de API necesita un nombre (por ejemplo, el plugin que la usa)."
    }


def test_las_claves_de_api_solo_se_crean_y_revocan_desde_el_propio_equipo() -> None:
    navegador, cab = _admin(ip="203.0.113.7")
    creada = navegador.post("/v1/admin/claves-api", json={"nombre": "x"}, headers=cab)
    assert (creada.status_code, creada.json()) == (403, {"detalle": REMOTO})
    assert _filas("SELECT 1 FROM clave_api") == []
    assert navegador.get("/v1/admin/claves-api").status_code == 200  # ver no es sensible


def test_revocar_una_clave_de_api() -> None:
    navegador, cab = _admin()
    secreto = navegador.post("/v1/admin/claves-api", json={"nombre": "x"}, headers=cab).json()[
        "secreto"
    ]
    (fila,) = navegador.get("/v1/admin/claves-api").json()
    assert navegador.post("/v1/admin/claves-api/9999/revocar", headers=cab).status_code == 404
    hecha = navegador.post(f"/v1/admin/claves-api/{fila['id']}/revocar", headers=cab)
    assert hecha.status_code == 200
    assert navegador.get("/v1/admin/claves-api").json()[0]["estado"] == "revocada"
    # la clave revocada ya no abre la API
    assert cliente(app).get("/partidas", headers={CABECERA: secreto}).status_code == 401


# --- instalación ---------------------------------------------------------------------------------


def test_la_instalacion_informa_red_api_y_respaldos_vacios() -> None:
    navegador, _ = _admin()
    cuerpo = navegador.get("/v1/admin/instalacion").json()
    assert cuerpo["red_local"] is False
    assert cuerpo["api_activa"] is False
    assert cuerpo["puerto"] > 0
    assert cuerpo["respaldos"] == []
    assert cuerpo["pendientes"] == []
    assert cuerpo["sensible"] == {"permitida": True, "motivo": ""}


def test_crear_un_respaldo_y_descargarlo() -> None:
    navegador, cab = _admin()
    creado = navegador.post("/v1/admin/instalacion/respaldos", headers=cab)
    assert creado.status_code == 200, creado.text
    nombre = creado.json()["nombre"]
    (juego,) = navegador.get("/v1/admin/instalacion").json()["respaldos"]
    assert juego["nombre"] == nombre
    zip_ = navegador.get(f"/v1/admin/instalacion/respaldos/{nombre}")
    assert zip_.status_code == 200
    assert zip_.headers["content-type"] == "application/zip"
    assert zip_.headers["cache-control"] == "no-store"
    with zipfile.ZipFile(io.BytesIO(zip_.content)) as z:
        assert "ficha.json" in z.namelist()


def test_un_nombre_de_respaldo_fuera_de_la_lista_no_existe() -> None:
    navegador, _ = _admin()
    for nombre in ("no-existe", "%2e%2e%2f%2e%2e%2fsilice.toml"):
        assert navegador.get(f"/v1/admin/instalacion/respaldos/{nombre}").status_code in (404, 400)


def test_los_respaldos_no_se_descargan_desde_la_red() -> None:
    navegador, cab = _admin()
    nombre = navegador.post("/v1/admin/instalacion/respaldos", headers=cab).json()["nombre"]
    remoto, _ = _admin(ip="203.0.113.7")
    respuesta = remoto.get(f"/v1/admin/instalacion/respaldos/{nombre}")
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": REMOTO})


def _evento_perdido(nombre: str = "eventos_perdidos_20261110.json") -> Path:
    archivo = config.carpeta_datos() / nombre
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(
        json.dumps(
            {
                "diferencias": [{"tipo": "revocada", "tabla": "clave_api", "etiqueta": "plugin"}],
                "eventos": [{"x": 1}, {"x": 2}],
                "revisado": False,
            }
        ),
        encoding="utf-8",
    )
    return archivo


def test_los_eventos_perdidos_se_listan_y_se_marcan_revisados() -> None:
    archivo = _evento_perdido()
    navegador, cab = _admin(ip="127.0.0.1")
    cuerpo = navegador.get("/v1/admin/instalacion").json()
    assert cuerpo["pendientes"] == [
        {"nombre": archivo.name, "diferencias": ["revocada: clave_api plugin"], "eventos": 2}
    ]
    # con eventos sin revisar, lo sensible se bloquea (SEG-12) pero revisar sigue siendo posible
    assert cuerpo["sensible"]["permitida"] is False
    hecha = navegador.post(f"/v1/admin/instalacion/eventos/{archivo.name}/revisar", headers=cab)
    assert hecha.status_code == 200, hecha.text
    assert json.loads(archivo.read_text(encoding="utf-8"))["revisado"] is True
    assert navegador.get("/v1/admin/instalacion").json()["pendientes"] == []


def test_revisar_un_evento_que_no_existe_o_con_ruta_ajena() -> None:
    _evento_perdido()
    navegador, cab = _admin()
    for nombre in ("otro.json", "..%2fsilice.toml"):
        r = navegador.post(f"/v1/admin/instalacion/eventos/{nombre}/revisar", headers=cab)
        assert r.status_code in (404, 400)
