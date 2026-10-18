"""Cambio de contraseña obligatorio en la interfaz nueva y lo que `/v1/sesion` informa (puntos 6 y 7
de la ola 0a de la sesión 2b).

- Una cuenta con la contraseña temporal entra (200, `debe_cambiar_clave: true`, `acciones: []`) y
  recibe una cookie que solo sirve para `POST /v1/sesion/contrasena`, `GET` y `DELETE /v1/sesion`:
  cualquier otra ruta responde 403 con un mensaje llano. Antes de la ola 0a, el 403 venía en la
  entrada y sin cookie («cambie su contraseña en la interfaz clásica»).
- `POST /v1/sesion/contrasena` `{actual, nueva}` (CSRF y `Origin`) usa
  `seguridad.cuentas.cambiar_contrasena`: la política de siempre, todas las fichas de la cuenta se
  cierran y se abre una nueva (como en Streamlit, `ui/acceso.py`). Los 422 no repiten lo enviado.
- `GET/POST /v1/sesion` informan `debe_cambiar_clave`, `acciones` (las de su rol) y `modo_entrega`.

Oráculos a mano: las acciones de cada rol (spec S3 §5.1, en el orden de la matriz), los mensajes de
`seguridad.cuentas` como literales y el CSRF recalculado con `hashlib`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api import caso_web, dependencias
from api.main import app
from operacion import config
from operacion.base_datos import preparar_base
from operacion.instalacion import sesion_de_instalacion
from seguridad import sesiones
from seguridad.modelo import EventoAcceso, Sesion, Usuario
from tests.fixtures.sesion_web import (
    CUENTAS,
    NUEVA,
    ORIGEN,
    cliente,
    con_cuenta,
    copiar_instalacion,
    csrf,
    entrar,
    ficha_de,
    plantilla_con_cuentas,
    protegida,
)

TEMPORAL = CUENTAS["tomas"][0]
PROPIA = "la contrasena propia de tomas"
MENSAJE_TEMPORAL = "Su contraseña es temporal: elija una propia antes de seguir."
MENSAJE_FALLO = "Usuario o contraseña incorrectos."
MENSAJE_CORTA = "La contraseña debe tener al menos 10 caracteres."
ACCIONES = {
    "ana": [
        "editar_hoja",
        "convertir_y_reajustar",
        "control_de_obra",
        "decidir_recuperacion",
        "entregar_paquete",
        "leer_proyecto",
        "cambiar_caso",
    ],
    "rita": ["leer_proyecto", "revisar_paquete"],
    "admin": [
        "cambiar_caso",
        "administrar_cuentas",
        "administrar_empresa",
        "administrar_precios",
        "administrar_red_y_api",
        "cambiar_carpeta_de_datos",
    ],
}
ROLES = {"ana": ["arma"], "rita": ["revisa"], "admin": ["administrador"]}
NOMBRES = {"ana": "Ana", "rita": "Rita", "admin": "Admin de Prueba"}


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("contrasena"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _tomas_dentro() -> tuple[TestClient, str]:
    navegador = cliente(app)
    respuesta = entrar(navegador, "tomas")
    assert respuesta.status_code == 200, respuesta.text
    return navegador, ficha_de(respuesta)


def _cambiar(navegador: TestClient, ficha: str, actual: str = TEMPORAL, nueva: str = PROPIA):
    return navegador.post(
        "/v1/sesion/contrasena",
        json={"actual": actual, "nueva": nueva},
        headers=protegida(ficha),
    )


def _abiertas(login: str) -> list[str]:
    with sesion_de_instalacion() as sesion:
        usuario = sesion.scalar(select(Usuario).where(Usuario.login == login))
        return list(
            sesion.scalars(
                select(Sesion.huella_ficha).where(
                    Sesion.usuario_id == usuario.id, Sesion.cerrada.is_(False)
                )
            )
        )


# --- lo que informa /v1/sesion ---------------------------------------------------------------


@pytest.mark.parametrize("login", ["ana", "rita", "admin"])
def test_entrar_y_consultar_informan_acciones_y_modo_entrega(login: str) -> None:
    navegador = cliente(app)
    respuesta = entrar(navegador, login)
    ficha = ficha_de(respuesta)
    esperado = {
        "login": login,
        "nombre": NOMBRES[login],
        "roles": ROLES[login],
        "csrf": csrf(ficha),
        "debe_cambiar_clave": False,
        "acciones": ACCIONES[login],
        "modo_entrega": False,
    }
    assert respuesta.json() == esperado
    assert navegador.get("/v1/sesion").json() == esperado


def test_el_modo_entrega_viaja_en_la_sesion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILICE_MODO_ENTREGA", "1")
    navegador, _ = con_cuenta(app, "ana")
    assert navegador.get("/v1/sesion").json()["modo_entrega"] is True


# --- la cookie restringida -------------------------------------------------------------------


def test_la_cuenta_temporal_entra_con_una_cookie_restringida() -> None:
    navegador = cliente(app)
    respuesta = entrar(navegador, "tomas")
    assert respuesta.status_code == 200, respuesta.text
    ficha = ficha_de(respuesta)
    cuerpo = respuesta.json()
    assert cuerpo["debe_cambiar_clave"] is True and cuerpo["acciones"] == []
    assert cuerpo["csrf"] == csrf(ficha)
    consulta = navegador.get("/v1/sesion")
    assert consulta.status_code == 200 and consulta.json() == cuerpo


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("GET", "/v1/casos"),
        ("POST", "/v1/casos/actual"),
        ("GET", "/v1/proyectos"),
        ("GET", "/partidas"),
        ("POST", "/presupuestos"),
        ("POST", "/v1/libros/auditoria"),
        ("POST", "/v1/auditorias"),
    ],
)
def test_la_cookie_restringida_no_sirve_para_ninguna_otra_ruta(metodo: str, ruta: str) -> None:
    navegador, ficha = _tomas_dentro()
    respuesta = navegador.request(metodo, ruta, json={}, headers=protegida(ficha))
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_TEMPORAL})


def test_la_cookie_restringida_sirve_para_salir() -> None:
    navegador, ficha = _tomas_dentro()
    assert navegador.delete("/v1/sesion", headers=protegida(ficha)).status_code == 204
    assert _abiertas("tomas") == []


# --- POST /v1/sesion/contrasena --------------------------------------------------------------


def test_cambiar_la_contrasena_abre_una_ficha_normal_y_cierra_las_demas() -> None:
    otro, ficha_otra = _tomas_dentro()  # la misma cuenta en otro navegador
    navegador, ficha = _tomas_dentro()
    respuesta = _cambiar(navegador, ficha)
    assert respuesta.status_code == 200, respuesta.text
    nueva = ficha_de(respuesta)
    assert nueva not in (ficha, ficha_otra)
    assert respuesta.json() == {
        "login": "tomas",
        "nombre": "Tomas",
        "roles": ["arma"],
        "csrf": csrf(nueva),
        "debe_cambiar_clave": False,
        "acciones": ACCIONES["ana"],
        "modo_entrega": False,
    }
    assert _abiertas("tomas") == [sesiones.huella_de(nueva)]
    assert navegador.get("/v1/casos").status_code == 200  # ya no está restringida
    assert otro.get("/v1/sesion").status_code == 401
    assert entrar(cliente(app), "tomas", TEMPORAL).status_code == 401
    assert entrar(cliente(app), "tomas", PROPIA).status_code == 200
    for texto in (TEMPORAL, PROPIA, ficha, nueva):
        assert texto not in respuesta.text
    with sesion_de_instalacion() as sesion:
        tipos = list(sesion.scalars(select(EventoAcceso.tipo).where(
            EventoAcceso.login_intentado == "tomas"
        )))
    assert "cambio de clave" in tipos


def test_un_cambio_voluntario_conserva_el_caso_elegido() -> None:
    carpeta = config.carpeta_casos()
    carpeta.mkdir(parents=True, exist_ok=True)
    preparar_base(carpeta / "anexo.db")
    navegador, ficha = con_cuenta(app, "ana")
    elegido = navegador.post(
        "/v1/casos/actual", json={"nombre": "anexo.db"}, headers=protegida(ficha)
    )
    assert elegido.status_code == 200, elegido.text
    respuesta = _cambiar(navegador, ficha, NUEVA, "una tercera contrasena larga")
    assert respuesta.status_code == 200, respuesta.text
    assert navegador.get("/v1/casos").json()["actual"]["nombre"] == "anexo.db"
    assert caso_web.elegido(sesiones.huella_de(ficha)) is None


def test_la_contrasena_actual_equivocada_da_403_y_sigue_restringida() -> None:
    navegador, ficha = _tomas_dentro()
    respuesta = _cambiar(navegador, ficha, actual="no es la temporal de tomas")
    assert (respuesta.status_code, respuesta.json()) == (403, {"detalle": MENSAJE_FALLO})
    assert navegador.get("/v1/sesion").json()["debe_cambiar_clave"] is True
    assert _abiertas("tomas") == [sesiones.huella_de(ficha)]


def test_una_contrasena_nueva_fuera_de_la_politica_da_422_con_su_motivo() -> None:
    navegador, ficha = _tomas_dentro()
    for nueva, motivo in (
        ("corta", MENSAJE_CORTA),
        ("tomas", MENSAJE_CORTA),
        ("tomas     ", "La contraseña no puede ser igual al usuario."),
    ):
        respuesta = _cambiar(navegador, ficha, nueva=nueva)
        assert (respuesta.status_code, respuesta.json()) == (422, {"detalle": motivo}), nueva
    assert navegador.get("/v1/sesion").json()["debe_cambiar_clave"] is True


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"actual": TEMPORAL},
        {"actual": TEMPORAL, "nueva": 1234567890123},
        {"actual": TEMPORAL, "nueva": "n" * 129},
        {"actual": ["secreto-en-lista"], "nueva": PROPIA},
    ],
    ids=["sin-nueva", "numero", "larga", "lista"],
)
def test_un_cuerpo_invalido_da_422_sin_repetir_lo_enviado(cuerpo: dict) -> None:
    navegador, ficha = _tomas_dentro()
    respuesta = navegador.post("/v1/sesion/contrasena", json=cuerpo, headers=protegida(ficha))
    assert respuesta.status_code == 422
    assert set(respuesta.json()) == {"detalle"}
    for valor in cuerpo.values():
        texto = valor[0] if isinstance(valor, list) else str(valor)
        assert texto not in respuesta.text


def test_sin_sesion_da_401_y_sin_csrf_u_origen_da_403() -> None:
    sin_sesion = cliente(app).post(
        "/v1/sesion/contrasena", json={"actual": TEMPORAL, "nueva": PROPIA},
        headers={"Origin": ORIGEN},
    )
    assert sin_sesion.status_code == 401
    navegador, ficha = _tomas_dentro()
    sin_csrf = navegador.post(
        "/v1/sesion/contrasena", json={"actual": TEMPORAL, "nueva": PROPIA},
        headers={"Origin": ORIGEN},
    )
    ajeno = navegador.post(
        "/v1/sesion/contrasena", json={"actual": TEMPORAL, "nueva": PROPIA},
        headers=protegida(ficha, "http://atacante.ejemplo"),
    )
    assert (sin_csrf.status_code, ajeno.status_code) == (403, 403)
    assert navegador.get("/v1/sesion").json()["debe_cambiar_clave"] is True
