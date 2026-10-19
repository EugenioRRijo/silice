"""`/v1/cuentas` y `/v1/accesos`: pestañas Cuentas y Accesos de Administración (migración).

Paridad con `ui/paginas/administracion.py` (acción `ADMINISTRAR_CUENTAS`): los mensajes de éxito
y de error son los literales de Streamlit y de `seguridad.cuentas`, escritos aquí a mano. Los
datos son
ficticios (admin, ana, rita, tomas, luis). Ninguna operación de estas pestañas es `Sensible` en
Streamlit (no llaman a `exigir_local`), así que la ruta exige el rol y no el propio equipo.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from sqlalchemy import select

from api import dependencias
from api.main import app
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import EventoAcceso, Usuario
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    CUENTAS,
    MENSAJE_PERMISO,
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

TEMPORAL = "temporal ficticia 123"
OTRA = "otra temporal ficticia 456"
CAMPOS_CUENTA = {"id", "login", "nombre", "roles", "activa"}


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("cuentas_api"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    yield
    dependencias.cerrar_motores()


@pytest.fixture
def admin():
    return con_cuenta(app, "admin")


def _consulta(sql):
    from operacion import config

    motor = crear_motor(config.ruta_instalacion())
    sesion = abrir_sesion(motor)
    try:
        return sql(sesion)
    finally:
        sesion.close()
        motor.dispose()


def _id_de(navegador, login: str) -> int:
    filas = navegador.get("/v1/cuentas").json()["cuentas"]
    return next(f["id"] for f in filas if f["login"] == login)


def _post(navegador, ficha, ruta, cuerpo=None):
    return navegador.post(ruta, json=cuerpo or {}, headers=protegida(ficha))


def _alta(navegador, ficha, login="luis", roles=("administrador",), clave=TEMPORAL, nombre="Luis"):
    return _post(
        navegador,
        ficha,
        "/v1/cuentas",
        {"login": login, "nombre": nombre, "roles": list(roles), "contrasena_temporal": clave},
    )


# --- lectura ---------------------------------------------------------------------------------


def test_lista_las_cuentas_ordenadas_por_usuario_sin_credenciales(admin) -> None:
    navegador, _ = admin
    respuesta = navegador.get("/v1/cuentas")
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert [c["login"] for c in cuerpo["cuentas"]] == ["admin", "ana", "rita", "tomas"]
    assert all(set(c) == CAMPOS_CUENTA for c in cuerpo["cuentas"])
    ana = next(c for c in cuerpo["cuentas"] if c["login"] == "ana")
    assert ana["roles"] == ["arma"] and ana["activa"] is True and ana["nombre"] == "Ana"
    assert "argon2" not in respuesta.text and "huella" not in respuesta.text
    assert cuerpo["aviso_arma_y_revisa"] == (
        "Esta cuenta podrá revisar paquetes que ella misma armó; la vista de revisión lo indicará."
    )


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_solo_el_administrador_lee_y_escribe(login: str) -> None:
    navegador, ficha = con_cuenta(app, login)
    for respuesta in (
        navegador.get("/v1/cuentas"),
        navegador.get("/v1/accesos"),
        _alta(navegador, ficha),
        _post(navegador, ficha, "/v1/cuentas/1/desactivar"),
    ):
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detalle": MENSAJE_PERMISO}


def test_sin_sesion_401_y_la_clave_de_api_no_administra_cuentas() -> None:
    assert cliente(app).get("/v1/cuentas").status_code == 401
    assert cliente(app).get("/v1/accesos").status_code == 401
    clave = crear_clave_de_prueba()
    for ruta in ("/v1/cuentas", "/v1/accesos"):
        respuesta = cliente(app).get(ruta, headers={CABECERA: clave})
        assert respuesta.status_code == 403, respuesta.text
        assert "sesión" in respuesta.json()["detalle"]


def test_toda_escritura_exige_csrf_y_origen(admin) -> None:
    navegador, ficha = admin
    cuerpo = {"login": "luis", "nombre": "L", "roles": ["arma"], "contrasena_temporal": TEMPORAL}
    assert navegador.post("/v1/cuentas", json=cuerpo).status_code == 403
    sin_origen = protegida(ficha, origen=None)
    assert navegador.post("/v1/cuentas", json=cuerpo, headers=sin_origen).status_code == 403
    assert _consulta(lambda s: s.scalar(select(Usuario).where(Usuario.login == "luis"))) is None


# --- alta ------------------------------------------------------------------------------------


def test_alta_crea_la_cuenta_con_contrasena_temporal_y_no_la_devuelve(admin, caplog) -> None:
    navegador, ficha = admin
    caplog.set_level(logging.DEBUG)
    respuesta = _alta(navegador, ficha, roles=("arma", "revisa"), nombre="Luis Ficticio")
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert set(cuerpo["cuenta"]) == CAMPOS_CUENTA
    assert cuerpo["cuenta"]["login"] == "luis" and cuerpo["cuenta"]["roles"] == ["arma", "revisa"]
    assert cuerpo["mensaje"] == "Cuenta creada. La persona deberá cambiar la contraseña al entrar."
    assert cuerpo["aviso"].startswith("Esta cuenta podrá revisar paquetes")
    assert TEMPORAL not in respuesta.text and TEMPORAL not in caplog.text
    fila = _consulta(lambda s: s.scalar(select(Usuario).where(Usuario.login == "luis")))
    assert fila.debe_cambiar_clave is True and fila.huella_clave.startswith("$argon2")
    detalles = _consulta(lambda s: " ".join(s.scalars(select(EventoAcceso.detalle))))
    assert TEMPORAL not in detalles
    entrada = cliente(app).post("/v1/sesion", json={"login": "luis", "contrasena": TEMPORAL})
    assert entrada.status_code == 200 and entrada.json()["debe_cambiar_clave"] is True


def test_alta_sin_aviso_cuando_no_se_mezclan_arma_y_revisa(admin) -> None:
    navegador, ficha = admin
    cuerpo = _alta(navegador, ficha, roles=("arma",)).json()
    assert cuerpo["aviso"] is None


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"login": "ana"}, "Ya existe una cuenta con el usuario 'ana'."),
        ({"login": "A B"}, "El usuario son 3 a 40 caracteres: letras, números, punto o guion."),
        ({"contrasena_temporal": "corta"}, "La contraseña debe tener al menos 10 caracteres."),
        ({"contrasena_temporal": "x" * 129}, "La contraseña admite hasta 128 caracteres."),
        ({"contrasena_temporal": "luis"}, "La contraseña debe tener al menos 10 caracteres."),
        ({"contrasena_temporal": "password123"}, "Esa contraseña es demasiado común; elija otra."),
        ({"roles": []}, "una cuenta necesita al menos un rol"),
    ],
)
def test_alta_rechaza_con_el_mensaje_de_seguridad_cuentas(admin, cambios, mensaje) -> None:
    navegador, ficha = admin
    base = {"login": "luis", "nombre": "Luis", "roles": ["arma"], "contrasena_temporal": TEMPORAL}
    respuesta = _post(navegador, ficha, "/v1/cuentas", base | cambios)
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json() == {"detalle": mensaje}


def test_alta_con_cuerpo_invalido_no_repite_lo_enviado(admin) -> None:
    navegador, ficha = admin
    respuesta = _post(
        navegador,
        ficha,
        "/v1/cuentas",
        {"login": "luis", "nombre": "L", "roles": ["dios"], "contrasena_temporal": TEMPORAL},
    )
    assert respuesta.status_code == 422
    assert list(respuesta.json()) == ["detalle"]
    assert TEMPORAL not in respuesta.text and "dios" not in respuesta.text


# --- roles, desactivar, reactivar -------------------------------------------------------------


def test_cambiar_roles_cierra_las_sesiones_de_la_cuenta(admin) -> None:
    navegador, ficha = admin
    ana, _ = con_cuenta(app, "ana")
    destino = _id_de(navegador, "ana")
    respuesta = _post(navegador, ficha, f"/v1/cuentas/{destino}/roles", {"roles": ["revisa"]})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["mensaje"] == "Roles cambiados; sus sesiones se cerraron."
    assert respuesta.json()["cuenta"]["roles"] == ["revisa"]
    assert ana.get("/v1/sesion").status_code == 401


def test_cambiar_roles_devuelve_el_aviso_de_arma_y_revisa(admin) -> None:
    navegador, ficha = admin
    destino = _id_de(navegador, "ana")
    cuerpo = _post(
        navegador, ficha, f"/v1/cuentas/{destino}/roles", {"roles": ["arma", "revisa"]}
    ).json()
    assert cuerpo["aviso"].startswith("Esta cuenta podrá revisar paquetes")


def test_no_se_puede_rebajar_al_unico_administrador(admin) -> None:
    navegador, ficha = admin
    propio = _id_de(navegador, "admin")
    respuesta = _post(navegador, ficha, f"/v1/cuentas/{propio}/roles", {"roles": ["arma"]})
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "Debe quedar al menos un administrador activo."}
    assert navegador.get("/v1/sesion").status_code == 200  # nada cambió: su ficha sigue abierta


def test_con_otro_administrador_activo_si_se_puede_rebajar(admin) -> None:
    navegador, ficha = admin
    assert _alta(navegador, ficha).status_code == 201  # luis, administrador
    propio = _id_de(navegador, "admin")
    assert (
        _post(navegador, ficha, f"/v1/cuentas/{propio}/roles", {"roles": ["arma"]}).status_code
        == 200
    )


def test_desactivar_conserva_la_cuenta_y_cierra_sus_sesiones(admin) -> None:
    navegador, ficha = admin
    rita, _ = con_cuenta(app, "rita")
    destino = _id_de(navegador, "rita")
    respuesta = _post(navegador, ficha, f"/v1/cuentas/{destino}/desactivar")
    assert respuesta.status_code == 200
    assert respuesta.json()["mensaje"] == "Cuenta desactivada; sus registros se conservan."
    assert respuesta.json()["cuenta"]["activa"] is False
    assert rita.get("/v1/sesion").status_code == 401
    assert (
        cliente(app)
        .post("/v1/sesion", json={"login": "rita", "contrasena": CUENTAS["rita"][0]})
        .status_code
        == 401
    )
    reactivada = _post(navegador, ficha, f"/v1/cuentas/{destino}/reactivar")
    assert reactivada.json()["mensaje"] == "Cuenta reactivada."
    assert reactivada.json()["cuenta"]["activa"] is True


def test_no_se_puede_desactivar_al_unico_administrador(admin) -> None:
    navegador, ficha = admin
    respuesta = _post(navegador, ficha, f"/v1/cuentas/{_id_de(navegador, 'admin')}/desactivar")
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": "Debe quedar al menos un administrador activo."}


def test_cuenta_inexistente_404_con_el_mensaje_de_cuentas(admin) -> None:
    navegador, ficha = admin
    for accion in ("desactivar", "reactivar", "desbloquear", "restablecer", "roles"):
        cuerpo = {"contrasena_temporal": OTRA, "roles": ["arma"]}
        respuesta = _post(navegador, ficha, f"/v1/cuentas/9999/{accion}", cuerpo)
        assert respuesta.status_code == 404, (accion, respuesta.text)
        assert respuesta.json() == {"detalle": "no hay una cuenta con id 9999"}


# --- desbloquear y restablecer ----------------------------------------------------------------


def test_desbloquear_devuelve_el_acceso_a_una_cuenta_bloqueada(admin) -> None:
    navegador, ficha = admin
    anonimo = cliente(app)
    for _ in range(5):
        anonimo.post("/v1/sesion", json={"login": "ana", "contrasena": "equivocada ficticia"})
    bloqueada = anonimo.post("/v1/sesion", json={"login": "ana", "contrasena": CUENTAS["ana"][0]})
    assert bloqueada.status_code == 423
    respuesta = _post(navegador, ficha, f"/v1/cuentas/{_id_de(navegador, 'ana')}/desbloquear")
    assert respuesta.status_code == 200
    assert respuesta.json()["mensaje"] == "Cuenta desbloqueada."
    entra = anonimo.post("/v1/sesion", json={"login": "ana", "contrasena": CUENTAS["ana"][0]})
    assert entra.status_code == 200


def test_restablecer_fija_una_temporal_y_no_la_devuelve(admin, caplog) -> None:
    navegador, ficha = admin
    caplog.set_level(logging.DEBUG)
    ana, _ = con_cuenta(app, "ana")
    respuesta = _post(
        navegador,
        ficha,
        f"/v1/cuentas/{_id_de(navegador, 'ana')}/restablecer",
        {"contrasena_temporal": OTRA},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json()["mensaje"] == "Contraseña restablecida; sus sesiones se cerraron."
    assert OTRA not in respuesta.text and OTRA not in caplog.text
    assert ana.get("/v1/sesion").status_code == 401
    entra = cliente(app).post("/v1/sesion", json={"login": "ana", "contrasena": OTRA})
    assert entra.status_code == 200 and entra.json()["debe_cambiar_clave"] is True
    detalles = _consulta(lambda s: " ".join(s.scalars(select(EventoAcceso.detalle))))
    assert OTRA not in detalles


@pytest.mark.parametrize(
    ("clave", "mensaje"),
    [
        ("corta", "La contraseña debe tener al menos 10 caracteres."),
        ("ana", "La contraseña debe tener al menos 10 caracteres."),
        ("password123", "Esa contraseña es demasiado común; elija otra."),
    ],
)
def test_restablecer_aplica_la_politica_de_contrasenas(admin, clave, mensaje) -> None:
    navegador, ficha = admin
    respuesta = _post(
        navegador,
        ficha,
        f"/v1/cuentas/{_id_de(navegador, 'ana')}/restablecer",
        {"contrasena_temporal": clave},
    )
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": mensaje}


def test_restablecer_con_cuerpo_invalido_no_repite_lo_enviado(admin) -> None:
    navegador, ficha = admin
    respuesta = _post(
        navegador,
        ficha,
        f"/v1/cuentas/{_id_de(navegador, 'ana')}/restablecer",
        {"contrasena_temporal": 12345678901},
    )
    assert respuesta.status_code == 422
    assert list(respuesta.json()) == ["detalle"] and "12345678901" not in respuesta.text


# --- accesos ---------------------------------------------------------------------------------


def test_accesos_son_los_ultimos_200_mas_nuevos_primero(admin) -> None:
    navegador, ficha = admin
    anonimo = cliente(app, "10.0.0.7")
    for _ in range(3):
        anonimo.post("/v1/sesion", json={"login": "ficticio", "contrasena": "equivocada ficticia"})
    respuesta = navegador.get("/v1/accesos")
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    cuerpo = respuesta.json()
    assert cuerpo["maximo"] == 200
    eventos = cuerpo["eventos"]
    assert set(eventos[0]) == {"id", "fecha_hora", "tipo", "usuario", "ip", "detalle"}
    assert [e["tipo"] for e in eventos[:3]] == ["fallo", "fallo", "fallo"]
    assert eventos[0]["usuario"] == "ficticio" and eventos[0]["ip"] == "10.0.0.7"
    ids = [e["id"] for e in eventos]
    assert ids == sorted(ids, reverse=True)
    assert "T" not in eventos[0]["fecha_hora"]  # «AAAA-MM-DD hh:mm:ss», como Streamlit


def test_accesos_se_limita_a_200(admin) -> None:
    navegador, _ = admin
    from datetime import datetime

    from operacion import config

    motor = crear_motor(config.ruta_instalacion())
    sesion = abrir_sesion(motor)
    sesion.add_all(
        EventoAcceso(fecha_hora=datetime(2026, 1, 1), tipo="fallo", login_intentado="x")
        for _ in range(230)
    )
    sesion.commit()
    sesion.close()
    motor.dispose()
    assert len(navegador.get("/v1/accesos").json()["eventos"]) == 200
    assert len(navegador.get("/v1/accesos?limite=5").json()["eventos"]) == 5
    assert navegador.get("/v1/accesos?limite=201").status_code == 422


def test_el_registro_de_accesos_es_de_solo_lectura(admin) -> None:
    navegador, ficha = admin
    for metodo in ("POST", "PUT", "PATCH", "DELETE"):
        r = navegador.request(metodo, "/v1/accesos", json={}, headers=protegida(ficha))
        assert r.status_code == 405
