"""`/v1/solicitudes`: el contrato y los permisos del registro con código (C9a; spec
2026-11-26-registro-con-codigo §6).

Oráculos a mano: los cuerpos esperados se escriben aquí (campos exactos), el CSRF lo recalcula
`tests.fixtures.sesion_web` y la forma del código es una expresión regular propia. La respuesta del
canje se compara con la de `POST /v1/sesion` de una cuenta de la plantilla: deben tener los mismos
campos y la misma cookie. Datos ficticios (`lucia`, `ejemplo.com`).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import pytest
from sqlalchemy import select

from api import dependencias
from api.main import app
from operacion import config
from seguridad import solicitudes
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import EventoAcceso, SolicitudCuenta, Usuario
from tests.fixtures.claves_api import CABECERA, crear_clave_de_prueba
from tests.fixtures.sesion_web import (
    COOKIE,
    MENSAJE_PERMISO,
    ORIGEN,
    cliente,
    con_cuenta,
    copiar_instalacion,
    entrar,
    plantilla_con_cuentas,
    protegida,
)

PEDIDO = {
    "nombre": "Lucía Prueba",
    "correo": "lucia@ejemplo.com",
    "login": "lucia",
    "contrasena": "clave larga de lucia 2026",
}
MENSAJE_RECIBIDA = (
    "Su solicitud quedó registrada. Cuando el administrador la apruebe, le llegará un código de "
    "20 caracteres a su correo. Escríbalo en “Tengo un código”."
)
MENSAJE_CANJE = "El usuario, la contraseña o el código no son válidos."
MENSAJE_LIMITE = (
    "Hay demasiadas solicitudes pendientes. Pida al administrador que revise las que hay."
)
FORMATO = re.compile(r"^[A-Z2-7]{4}(-[A-Z2-7]{4}){4}$")
CAMPOS_SOLICITUD = {
    "id", "nombre", "login", "correo", "creada", "estado", "papel", "vence", "reutilizada",
}
AJENO = {"Origin": "http://otro.sitio.example"}


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("solicitudes_api"))


@pytest.fixture(autouse=True)
def _instalacion(_plantilla: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantilla)
    solicitudes.CUPO.reiniciar()
    yield
    solicitudes.CUPO.reiniciar()
    dependencias.cerrar_motores()


def _leer(consulta):
    motor = crear_motor(config.ruta_instalacion())
    sesion = abrir_sesion(motor)
    try:
        return consulta(sesion)
    finally:
        sesion.close()
        motor.dispose()


def _pedir(navegador=None, **cambios):
    navegador = navegador or cliente(app)
    return navegador.post("/v1/solicitudes", json={**PEDIDO, **cambios}, headers={"Origin": ORIGEN})


def _id(login: str = "lucia") -> int:
    return _leer(
        lambda s: s.scalar(select(SolicitudCuenta.id).where(SolicitudCuenta.login == login))
    )


def _aprobar(admin, solicitud_id: int, papel: str = "arma"):
    navegador, ficha = admin
    return navegador.post(
        f"/v1/solicitudes/{solicitud_id}/aprobar", json={"papel": papel}, headers=protegida(ficha)
    )


def _canjear(codigo: str, navegador=None, **cambios):
    navegador = navegador or cliente(app)
    cuerpo = {"login": PEDIDO["login"], "contrasena": PEDIDO["contrasena"], "codigo": codigo}
    return navegador.post(
        "/v1/solicitudes/canjear", json={**cuerpo, **cambios}, headers={"Origin": ORIGEN}
    )


@pytest.fixture
def admin():
    return con_cuenta(app, "admin")


# --- POST /v1/solicitudes -------------------------------------------------------------------


def test_cualquiera_sin_sesion_pide_una_cuenta_y_recibe_el_mensaje(admin) -> None:
    respuesta = _pedir()
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json() == {"mensaje": MENSAJE_RECIBIDA}
    assert COOKIE not in respuesta.cookies
    assert _leer(lambda s: s.scalar(select(Usuario).where(Usuario.login == "lucia"))) is None


@pytest.mark.parametrize("login", ["lucia", "admin"])
def test_un_login_en_uso_da_409_sin_decir_donde(login: str) -> None:
    assert _pedir().status_code == 201
    respuesta = _pedir(login=login, correo="otra@ejemplo.com")
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "Ese usuario ya está en uso; elija otro."}


@pytest.mark.parametrize(
    "cambios",
    [{"correo": "sin-arroba"}, {"contrasena": "corta"}, {"login": "x"}, {"nombre": " "},
     {"contrasena": 123}, {"login": None}],
)
def test_datos_malos_dan_422_sin_repetir_la_contrasena(cambios) -> None:
    respuesta = _pedir(**cambios)
    assert respuesta.status_code == 422, respuesta.text
    assert set(respuesta.json()) == {"detalle"}
    assert PEDIDO["contrasena"] not in respuesta.text and "corta" not in respuesta.text


def test_la_sexta_del_mismo_equipo_en_una_hora_da_429() -> None:
    for i in range(5):
        assert _pedir(login=f"persona{i}").status_code == 201
    respuesta = _pedir(login="persona5")
    assert respuesta.status_code == 429
    assert respuesta.json() == {"detalle": MENSAJE_LIMITE}


def test_el_sexto_409_del_mismo_equipo_da_429() -> None:
    """El 409 gasta cupo: no sirve para probar logins sin límite (revisión de seguridad #1)."""
    for _ in range(5):
        assert _pedir(login="admin").status_code == 409
    respuesta = _pedir(login="admin")
    assert respuesta.status_code == 429 and respuesta.json() == {"detalle": MENSAJE_LIMITE}
    fallidas = _leer(
        lambda s: s.scalars(
            select(EventoAcceso.detalle).where(EventoAcceso.tipo == "solicitud fallida")
        ).all()
    )
    assert fallidas == ["login en uso"] * 5


def test_un_origen_ajeno_no_pide_cuentas() -> None:
    respuesta = cliente(app).post("/v1/solicitudes", json=PEDIDO, headers=AJENO)
    assert respuesta.status_code == 403
    assert _id() is None


# --- GET /v1/solicitudes --------------------------------------------------------------------


def test_el_administrador_ve_las_solicitudes_con_sus_campos(admin) -> None:
    _pedir()
    navegador, _ = admin
    respuesta = navegador.get("/v1/solicitudes")
    assert respuesta.status_code == 200
    assert respuesta.headers["Cache-Control"] == "no-store"
    filas = respuesta.json()["solicitudes"]
    assert set(respuesta.json()) == {"solicitudes"}
    assert [set(f) for f in filas] == [CAMPOS_SOLICITUD]
    fila = filas[0]
    assert (fila["nombre"], fila["login"], fila["correo"], fila["estado"]) == (
        "Lucía Prueba", "lucia", "lucia@ejemplo.com", "pendiente"
    )
    assert fila["papel"] is None and fila["vence"] is None and fila["creada"]
    assert fila["reutilizada"] is False


@pytest.mark.parametrize("login", ["ana", "rita"])
def test_sin_el_rol_de_administrador_no_se_ven_ni_se_resuelven(login: str) -> None:
    _pedir()
    navegador, ficha = con_cuenta(app, login)
    assert navegador.get("/v1/solicitudes").json() == {"detalle": MENSAJE_PERMISO}
    for accion, cuerpo in (("aprobar", {"papel": "arma"}), ("rechazar", {})):
        respuesta = navegador.post(
            f"/v1/solicitudes/{_id()}/{accion}", json=cuerpo, headers=protegida(ficha)
        )
        assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_PERMISO}
    assert _leer(lambda s: s.get(SolicitudCuenta, _id()).estado) == "pendiente"


def test_sin_sesion_401_y_con_clave_de_api_403() -> None:
    assert cliente(app).get("/v1/solicitudes").status_code == 401
    clave = crear_clave_de_prueba()
    respuesta = cliente(app).get("/v1/solicitudes", headers={CABECERA: clave})
    assert respuesta.status_code == 403


# --- POST /v1/solicitudes/{id}/aprobar y /rechazar ------------------------------------------


def test_aprobar_devuelve_el_codigo_una_vez_con_su_vencimiento_y_el_mailto(admin) -> None:
    _pedir()
    respuesta = _aprobar(admin, _id(), "revisa")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["Cache-Control"] == "no-store"
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"codigo", "vence", "mailto"}
    assert FORMATO.fullmatch(cuerpo["codigo"])
    assert cuerpo["mailto"].startswith("mailto:lucia@ejemplo.com?subject=")
    assert cuerpo["codigo"] in unquote(cuerpo["mailto"])
    navegador, _ = admin
    lista = navegador.get("/v1/solicitudes")
    sin_guiones = cuerpo["codigo"].replace("-", "")
    assert cuerpo["codigo"] not in lista.text and sin_guiones not in lista.text
    fila = lista.json()["solicitudes"][0]
    assert (fila["estado"], fila["papel"], fila["vence"]) == ("aprobada", "revisa", cuerpo["vence"])


def test_aprobar_exige_csrf(admin) -> None:
    _pedir()
    navegador, _ = admin
    respuesta = navegador.post(
        f"/v1/solicitudes/{_id()}/aprobar", json={"papel": "arma"}, headers={"Origin": ORIGEN}
    )
    assert respuesta.status_code == 403


@pytest.mark.parametrize("cuerpo", [{"papel": "administrador"}, {}, {"papel": 1}])
def test_un_papel_que_no_es_arma_ni_revisa_da_422(admin, cuerpo) -> None:
    _pedir()
    navegador, ficha = admin
    respuesta = navegador.post(
        f"/v1/solicitudes/{_id()}/aprobar", json=cuerpo, headers=protegida(ficha)
    )
    assert respuesta.status_code == 422 and set(respuesta.json()) == {"detalle"}


def test_una_solicitud_que_no_existe_da_404(admin) -> None:
    assert _aprobar(admin, 999).status_code == 404
    navegador, ficha = admin
    assert navegador.post(
        "/v1/solicitudes/999/rechazar", json={}, headers=protegida(ficha)
    ).status_code == 404


def test_rechazar_responde_un_mensaje_y_despues_no_se_aprueba(admin) -> None:
    _pedir()
    navegador, ficha = admin
    respuesta = navegador.post(
        f"/v1/solicitudes/{_id()}/rechazar", json={}, headers=protegida(ficha)
    )
    assert respuesta.status_code == 200
    assert set(respuesta.json()) == {"mensaje"} and respuesta.json()["mensaje"]
    assert _aprobar(admin, _id()).status_code == 409


# --- POST /v1/solicitudes/canjear -----------------------------------------------------------


def test_el_canje_abre_la_sesion_igual_que_entrar(admin) -> None:
    _pedir()
    codigo = _aprobar(admin, _id()).json()["codigo"]
    navegador = cliente(app)
    respuesta = _canjear(codigo.lower(), navegador)
    assert respuesta.status_code == 200, respuesta.text
    referencia = entrar(cliente(app), "ana")
    assert set(respuesta.json()) == set(referencia.json())
    cuerpo = respuesta.json()
    assert (cuerpo["login"], cuerpo["nombre"], cuerpo["roles"]) == (
        "lucia", "Lucía Prueba", ["arma"]
    )
    assert cuerpo["debe_cambiar_clave"] is False and "editar_hoja" in cuerpo["acciones"]
    assert respuesta.cookies.get(COOKIE)
    cookie_canje = respuesta.headers["set-cookie"].split(";", 1)[1]
    assert cookie_canje == referencia.headers["set-cookie"].split(";", 1)[1]
    sesion = navegador.get("/v1/sesion")
    assert sesion.status_code == 200 and sesion.json()["login"] == "lucia"
    assert _leer(lambda s: s.get(SolicitudCuenta, _id()).estado) == "usada"


def test_el_segundo_canje_y_un_codigo_ajeno_dan_401_con_el_mismo_mensaje(admin) -> None:
    _pedir()
    codigo = _aprobar(admin, _id()).json()["codigo"]
    for respuesta in (
        _canjear("AAAA-BBBB-CCCC-DDDD-EEEE"),
        _canjear(codigo, contrasena="otra clave larga que no es"),
        _canjear(codigo, login="nadie"),
    ):
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detalle": MENSAJE_CANJE}
        assert COOKIE not in respuesta.cookies
    assert _canjear(codigo).status_code == 200
    segundo = _canjear(codigo)
    assert segundo.status_code == 401 and segundo.json() == {"detalle": MENSAJE_CANJE}


def test_el_canje_con_un_origen_ajeno_da_403(admin) -> None:
    _pedir()
    codigo = _aprobar(admin, _id()).json()["codigo"]
    cuerpo = {"login": "lucia", "contrasena": PEDIDO["contrasena"], "codigo": codigo}
    respuesta = cliente(app).post("/v1/solicitudes/canjear", json=cuerpo, headers=AJENO)
    assert respuesta.status_code == 403
    assert _leer(lambda s: s.get(SolicitudCuenta, _id()).estado) == "aprobada"


def test_un_cuerpo_malo_en_el_canje_da_422_sin_eco() -> None:
    respuesta = cliente(app).post(
        "/v1/solicitudes/canjear",
        json={"login": "lucia", "contrasena": 12345678901, "codigo": "secreto-pegado"},
        headers={"Origin": ORIGEN},
    )
    assert respuesta.status_code == 422
    assert "secreto-pegado" not in respuesta.text and "12345678901" not in respuesta.text


def test_el_registro_de_accesos_no_guarda_ni_el_codigo_ni_la_contrasena(admin) -> None:
    _pedir()
    codigo = _aprobar(admin, _id()).json()["codigo"]
    _canjear(codigo, contrasena="otra clave larga que no es")
    _canjear(codigo)
    textos = _leer(
        lambda s: [f"{e.login_intentado} {e.detalle}" for e in s.scalars(select(EventoAcceso))]
    )
    secretos = (codigo, codigo.replace("-", ""), PEDIDO["contrasena"], "otra clave larga")
    assert not [t for t in textos for secreto in secretos if secreto in t]


# --- hallazgos de C9a (lote G4): #5, #6, #8 y #9 en HTTP ------------------------------------


def test_el_canje_da_401_generico_si_quien_aprobo_dejo_de_ser_administrador(admin) -> None:
    """#5: una aprobación no sobrevive a quien la dio (desactivado o sin rol de administrador)."""
    _pedir()
    nav_admin, ficha_admin = admin
    id_ana = _leer(lambda s: s.scalar(select(Usuario.id).where(Usuario.login == "ana")))
    subir = nav_admin.post(
        f"/v1/cuentas/{id_ana}/roles",
        json={"roles": ["arma", "administrador"]},
        headers=protegida(ficha_admin),
    )
    assert subir.status_code == 200, subir.text
    ana_admin = con_cuenta(app, "ana")
    codigo = _aprobar(ana_admin, _id()).json()["codigo"]
    bajar = nav_admin.post(
        f"/v1/cuentas/{id_ana}/desactivar",
        json={},
        headers=protegida(ficha_admin),
    )
    assert bajar.status_code == 200, bajar.text
    respuesta = _canjear(codigo)
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": MENSAJE_CANJE}
    assert COOKIE not in respuesta.cookies
    ultimo = _leer(
        lambda s: s.scalars(select(EventoAcceso).order_by(EventoAcceso.id.desc())).first()
    )
    assert ultimo.tipo == "codigo rechazado" and ultimo.detalle == "aprobador revocado"


def test_get_solicitudes_marca_reutilizada_tras_rechazar_y_volver_a_pedir(admin) -> None:
    """#6: al reutilizar una rechazada queda rastro en el evento y `reutilizada: true` en GET."""
    _pedir()
    navegador, ficha = admin
    assert (
        navegador.post(
            f"/v1/solicitudes/{_id()}/rechazar", json={}, headers=protegida(ficha)
        ).status_code
        == 200
    )
    assert _pedir(correo="lucia2@ejemplo.com").status_code == 201
    lista = navegador.get("/v1/solicitudes")
    assert lista.status_code == 200
    fila = lista.json()["solicitudes"][0]
    assert fila["estado"] == "pendiente" and fila["reutilizada"] is True
    evento = _leer(
        lambda s: s.scalars(
            select(EventoAcceso)
            .where(EventoAcceso.tipo == "solicitud")
            .order_by(EventoAcceso.id.desc())
        ).first()
    )
    assert evento.detalle == (
        "reutiliza una solicitud rechazada resuelta por Admin de Prueba <admin>"
    )


@pytest.mark.parametrize("ruta", ["/v1/solicitudes", "/v1/solicitudes/canjear"])
@pytest.mark.parametrize("cuerpo", [b"{}", b'{"login": 123}', b"{json roto"])
def test_origen_ajeno_da_403_antes_de_leer_un_cuerpo_invalido_o_roto(
    ruta: str, cuerpo: bytes
) -> None:
    """#8: la puerta de `Origin` corre antes de leer el cuerpo (403 con no-store, nunca 422)."""
    respuesta = cliente(app).post(
        ruta,
        content=cuerpo,
        headers={**AJENO, "Content-Type": "application/json"},
    )
    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.headers["Cache-Control"] == "no-store"
    assert set(respuesta.json()) == {"detalle"}


def test_get_solicitudes_calcula_vencida_sin_escribir_en_la_base(admin) -> None:
    """#9: GET /v1/solicitudes calcula `vencida` al responder y no modifica la tabla."""
    _pedir()
    solicitud_id = _id()
    assert _aprobar(admin, solicitud_id).status_code == 200
    motor = crear_motor(config.ruta_instalacion())
    sesion = abrir_sesion(motor)
    try:
        fila = sesion.get(SolicitudCuenta, solicitud_id)
        fila.vence = datetime(2026, 1, 1, 0, 0, 0)
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()
    navegador, _ = admin
    respuesta = navegador.get("/v1/solicitudes")
    assert respuesta.status_code == 200
    assert respuesta.json()["solicitudes"][0]["estado"] == "vencida"
    assert _leer(lambda s: s.get(SolicitudCuenta, solicitud_id).estado) == "aprobada"
