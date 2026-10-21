"""Acceso del navegador a la API por cuenta y cookie de sesión (RT-9; RS2-4, RS2-5, RS2-6; RF-113).

`/v1/sesion` se ejerce sobre `api.main.app` real (con la protección de red y de hosts). La
dependencia `exigir_clave_o_sesion` se ejerce sobre una aplicación de prueba que monta el mismo
router de sesión, una ruta sonda y el router real de `/v1/libros` con esa dependencia. Desde la
2.3b `api.main` monta las rutas de libros con esa misma dependencia; la regresión «con clave
responde igual que antes» se mide contra una aplicación de referencia con `exigir_clave_api`
(el `CON_CLAVE` de antes) y las pruebas de la réplica (`test_api_libros_replica.py`) ejercen la
sesión sobre `api.main.app`.

Oráculos, ninguno sale del código bajo prueba:

- El CSRF se recalcula aquí con `hashlib` desde la ficha de la cookie (RS2-4): `sha256("csrf:" +
  ficha)` en hexadecimal.
- Los mensajes son los literales de `seguridad.cuentas` (los mismos que la interfaz clásica) y el
  de la contraseña temporal. Ola 0a de la sesión 2b: la cuenta que debe cambiar su contraseña ya
  no recibe un 403 «cámbiela en la interfaz clásica» al entrar, sino una cookie restringida (la
  prueba de esa cookie y de `POST /v1/sesion/contrasena` está en `test_api_sesion_contrasena.py`);
  `GET/POST /v1/sesion` agregan `debe_cambiar_clave`, `acciones` y `modo_entrega`.
- La expiración se provoca moviendo 31 minutos hacia atrás la `ultima_actividad` de la fila de la
  sesión (nunca `sleep`); la cota exacta (29:59 sigue, 30:00 expira) ya la prueba
  `test_sesiones.py`.

Las cuentas se crean una vez por módulo en una `instalacion.db` migrada que cada prueba copia.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from api import sesion_web
from api.main import app, manejar_http_exception
from api.proteccion import MENSAJE_SIN_CLAVE, exigir_clave_api
from api.rutas import libros
from api.rutas import sesion as rutas_sesion
from operacion import config, registro
from operacion.base_datos import Destino, preparar_base
from operacion.instalacion import sesion_de_instalacion
from seguridad import cuentas, sesiones
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import EventoAcceso, Sesion, Usuario
from seguridad.permisos import Accion
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona

NUEVA = "otra contrasena larga de prueba"
ORIGEN = ANFITRION  # http://127.0.0.1:8000: el mismo anfitrión que el `Host` del cliente
COOKIE = "silice_sesion"
CSRF = "X-Silice-CSRF"
MENSAJE_CAMBIAR = "Su contraseña es temporal: elija una propia antes de seguir."  # ola 0a
MENSAJE_PERMISO = "Su cuenta no tiene permiso para esta acción."
#: Lo que `/v1/sesion` informa de una cuenta de arma sin contraseña temporal (ola 0a).
_ESTADO_DE_ARMA = {
    "debe_cambiar_clave": False,
    "acciones": [
        "editar_hoja",
        "convertir_y_reajustar",
        "control_de_obra",
        "decidir_recuperacion",
        "entregar_paquete",
        "operar_arenera",
        "leer_proyecto",
        "cambiar_caso",
    ],
    "modo_entrega": False,
}
#: Login -> contraseña vigente. `tomas` conserva la temporal: debe cambiarla.
CUENTAS = {"admin": CONTRASENA, "ana": NUEVA, "rita": NUEVA, "tomas": CONTRASENA}


# --- Ayudas ---------------------------------------------------------------------------------


def _csrf(ficha: str) -> str:
    return hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def _instalacion_con_cuentas(tmp_path_factory) -> Path:
    """`instalacion.db` migrada con cuatro cuentas por el camino real: admin (administrador),
    ana (arma), rita (revisa) y tomas (arma, con la contraseña temporal sin cambiar)."""
    carpeta = tmp_path_factory.mktemp("plantilla_sesion_web")
    plantilla = carpeta / "instalacion.db"
    preparar_base(plantilla, Destino.INSTALACION)
    motor = crear_motor(plantilla)
    sesion = abrir_sesion(motor)
    try:
        admin = administrador(sesion, carpeta)
        for login, roles in (("ana", ("arma",)), ("rita", ("revisa",))):
            usuario = persona(sesion, admin, login, roles)
            cuentas.cambiar_contrasena(sesion, usuario.id, CONTRASENA, NUEVA, AHORA)
        persona(sesion, admin, "tomas", ("arma",))
        for usuario in sesion.scalars(select(Usuario)):
            sesiones.cerrar_todas(sesion, usuario.id, "plantilla")
        sesion.commit()
    finally:
        sesion.close()
        motor.dispose()  # cierra el WAL: la copia lleva todo
    return plantilla


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_con_cuentas: Path) -> Iterator[None]:
    destino = config.ruta_instalacion()
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_instalacion_con_cuentas, destino)
    cuentas.FRENO.reiniciar()  # el freno global es del proceso: ninguna prueba hereda fallos
    yield
    cuentas.FRENO.reiniciar()


def _cliente(aplicacion: FastAPI = app, ip: str = IP_LOCAL[0]) -> TestClient:
    return TestClient(
        aplicacion, base_url=ANFITRION, client=(ip, 50000), raise_server_exceptions=False
    )


def _entrar(cliente: TestClient, login: str, contrasena: str | None = None, **extra):
    clave = CUENTAS[login] if contrasena is None else contrasena
    return cliente.post("/v1/sesion", json={"login": login, "contrasena": clave}, **extra)


def _ficha(respuesta) -> str:
    ficha = respuesta.cookies.get(COOKIE)
    assert ficha, respuesta.headers.get("set-cookie")
    return ficha


def _con_cuenta(login: str, aplicacion: FastAPI = app) -> tuple[TestClient, str]:
    """Un cliente ya dentro con `login` (la cookie queda en su tarro) y su ficha."""
    cliente = _cliente(aplicacion)
    respuesta = _entrar(cliente, login)
    assert respuesta.status_code == 200, respuesta.text
    return cliente, _ficha(respuesta)


def _protegida(ficha: str, origen: str | None = ORIGEN) -> dict[str, str]:
    cabeceras = {CSRF: _csrf(ficha)}
    if origen is not None:
        cabeceras["Origin"] = origen
    return cabeceras


def _fila(ficha: str) -> Sesion:
    with sesion_de_instalacion() as sesion:
        return sesion.get(Sesion, sesiones.huella_de(ficha))


def _app_de_prueba() -> FastAPI:
    """El router de sesión real, una sonda y el router real de libros, los dos con
    `exigir_clave_o_sesion(Accion.LEER_PROYECTO)` (RS2-5), y el formato `{"detalle": ...}`."""
    prueba = FastAPI()
    prueba.add_exception_handler(HTTPException, manejar_http_exception)
    prueba.include_router(rutas_sesion.router)
    lectura = [Depends(sesion_web.exigir_clave_o_sesion(Accion.LEER_PROYECTO))]

    @prueba.get("/sonda", dependencies=lectura)
    def leer() -> dict[str, bool]:
        return {"ok": True}

    @prueba.post("/sonda", dependencies=lectura)
    def escribir() -> dict[str, bool]:
        return {"ok": True}

    prueba.include_router(libros.router, dependencies=lectura)
    return prueba


PRUEBA = _app_de_prueba()


def _app_de_referencia() -> FastAPI:
    """Las rutas de libros como estaban antes de la 2.3b: solo `exigir_clave_api` (`CON_CLAVE`)."""
    referencia = FastAPI()
    referencia.add_exception_handler(HTTPException, manejar_http_exception)
    referencia.include_router(libros.router, dependencies=[Depends(exigir_clave_api)])
    return referencia


REFERENCIA = _app_de_referencia()


def _libro_con_extension_mala(cliente: TestClient, **extra):
    """Una petición a `/v1/libros/auditoria` que la ruta rechaza con 415: si llega a 415, pasó
    la dependencia de acceso (que corre antes que la validación de la entrada)."""
    return cliente.post(
        "/v1/libros/auditoria",
        files={"libro": ("libro.txt", b"no es un libro")},
        data={"fecha_devolucion": "2026-10-13"},
        **extra,
    )


# --- POST /v1/sesion ------------------------------------------------------------------------


def test_entrar_pone_cookie_httponly_samesite_strict_y_devuelve_csrf() -> None:
    respuesta = _entrar(_cliente(), "ana")
    assert respuesta.status_code == 200, respuesta.text
    ficha = _ficha(respuesta)
    assert respuesta.json() == {
        "login": "ana",
        "nombre": "Ana",
        "roles": ["arma"],
        "csrf": _csrf(ficha),
        **_ESTADO_DE_ARMA,
    }
    galleta = respuesta.headers["set-cookie"]
    atributos = {a.strip().split("=", 1)[0].lower(): a.strip() for a in galleta.split(";")[1:]}
    assert galleta.startswith(f"{COOKIE}={ficha};")
    assert "httponly" in atributos
    assert atributos["samesite"].lower() == "samesite=strict"
    assert atributos["path"] == "Path=/"
    assert not {"max-age", "expires", "secure", "domain"} & atributos.keys()  # RS2-6
    assert ficha not in respuesta.text


def test_contrasena_mala_da_401_sin_cookie() -> None:
    respuesta = _entrar(_cliente(), "ana", "no es la contrasena de ana")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": cuentas.MENSAJE_FALLO}
    assert "set-cookie" not in respuesta.headers


def test_usuario_inexistente_da_el_mismo_401_que_la_contrasena_mala() -> None:
    inexistente = _entrar(_cliente(), "nadie", NUEVA)
    mala = _entrar(_cliente(), "ana", "no es la contrasena de ana")
    assert (inexistente.status_code, inexistente.json()) == (mala.status_code, mala.json())
    assert "set-cookie" not in inexistente.headers


def test_cinco_fallos_bloquean_con_423() -> None:
    cliente = _cliente()
    codigos = [_entrar(cliente, "ana", f"mala numero {i} de ana").status_code for i in range(5)]
    assert codigos == [401, 401, 401, 401, 423]
    bloqueada = _entrar(cliente, "ana")  # ni la buena entra mientras dura el bloqueo
    assert bloqueada.status_code == 423
    assert bloqueada.json() == {"detalle": cuentas.MENSAJE_BLOQUEO}
    assert "set-cookie" not in bloqueada.headers


def test_el_acceso_registra_la_ip_del_cliente() -> None:
    cliente = _cliente(ip="192.168.1.30")
    assert _entrar(cliente, "ana", "no es la contrasena de ana").status_code == 401
    assert _entrar(cliente, "ana").status_code == 200
    with sesion_de_instalacion() as sesion:
        filas = sesion.execute(
            select(EventoAcceso.tipo, EventoAcceso.ip_cliente)
            .where(EventoAcceso.login_intentado == "ana")
            .where(EventoAcceso.tipo.in_(("fallo", "entrada")))
            .order_by(EventoAcceso.id)
        ).all()
    assert [tuple(f) for f in filas] == [("fallo", "192.168.1.30"), ("entrada", "192.168.1.30")]


def test_cuenta_que_debe_cambiar_clave_entra_con_la_cookie_restringida() -> None:
    """Ola 0a (sesión 2b): antes era 403 sin cookie («cámbiela en la interfaz clásica»); ahora
    entra con una ficha cuya cuenta debe cambiar la contraseña, y nada más le sirve."""
    respuesta = _entrar(_cliente(), "tomas")
    assert respuesta.status_code == 200
    ficha = _ficha(respuesta)
    assert respuesta.json()["debe_cambiar_clave"] is True
    assert respuesta.json()["acciones"] == []
    with sesion_de_instalacion() as sesion:
        tomas = sesion.scalar(select(Usuario).where(Usuario.login == "tomas"))
        abiertas = sesion.scalars(
            select(Sesion.huella_ficha).where(
                Sesion.usuario_id == tomas.id, Sesion.cerrada.is_(False)
            )
        ).all()
    assert abiertas == [sesiones.huella_de(ficha)]


def test_entrar_desde_otro_origen_da_403_sin_cookie() -> None:
    """Contra el CSRF de acceso: un `Origin` presente y ajeno no abre sesión."""
    respuesta = _entrar(_cliente(), "ana", headers={"Origin": "http://atacante.ejemplo"})
    assert respuesta.status_code == 403
    assert "set-cookie" not in respuesta.headers


def test_entrar_con_el_origin_propio_pasa() -> None:
    """Un navegador siempre manda `Origin` en un POST: el de la instalación entra."""
    respuesta = _entrar(_cliente(), "ana", headers={"Origin": ORIGEN})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["csrf"] == _csrf(_ficha(respuesta))


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"login": "ana", "contrasena": "s" * 138},  # pasa del máximo de 128
        {"login": "ana", "contrasena": 12345},  # no es texto
        {"login": "ana"},  # falta la contraseña
        {"login": ["ana-en-lista"], "contrasena": "secreto-que-no-vuelve"},
    ],
    ids=["larga", "numero", "sin-contrasena", "login-lista"],
)
def test_un_cuerpo_invalido_da_422_sin_repetir_lo_enviado(cuerpo: dict) -> None:
    respuesta = _cliente().post("/v1/sesion", json=cuerpo)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": rutas_sesion.MENSAJE_CUERPO_INVALIDO}
    for valor in cuerpo.values():
        texto = valor[0] if isinstance(valor, list) else str(valor)
        assert texto not in respuesta.text
    assert "set-cookie" not in respuesta.headers


def test_el_422_de_las_demas_rutas_no_cambia() -> None:
    """El manejador acotado a `/v1/sesion` no toca el formato de FastAPI del resto de la API."""
    clave = crear_clave_de_prueba()
    respuesta = _cliente().post("/v1/libros/auditoria", headers={CABECERA: clave})
    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()  # el de FastAPI, con su lista de errores


class _FrenoFijo:
    """Un freno global que siempre pide esperar `segundos` (sin fallos reales)."""

    def __init__(self, segundos: float) -> None:
        self.segundos = segundos

    def espera(self, _ahora) -> float:
        return self.segundos

    def registrar_fallo(self, _ahora) -> None:  # pragma: no cover - no llega a contar
        raise AssertionError("el intento frenado no se verifica")

    def reiniciar(self) -> None:
        pass


@pytest.fixture
def _sin_dormir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ningún `time.sleep` real: si `autenticar` llegara a dormir, la prueba falla."""

    def prohibido(segundos: float) -> None:
        raise AssertionError(f"la API durmió {segundos} s dentro de su hilo")

    monkeypatch.setattr(cuentas.time, "sleep", prohibido)


def _intentos(login: str) -> int:
    with sesion_de_instalacion() as sesion:
        fila = sesion.get(cuentas.IntentoAcceso, login)
        return 0 if fila is None else fila.fallos_seguidos


@pytest.mark.usefixtures("_sin_dormir")
def test_el_freno_global_responde_429_con_retry_after_sin_dormir() -> None:
    """RS2-11: 21 fallos del proceso en la ventana piden 2 s (2**1); la API no duerme."""
    ahora = sesion_web.ahora()
    for _ in range(cuentas.FRENO_FALLOS + 1):
        cuentas.FRENO.registrar_fallo(ahora)
    respuesta = _entrar(_cliente(), "ana")
    assert respuesta.status_code == 429
    assert respuesta.headers["retry-after"] == "2"
    assert respuesta.json() == {"detalle": rutas_sesion.MENSAJE_FRENO}
    assert "set-cookie" not in respuesta.headers
    assert _intentos("ana") == 0  # frenado antes de verificar: no es un intento de contraseña


@pytest.mark.usefixtures("_sin_dormir")
def test_el_retry_after_redondea_hacia_arriba(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cuentas, "FRENO", _FrenoFijo(1.2))
    respuesta = _entrar(_cliente(), "ana")
    assert (respuesta.status_code, respuesta.headers["retry-after"]) == (429, "2")


@pytest.mark.usefixtures("_sin_dormir")
def test_sin_freno_el_acceso_cuenta_el_fallo_como_siempre() -> None:
    for _ in range(cuentas.FRENO_FALLOS - 1):  # 19: todavía sin espera
        cuentas.FRENO.registrar_fallo(sesion_web.ahora())
    assert _entrar(_cliente(), "ana", "no es la contrasena de ana").status_code == 401
    assert _intentos("ana") == 1
    assert _entrar(_cliente(), "ana").status_code == 429  # el fallo 20 activa el freno


def test_volver_a_entrar_cierra_la_ficha_anterior() -> None:
    cliente, vieja = _con_cuenta("ana")
    respuesta = _entrar(cliente, "ana")  # el tarro manda la cookie vieja
    assert respuesta.status_code == 200
    nueva = _ficha(respuesta)
    assert nueva != vieja
    fila = _fila(vieja)
    assert (fila.cerrada, fila.motivo_cierre) == (True, "salida")
    otro = _cliente()
    otro.cookies.set(COOKIE, vieja)
    assert otro.get("/v1/sesion").status_code == 401
    assert cliente.get("/v1/sesion").json()["csrf"] == _csrf(nueva)


# --- GET /v1/sesion -------------------------------------------------------------------------


def test_get_sesion_sin_cookie_da_401() -> None:
    respuesta = _cliente().get("/v1/sesion")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": sesion_web.MENSAJE_SIN_SESION}


def test_get_sesion_con_cookie_da_el_usuario() -> None:
    cliente, ficha = _con_cuenta("rita")
    respuesta = cliente.get("/v1/sesion")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "login": "rita",
        "nombre": "Rita",
        "roles": ["revisa"],
        "csrf": _csrf(ficha),
        "debe_cambiar_clave": False,
        "acciones": ["leer_proyecto", "revisar_paquete"],
        "modo_entrega": False,
        }
    assert ficha not in respuesta.text


def test_get_sesion_con_una_ficha_inventada_da_401() -> None:
    cliente = _cliente()
    cliente.cookies.set(COOKIE, "ficha-inventada-por-alguien")
    assert cliente.get("/v1/sesion").status_code == 401


def test_sesion_expirada_por_inactividad_da_401() -> None:
    cliente, ficha = _con_cuenta("ana")
    with sesion_de_instalacion() as sesion:
        fila = sesion.get(Sesion, sesiones.huella_de(ficha))
        fila.ultima_actividad -= timedelta(minutes=31)
        fila.creada -= timedelta(minutes=31)
        sesion.commit()
    respuesta = cliente.get("/v1/sesion")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": sesion_web.MENSAJE_SIN_SESION}
    galleta = respuesta.headers["set-cookie"].lower()
    assert galleta.startswith(f"{COOKIE}=") and "max-age=0" in galleta  # borra la que no sirve
    fila = _fila(ficha)
    assert (fila.cerrada, fila.motivo_cierre) == (True, "inactividad")


# --- DELETE /v1/sesion ----------------------------------------------------------------------


def test_salir_sin_csrf_da_403() -> None:
    cliente, ficha = _con_cuenta("ana")
    respuesta = cliente.delete("/v1/sesion", headers={"Origin": ORIGEN})
    assert respuesta.status_code == 403
    assert _fila(ficha).cerrada is False
    assert cliente.get("/v1/sesion").status_code == 200


def test_salir_desde_otro_origen_da_403() -> None:
    cliente, ficha = _con_cuenta("ana")
    respuesta = cliente.delete("/v1/sesion", headers=_protegida(ficha, "http://atacante.ejemplo"))
    assert respuesta.status_code == 403
    assert _fila(ficha).cerrada is False


def test_salir_cierra_la_ficha_y_borra_la_cookie() -> None:
    cliente, ficha = _con_cuenta("ana")
    respuesta = cliente.delete("/v1/sesion", headers=_protegida(ficha))
    assert respuesta.status_code == 204
    galleta = respuesta.headers["set-cookie"].lower()
    assert galleta.startswith(f'{COOKIE}="";') or galleta.startswith(f"{COOKIE}=;")
    assert "max-age=0" in galleta and "path=/" in galleta
    fila = _fila(ficha)
    assert (fila.cerrada, fila.motivo_cierre) == (True, "salida")
    otro = _cliente()
    otro.cookies.set(COOKIE, ficha)  # la ficha vieja ya no sirve aunque alguien la guarde
    assert otro.get("/v1/sesion").status_code == 401


def test_salir_sin_sesion_da_401() -> None:
    assert _cliente().delete("/v1/sesion", headers={"Origin": ORIGEN}).status_code == 401


# --- exigir_clave_o_sesion ------------------------------------------------------------------


def test_get_con_cookie_pasa_sin_csrf() -> None:
    cliente, _ = _con_cuenta("ana", PRUEBA)
    respuesta = cliente.get("/sonda")
    assert (respuesta.status_code, respuesta.json()) == (200, {"ok": True})


def test_post_sin_nada_da_401() -> None:
    respuesta = _cliente(PRUEBA).post("/sonda", headers={"Origin": ORIGEN})
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": sesion_web.MENSAJE_SIN_SESION}


def test_post_con_cookie_sin_csrf_da_403() -> None:
    cliente, _ = _con_cuenta("ana", PRUEBA)
    respuesta = cliente.post("/sonda", headers={"Origin": ORIGEN})
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": sesion_web.MENSAJE_CSRF}


def test_post_con_csrf_de_otra_ficha_da_403() -> None:
    cliente, _ = _con_cuenta("ana", PRUEBA)
    _, ajena = _con_cuenta("rita", PRUEBA)
    respuesta = cliente.post("/sonda", headers=_protegida(ajena))
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": sesion_web.MENSAJE_CSRF}


def test_post_con_csrf_no_ascii_da_403_y_no_500() -> None:
    cliente, _ = _con_cuenta("ana", PRUEBA)
    cabeceras = {CSRF: "ñ".encode("latin-1") * 64, "Origin": ORIGEN.encode("latin-1")}
    respuesta = cliente.post("/sonda", headers=cabeceras)
    assert respuesta.status_code == 403


def test_post_con_csrf_y_origin_ajeno_da_403() -> None:
    cliente, ficha = _con_cuenta("ana", PRUEBA)
    for origen in (
        "http://atacante.ejemplo",
        "http://127.0.0.1:9999",
        "https://127.0.0.1:8000",
        "null",
    ):
        respuesta = cliente.post("/sonda", headers=_protegida(ficha, origen))
        assert respuesta.status_code == 403, origen
        assert respuesta.json() == {"detalle": sesion_web.MENSAJE_ORIGEN}


def test_post_con_csrf_sin_origin_da_403() -> None:
    cliente, ficha = _con_cuenta("ana", PRUEBA)
    respuesta = cliente.post("/sonda", headers=_protegida(ficha, origen=None))
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": sesion_web.MENSAJE_ORIGEN}


def test_post_con_cookie_y_csrf_pasa() -> None:
    cliente, ficha = _con_cuenta("ana", PRUEBA)
    respuesta = cliente.post("/sonda", headers=_protegida(ficha))
    assert (respuesta.status_code, respuesta.json()) == (200, {"ok": True})


def test_sesion_expirada_da_401_en_una_ruta_protegida() -> None:
    cliente, ficha = _con_cuenta("ana", PRUEBA)
    with sesion_de_instalacion() as sesion:
        fila = sesion.get(Sesion, sesiones.huella_de(ficha))
        fila.ultima_actividad -= timedelta(minutes=31)
        sesion.commit()
    assert cliente.post("/sonda", headers=_protegida(ficha)).status_code == 401


def test_cuenta_obligada_a_cambiar_clave_tras_entrar_da_403() -> None:
    cliente, _ = _con_cuenta("ana", PRUEBA)
    with sesion_de_instalacion() as sesion:
        ana = sesion.scalar(select(Usuario).where(Usuario.login == "ana"))
        ana.debe_cambiar_clave = True
        sesion.commit()
    respuesta = cliente.get("/sonda")
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_CAMBIAR}


def test_rol_administrador_solo_da_403_en_libros() -> None:
    """RS2-5: `LEER_PROYECTO` es de arma y revisa; el administrador solo no audita libros."""
    cliente, ficha = _con_cuenta("admin", PRUEBA)
    respuesta = _libro_con_extension_mala(cliente, headers=_protegida(ficha))
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_PERMISO}


@pytest.mark.parametrize("login", ["rita", "ana"])
def test_rol_revisa_pasa(login: str) -> None:
    """Revisa (y arma) llegan a la ruta: la extensión mala la rechaza la ruta misma con 415."""
    cliente, ficha = _con_cuenta(login, PRUEBA)
    respuesta = _libro_con_extension_mala(cliente, headers=_protegida(ficha))
    assert respuesta.status_code == 415, respuesta.text


def test_con_clave_de_api_las_rutas_de_libros_siguen_igual() -> None:
    """Con `X-Silice-Clave` (sin cookie) la aplicación real y la de prueba responden lo mismo que
    las rutas de antes con `CON_CLAVE` (la aplicación de referencia)."""
    clave = crear_clave_de_prueba()
    for cabeceras in ({CABECERA: clave}, {CABECERA: "AB12CD34.no-es-la-clave"}, {CABECERA: ""}):
        antes = _libro_con_extension_mala(_cliente(REFERENCIA), headers=cabeceras)
        for aplicacion in (PRUEBA, app):
            ahora = _libro_con_extension_mala(_cliente(aplicacion), headers=cabeceras)
            assert (ahora.status_code, ahora.json()) == (antes.status_code, antes.json())
    assert _libro_con_extension_mala(_cliente(PRUEBA), headers={CABECERA: clave}).status_code == 415
    sin_clave = _libro_con_extension_mala(_cliente(PRUEBA), headers={CABECERA: "x.y"})
    assert sin_clave.json() == {"detalle": MENSAJE_SIN_CLAVE}


def test_una_clave_de_api_mala_no_cae_a_la_cookie() -> None:
    """Quien manda la cabecera de la clave va por el camino de la clave, aunque tenga cookie."""
    cliente, ficha = _con_cuenta("ana", PRUEBA)
    respuesta = cliente.post("/sonda", headers={**_protegida(ficha), CABECERA: "x.y"})
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detalle": MENSAJE_SIN_CLAVE}


# --- Secretos -------------------------------------------------------------------------------


def test_la_ficha_no_aparece_en_respuestas_ni_registros() -> None:
    registro.configurar(config.carpeta_registros())
    try:
        cliente = _cliente()
        entrada = _entrar(cliente, "ana")
        ficha = _ficha(entrada)
        consulta = cliente.get("/v1/sesion")
        salida = cliente.delete("/v1/sesion", headers=_protegida(ficha))
        assert salida.status_code == 204
        logging.getLogger(registro.NOMBRE_LOGGER).info("fin de la prueba de la ficha")
    finally:
        logger = logging.getLogger(registro.NOMBRE_LOGGER)
        for manejador in list(logger.handlers):
            logger.removeHandler(manejador)
            manejador.close()
    for respuesta in (entrada, consulta, salida):
        assert ficha not in respuesta.text
    base = config.ruta_instalacion()
    for archivo in base.parent.glob(base.name + "*"):  # la base, su -wal y su -journal
        assert ficha.encode() not in archivo.read_bytes()
    with sesion_de_instalacion() as sesion:
        detalles = " ".join(sesion.scalars(select(EventoAcceso.detalle)))
    assert ficha not in detalles
    texto = (config.carpeta_registros() / "silice.log").read_text(encoding="utf-8")
    assert ficha not in texto


@pytest.mark.usefixtures("_sin_dormir")
def test_el_freno_global_no_guarda_lo_tecleado_que_no_es_un_usuario() -> None:
    """El evento `bloqueo` del 429 usa la misma clave que `autenticar`: marcador, no el texto."""
    pegada = "Mi Clave Pegada Por Error 2026!"
    ahora = sesion_web.ahora()
    for _ in range(cuentas.FRENO_FALLOS + 1):
        cuentas.FRENO.registrar_fallo(ahora)
    assert _entrar(_cliente(), pegada, "cualquiera").status_code == 429
    with sesion_de_instalacion() as sesion:
        filas = [
            f"{e.login_intentado}|{e.ip_cliente}|{e.tipo}|{e.detalle}"
            for e in sesion.scalars(select(EventoAcceso))
        ]
    assert any(f.startswith("(usuario no válido)|") and "|bloqueo|" in f for f in filas)
    assert not any("clave pegada" in f.casefold() for f in filas)
