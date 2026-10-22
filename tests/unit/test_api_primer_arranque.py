"""`GET /v1/primer-arranque` y `POST /v1/primer-arranque/reclamo` (BCP-1; diseño §3 y §10).

Rutas públicas, solo para el propio equipo. Se ejercen sobre `api.main.app` real con una
`instalacion.db` migrada y copiada en la carpeta de datos temporal de cada prueba (una plantilla
vacía y otra con cuentas, creadas una vez por módulo).

Oráculos a mano, ninguno sale del código bajo prueba:

- las claves del GET, los textos de error de `seguridad.cuentas` y los de la ruta se escriben aquí;
- las `acciones` de un administrador (y de uno que también arma) se listan literal desde la
  matriz de `seguridad/permisos.py`, en el orden de `Accion`;
- el CSRF se recalcula con `hashlib` (`sha256("csrf:" + ficha)`);
- 5 fallos bloquean 15 minutos y el freno global arranca en el fallo 20 con espera de 2**0 s.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api.main import app
from api.rutas import primer_arranque as ruta_pa
from operacion import config
from operacion.base_datos import Destino, preparar_base
from operacion.instalacion import cerrar_motores, sesion_de_instalacion
from seguridad import cuentas
from seguridad.modelo import CodigoInstalacion, EventoAcceso, IntentoAcceso, Sesion, Usuario
from tests.fixtures.claves_api import ANFITRION
from tests.fixtures.instalacion import CONTRASENA
from tests.fixtures.sesion_web import (
    COOKIE,
    copiar_instalacion,
    ficha_de,
    plantilla_con_cuentas,
)

URL_ESTADO = "/v1/primer-arranque"
URL_RECLAMO = "/v1/primer-arranque/reclamo"
ORIGEN = ANFITRION
OTRA_IP = "192.168.1.50"
T0 = datetime(2026, 11, 10, 9, 0, 0)

MENSAJE_REMOTO = (
    "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."
)
MENSAJE_ORIGEN = "La petición no viene de la interfaz de esta instalación."
MENSAJE_CODIGO = "El código de instalación no es válido o ya se usó."
MENSAJE_BLOQUEO = (
    "Demasiados intentos fallidos. Espere 15 minutos o pida al administrador que desbloquee "
    "la cuenta."
)
MENSAJE_FRENO = (
    "Demasiados intentos fallidos en este equipo. Espere unos segundos y vuelva a probar."
)
MENSAJE_CUERPO = (
    "Escriba el código, el usuario, el nombre y la contraseña como texto (la contraseña admite "
    "hasta 128 caracteres)."
)
MENSAJE_USUARIO = "El usuario son 3 a 40 caracteres: letras, números, punto o guion."
MENSAJE_CORTA = "La contraseña debe tener al menos 10 caracteres."
MENSAJE_IGUAL = "La contraseña no puede ser igual al usuario."
MENSAJE_COMUN = "Esa contraseña es demasiado común; elija otra."
MENSAJE_OCUPADA = "La base está ocupada; reintente en unos segundos."
CLAVES_DEL_ESTADO = {"sin_cuentas", "archivo_presente", "modo", "politica"}
CLAVES_DE_SESION = {
    "login",
    "nombre",
    "roles",
    "csrf",
    "debe_cambiar_clave",
    "acciones",
    "modo_entrega",
}
#: Matriz de `seguridad/permisos.py`, en el orden de `Accion`, de cada combinación de roles.
ACCIONES_ADMINISTRADOR = [
    "operar_arenera",
    "cambiar_caso",
    "administrar_cuentas",
    "administrar_empresa",
    "administrar_precios",
    "administrar_red_y_api",
    "cambiar_carpeta_de_datos",
]
ACCIONES_ADMINISTRADOR_Y_ARMA = [
    "editar_hoja",
    "convertir_y_reajustar",
    "control_de_obra",
    "decidir_recuperacion",
    "entregar_paquete",
    "operar_arenera",
    "leer_proyecto",
    "cambiar_caso",
    "administrar_cuentas",
    "administrar_empresa",
    "administrar_precios",
    "administrar_red_y_api",
    "cambiar_carpeta_de_datos",
]


# --- infraestructura ----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _plantilla_vacia(tmp_path_factory) -> Path:
    ruta = tmp_path_factory.mktemp("pa_vacia") / "instalacion.db"
    preparar_base(ruta, Destino.INSTALACION)
    return ruta


@pytest.fixture(scope="module")
def _plantilla_con_cuentas(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("pa_cuentas"))


@pytest.fixture
def vacia(_plantilla_vacia: Path) -> Iterator[None]:
    """Una instalación sin cuentas en la carpeta de datos de la prueba."""
    copiar_instalacion(_plantilla_vacia)
    yield
    cerrar_motores()


@pytest.fixture
def con_cuentas(_plantilla_con_cuentas: Path) -> Iterator[None]:
    """admin, ana (arma), rita (revisa) y tomas (arma, contraseña temporal)."""
    copiar_instalacion(_plantilla_con_cuentas)
    yield
    cerrar_motores()


def navegador(ip: str = "127.0.0.1", base_url: str = ANFITRION) -> TestClient:
    return TestClient(app, base_url=base_url, client=(ip, 50000), raise_server_exceptions=False)


def emitir(motivo: str = "primera vez", cuando: datetime | None = None) -> str:
    """Un código nuevo directo en la base de la prueba; devuelve el texto a mano."""
    with sesion_de_instalacion() as sesion:
        if motivo == "primera vez":
            return cuentas.emitir_codigo(sesion, config.carpeta_datos(), cuando or datetime.now())
        return cuentas.emitir_codigo_de_restablecimiento(
            sesion, config.carpeta_datos(), cuando or datetime.now()
        )


def cuerpo(codigo: str, usuario: str = "dueno", **extra) -> dict:
    datos = {
        "codigo": codigo,
        "usuario": usuario,
        "nombre": "Dueña Demo",
        "contrasena": CONTRASENA,
        "tambien_arma": False,
    }
    datos.update(extra)
    return datos


def reclamar(nav: TestClient, datos: dict, origen: str | None = ORIGEN, **cabeceras):
    if origen is not None:
        cabeceras["Origin"] = origen
    return nav.post(URL_RECLAMO, json=datos, headers=cabeceras)


def contar(modelo) -> int:
    with sesion_de_instalacion() as sesion:
        return sesion.scalar(select(func.count()).select_from(modelo))


@pytest.fixture
def reloj(monkeypatch: pytest.MonkeyPatch) -> dict[str, datetime]:
    """El reloj de la ruta, movible: `reloj["ahora"] = ...`."""
    marca = {"ahora": T0}
    monkeypatch.setattr(ruta_pa, "ahora", lambda: marca["ahora"])
    return marca


# --- GET /v1/primer-arranque (B2) ---------------------------------------------------------------


@pytest.mark.usefixtures("vacia")
def test_el_estado_dice_solo_cuatro_cosas_y_no_se_guarda(monkeypatch) -> None:
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: False)
    respuesta = navegador().get(URL_ESTADO)
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "sin_cuentas": True,
        "archivo_presente": False,
        "modo": "desarrollo",
        "politica": {"minimo": 10, "maximo": 128},
    }
    assert set(respuesta.json()) == CLAVES_DEL_ESTADO
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.usefixtures("vacia")
def test_el_get_nunca_escribe_el_codigo() -> None:
    navegador().get(URL_ESTADO)
    assert not (config.carpeta_datos() / "codigo_instalacion.txt").exists()
    assert contar(CodigoInstalacion) == 0  # un GET con efecto sería una trampa


@pytest.mark.usefixtures("vacia")
def test_el_modo_producto(monkeypatch) -> None:
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
    assert navegador().get(URL_ESTADO).json()["modo"] == "producto"


@pytest.mark.usefixtures("vacia")
def test_el_estado_sigue_al_archivo_y_a_las_cuentas() -> None:
    nav = navegador()
    codigo = emitir()
    assert nav.get(URL_ESTADO).json()["archivo_presente"] is True
    assert nav.get(URL_ESTADO).json()["sin_cuentas"] is True
    assert reclamar(nav, cuerpo(codigo)).status_code == 201
    despues = navegador().get(URL_ESTADO).json()  # sin la cookie, como desde otra pestaña
    assert despues["sin_cuentas"] is False and despues["archivo_presente"] is False


@pytest.mark.usefixtures("vacia")
def test_el_estado_no_trae_rutas_ni_el_codigo_ni_la_huella() -> None:
    codigo = emitir()
    huella = hashlib.sha256(codigo.encode("ascii")).hexdigest()
    texto = navegador().get(URL_ESTADO).text
    assert codigo not in texto and huella not in texto
    assert str(config.carpeta_datos()) not in texto and "\\" not in texto and ":/" not in texto


@pytest.mark.usefixtures("vacia")
def test_el_estado_desde_otra_ip_es_403_y_sin_cache() -> None:
    respuesta = navegador(OTRA_IP).get(URL_ESTADO)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detalle": MENSAJE_REMOTO}
    assert respuesta.headers["cache-control"] == "no-store"


# --- POST: el reclamo feliz (B3, B4, B9) --------------------------------------------------------


@pytest.mark.usefixtures("vacia")
def test_el_reclamo_crea_el_primer_administrador_y_abre_la_sesion() -> None:
    nav = navegador()
    codigo = emitir()
    respuesta = reclamar(nav, cuerpo(codigo, "dueno"))
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert set(datos) == CLAVES_DE_SESION
    assert (datos["login"], datos["nombre"], datos["roles"]) == (
        "dueno",
        "Dueña Demo",
        ["administrador"],
    )
    assert datos["debe_cambiar_clave"] is False and datos["modo_entrega"] is False
    assert datos["acciones"] == ACCIONES_ADMINISTRADOR
    ficha = ficha_de(respuesta)
    assert datos["csrf"] == hashlib.sha256(("csrf:" + ficha).encode("utf-8")).hexdigest()
    assert respuesta.headers["cache-control"] == "no-store"
    cookie = respuesta.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
    # el archivo se borró, la huella quedó usada y hay un evento de alta sin el código
    assert not (config.carpeta_datos() / "codigo_instalacion.txt").exists()
    with sesion_de_instalacion() as sesion:
        [fila] = sesion.scalars(select(CodigoInstalacion)).all()
        assert fila.usado is not None
        altas = sesion.scalars(select(EventoAcceso).where(EventoAcceso.tipo == "alta")).all()
        assert [a.login_intentado for a in altas] == ["dueno"]
    # la cookie sirve: la sesión vigente es la de la cuenta nueva
    consulta = nav.get("/v1/sesion")
    assert consulta.status_code == 200 and consulta.json()["login"] == "dueno"


@pytest.mark.usefixtures("vacia")
def test_tambien_arma_da_los_dos_roles_y_las_acciones_de_ambos() -> None:
    respuesta = reclamar(navegador(), cuerpo(emitir(), tambien_arma=True))
    assert respuesta.status_code == 201
    assert respuesta.json()["roles"] == ["arma", "administrador"]
    assert respuesta.json()["acciones"] == ACCIONES_ADMINISTRADOR_Y_ARMA


@pytest.mark.usefixtures("vacia")
@pytest.mark.parametrize("variante", ["minusculas", "sin guiones", "con espacios"])
def test_el_codigo_mal_escrito_se_acepta(variante: str) -> None:
    codigo = emitir()
    con_guiones = "-".join(codigo[i : i + 4] for i in range(0, 20, 4))
    escrito = {
        "minusculas": con_guiones.lower(),
        "sin guiones": codigo,
        "con espacios": "  " + con_guiones.replace("-", " ") + " ",
    }[variante]
    assert reclamar(navegador(), cuerpo(escrito)).status_code == 201


@pytest.mark.usefixtures("vacia")
def test_un_codigo_con_un_caracter_cambiado_es_401() -> None:
    codigo = emitir()
    cambiado = ("B" if codigo[0] != "B" else "C") + codigo[1:]
    respuesta = reclamar(navegador(), cuerpo(cambiado))
    assert respuesta.status_code == 401 and respuesta.json() == {"detalle": MENSAJE_CODIGO}
    assert contar(Usuario) == 0


@pytest.mark.usefixtures("vacia")
def test_un_codigo_ya_usado_es_401_igual() -> None:
    codigo = emitir()
    assert reclamar(navegador(), cuerpo(codigo, "uno")).status_code == 201
    otra = reclamar(navegador(), cuerpo(codigo, "dos"))
    assert otra.status_code == 401 and otra.json() == {"detalle": MENSAJE_CODIGO}
    assert contar(Usuario) == 1


@pytest.mark.usefixtures("con_cuentas")
def test_con_cuentas_el_codigo_de_la_primera_vez_no_sirve_y_responde_lo_mismo() -> None:
    tardio = emitir()
    respuesta = reclamar(navegador(), cuerpo(tardio, "nuevo"))
    assert respuesta.status_code == 401 and respuesta.json() == {"detalle": MENSAJE_CODIGO}
    assert reclamar(navegador(), cuerpo("A" * 20, "nuevo")).json() == respuesta.json()
    with sesion_de_instalacion() as sesion:
        assert sesion.scalar(select(Usuario).where(Usuario.login == "nuevo")) is None


# --- restablecimiento con cuentas (B9, B10) -----------------------------------------------------


@pytest.mark.usefixtures("con_cuentas")
def test_el_restablecimiento_devuelve_el_acceso_y_promueve_sin_tocar_a_las_demas(reloj) -> None:
    rescate = emitir("restablecimiento", T0)
    viejo = navegador()
    assert (
        viejo.post(
            "/v1/sesion", json={"login": "ana", "contrasena": "otra contrasena larga de prueba"}
        ).status_code
        == 200
    )
    respuesta = reclamar(navegador(), cuerpo(rescate, "ana", contrasena="una clave nueva y larga"))
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["roles"] == ["arma", "administrador"]  # ana era `arma`
    assert viejo.get("/v1/sesion").status_code == 401  # sus fichas anteriores se cerraron
    with sesion_de_instalacion() as sesion:
        rita = sesion.scalar(select(Usuario).where(Usuario.login == "rita"))
        assert rita.roles == "revisa"  # las demás cuentas no cambian
        promovidas = sesion.scalars(
            select(EventoAcceso).where(EventoAcceso.tipo == "cambio de roles")
        ).all()
        assert [e.login_intentado for e in promovidas if "promovida" in e.detalle] == ["ana"]
    # la contraseña nueva entra por /v1/sesion
    nuevo = navegador()
    assert (
        nuevo.post(
            "/v1/sesion", json={"login": "ana", "contrasena": "una clave nueva y larga"}
        ).status_code
        == 200
    )


@pytest.mark.usefixtures("con_cuentas")
def test_una_cookie_anterior_del_navegador_se_cierra_y_se_olvida_su_caso(
    reloj, monkeypatch
) -> None:
    olvidados: list[str] = []
    monkeypatch.setattr(ruta_pa.caso_web, "olvidar", olvidados.append)
    nav = navegador()
    primera = nav.post("/v1/sesion", json={"login": "admin", "contrasena": CONTRASENA})
    ficha_vieja = ficha_de(primera)
    rescate = emitir("restablecimiento", T0)
    nueva = reclamar(nav, cuerpo(rescate, "admin", contrasena="otra clave larga y nueva"))
    assert nueva.status_code == 201
    assert ficha_de(nueva) != ficha_vieja
    assert hashlib.sha256(ficha_vieja.encode("utf-8")).hexdigest() in olvidados
    with sesion_de_instalacion() as sesion:
        cerradas = sesion.scalars(select(Sesion).where(Sesion.cerrada.is_(True))).all()
        assert cerradas  # la anterior ya no vale
    ajena = navegador().get("/v1/sesion", headers={"Cookie": f"{COOKIE}={ficha_vieja}"})
    assert ajena.status_code == 401


@pytest.mark.usefixtures("con_cuentas")
@pytest.mark.parametrize(
    ("pasado", "esperado"),
    [
        (timedelta(hours=23, minutes=59, seconds=59), 201),
        (timedelta(hours=24), 401),
        (timedelta(days=3), 401),
    ],
)
def test_el_codigo_de_restablecimiento_caduca_a_las_24_horas(reloj, pasado, esperado) -> None:
    rescate = emitir("restablecimiento", T0)
    reloj["ahora"] = T0 + pasado
    respuesta = reclamar(
        navegador(), cuerpo(rescate, "admin", contrasena="una clave nueva y larga")
    )
    assert respuesta.status_code == esperado, respuesta.text
    if esperado == 401:
        assert respuesta.json() == {"detalle": MENSAJE_CODIGO}


@pytest.mark.usefixtures("con_cuentas")
def test_emitir_otro_restablecimiento_invalida_el_anterior(reloj) -> None:
    primero = emitir("restablecimiento", T0)
    segundo = emitir("restablecimiento", T0 + timedelta(minutes=1))
    assert reclamar(navegador(), cuerpo(primero, "admin")).status_code == 401
    assert reclamar(navegador(), cuerpo(segundo, "admin")).status_code == 201


# --- forma antes que código (B5, B7, S4, S4b) ---------------------------------------------------


FORMAS_MALAS = [
    ("dueno", "123456789", MENSAJE_CORTA),
    ("dueno", "password123", MENSAJE_COMUN),
    ("administrador", "administrador", MENSAJE_IGUAL),
    ("AB", CONTRASENA, MENSAJE_USUARIO),
    ("con espacio", CONTRASENA, MENSAJE_USUARIO),
    ("", CONTRASENA, MENSAJE_USUARIO),
]


@pytest.mark.usefixtures("vacia")
@pytest.mark.parametrize(("usuario", "contrasena", "mensaje"), FORMAS_MALAS)
def test_la_forma_mala_da_422_con_el_texto_de_la_politica(usuario, contrasena, mensaje) -> None:
    codigo = emitir()
    respuesta = reclamar(navegador(), cuerpo(codigo, usuario, contrasena=contrasena))
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": mensaje}
    assert contrasena not in respuesta.text  # no se repite lo enviado


@pytest.mark.usefixtures("vacia")
@pytest.mark.parametrize(("usuario", "contrasena", "mensaje"), FORMAS_MALAS)
def test_con_la_forma_mala_el_codigo_bueno_y_el_malo_responden_igual(
    usuario, contrasena, mensaje
) -> None:
    bueno = emitir()
    con_bueno = reclamar(navegador(), cuerpo(bueno, usuario, contrasena=contrasena))
    con_malo = reclamar(navegador(), cuerpo("A" * 20, usuario, contrasena=contrasena))
    assert (con_bueno.status_code, con_bueno.json()) == (con_malo.status_code, con_malo.json())
    assert con_bueno.json() == {"detalle": mensaje}
    # y ninguno gastó un intento ni el código: sigue sirviendo
    with sesion_de_instalacion() as sesion:
        assert sesion.get(IntentoAcceso, cuentas.CLAVE_INTENTOS_CODIGO) is None
    assert reclamar(navegador(), cuerpo(bueno)).status_code == 201


@pytest.mark.usefixtures("vacia")
def test_una_contrasena_de_129_caracteres_es_422_fijo() -> None:
    respuesta = reclamar(navegador(), cuerpo(emitir(), contrasena="x" * 129))
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": MENSAJE_CUERPO}
    assert "x" * 129 not in respuesta.text


@pytest.mark.usefixtures("vacia")
@pytest.mark.parametrize(
    "malo",
    [
        {"contrasena": "y" * 500},
        {"contrasena": 12345678901234},
        {"usuario": None},
        {"nombre": ["lista"]},
        {"tambien_arma": "si"},
        {"codigo": "Z" * 65},
        {"nombre": "n" * 121},
    ],
    ids=[
        "500-caracteres",
        "numero",
        "usuario-nulo",
        "nombre-lista",
        "arma-texto",
        "codigo-65",
        "nombre-121",
    ],
)
def test_un_cuerpo_invalido_es_422_fijo_y_no_repite_lo_enviado(malo: dict) -> None:
    codigo = emitir()
    datos = cuerpo(codigo)
    datos.update(malo)
    respuesta = reclamar(navegador(), datos)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": MENSAJE_CUERPO}
    for valor in (codigo, CONTRASENA, "y" * 20, "Z" * 20, "n" * 20):
        assert valor not in respuesta.text


@pytest.mark.usefixtures("vacia")
def test_un_campo_obligatorio_que_falta_es_422_fijo() -> None:
    datos = cuerpo(emitir())
    del datos["contrasena"]
    respuesta = reclamar(navegador(), datos)
    assert respuesta.status_code == 422 and respuesta.json() == {"detalle": MENSAJE_CUERPO}


# --- Origin y equipo propio (B8, S8) ------------------------------------------------------------


@pytest.mark.usefixtures("vacia")
def test_sin_origin_el_reclamo_es_403() -> None:
    codigo = emitir()
    respuesta = reclamar(navegador(), cuerpo(codigo), origen=None)
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_ORIGEN}
    assert contar(Usuario) == 0
    assert reclamar(navegador(), cuerpo(codigo)).status_code == 201  # el código no se gastó


@pytest.mark.usefixtures("vacia")
@pytest.mark.parametrize("origen", ["http://evil.example", "http://127.0.0.1:9999", "null"])
def test_un_origin_ajeno_es_403(origen: str) -> None:
    respuesta = reclamar(navegador(), cuerpo(emitir()), origen=origen)
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_ORIGEN}
    assert contar(Usuario) == 0


@pytest.mark.usefixtures("vacia")
def test_un_host_no_permitido_no_llega_a_la_ruta() -> None:
    nav = navegador(base_url="http://evil.example")
    respuesta = nav.post(
        URL_RECLAMO, json=cuerpo(emitir()), headers={"Origin": "http://evil.example"}
    )
    assert respuesta.status_code in (400, 403)
    assert contar(Usuario) == 0


@pytest.mark.usefixtures("vacia")
def test_el_reclamo_desde_otra_ip_es_403() -> None:
    respuesta = reclamar(navegador(OTRA_IP), cuerpo(emitir()))
    assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_REMOTO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert contar(Usuario) == 0


@pytest.mark.usefixtures("vacia")
@pytest.mark.parametrize("ip", ["127.0.0.1", OTRA_IP], ids=["propio", "remoto"])
def test_la_comprobacion_de_origen_y_equipo_antecede_al_422(ip: str) -> None:
    """Un cuerpo inválido, sin cuerpo o con JSON roto nunca da 422 a quien no pasa la puerta."""
    nav = navegador(ip)
    sin_origin = {"content-type": "application/json"}
    for contenido in (b"{}", b"", b"{esto no es json", b'{"codigo": 7}'):
        respuesta = nav.post(URL_RECLAMO, content=contenido, headers=sin_origin)
        assert respuesta.status_code == 403, (contenido, respuesta.status_code, respuesta.text)
        assert respuesta.json() == {"detalle": MENSAJE_ORIGEN}
    if ip == OTRA_IP:
        propio = {**sin_origin, "Origin": ORIGEN}
        for contenido in (b"{}", b"{esto no es json"):
            respuesta = nav.post(URL_RECLAMO, content=contenido, headers=propio)
            assert respuesta.status_code == 403 and respuesta.json() == {"detalle": MENSAJE_REMOTO}


# --- bloqueo, freno, base ocupada (S1, S2) ------------------------------------------------------


@pytest.mark.usefixtures("vacia")
def test_cinco_codigos_errados_bloquean_quince_minutos_incluso_al_correcto(reloj) -> None:
    codigo = emitir(cuando=T0)
    nav = navegador()
    for _ in range(4):
        respuesta = reclamar(nav, cuerpo("A" * 20))
        assert respuesta.status_code == 401 and respuesta.json() == {"detalle": MENSAJE_CODIGO}
    quinto = reclamar(nav, cuerpo("A" * 20))
    assert quinto.status_code == 423 and quinto.json() == {"detalle": MENSAJE_BLOQUEO}
    sexto = reclamar(nav, cuerpo(codigo))  # el correcto, ya bloqueado
    assert sexto.status_code == 423 and sexto.json() == {"detalle": MENSAJE_BLOQUEO}
    assert contar(Usuario) == 0
    reloj["ahora"] = T0 + timedelta(minutes=14, seconds=59)
    assert reclamar(nav, cuerpo(codigo)).status_code == 423
    reloj["ahora"] = T0 + timedelta(minutes=15)
    assert reclamar(nav, cuerpo(codigo)).status_code == 201


def test_el_freno_global_espera_dos_a_la_exceso_hasta_60_segundos() -> None:
    """Directo sobre `FrenoGlobal` (por la API el contador no pasa de 20, ver abajo)."""
    freno = cuentas.FrenoGlobal()
    esperas = {}
    for fallo in range(1, 27):
        freno.registrar_fallo(T0)
        esperas[fallo] = freno.espera(T0)
    assert esperas[19] == 0.0 and esperas[20] == 1.0
    assert (esperas[21], esperas[22], esperas[23]) == (2.0, 4.0, 8.0)
    assert esperas[25] == 32.0 and esperas[26] == 60.0  # tope
    assert freno.espera(T0 + timedelta(minutes=10)) == 0.0  # la ventana de 10 minutos se vació


@pytest.mark.usefixtures("vacia")
def test_con_veinte_fallos_de_todo_el_equipo_el_reclamo_da_429_sin_calcular_hashes(
    monkeypatch,
) -> None:
    cuentas.FRENO.reiniciar()
    nav = navegador()
    for i in range(20):  # 20 usuarios inexistentes en el acceso normal
        assert (
            nav.post("/v1/sesion", json={"login": f"nadie{i}", "contrasena": "x"}).status_code
            == 401
        )
    calculos: list[str] = []
    monkeypatch.setattr(cuentas, "_huella", lambda contrasena: calculos.append("hash") or "x")
    codigo = emitir()
    respuesta = reclamar(nav, cuerpo(codigo))
    assert respuesta.status_code == 429
    assert respuesta.headers["retry-after"] == "1"
    assert respuesta.json() == {"detalle": MENSAJE_FRENO}
    assert respuesta.headers["cache-control"] == "no-store"
    assert calculos == [] and contar(Usuario) == 0
    cuentas.FRENO.reiniciar()


@pytest.mark.usefixtures("vacia")
def test_una_base_ocupada_es_503(monkeypatch) -> None:
    def ocupada(_sesion) -> None:
        raise ValueError(MENSAJE_OCUPADA)

    codigo = emitir()
    original = cuentas._tomar_escritura
    monkeypatch.setattr(cuentas, "_tomar_escritura", ocupada)
    respuesta = reclamar(navegador(), cuerpo(codigo))
    assert respuesta.status_code == 503 and respuesta.json() == {"detalle": MENSAJE_OCUPADA}
    assert respuesta.headers["cache-control"] == "no-store"
    monkeypatch.setattr(cuentas, "_tomar_escritura", original)
    assert reclamar(navegador(), cuerpo(codigo)).status_code == 201


# --- carrera por la API (S3) --------------------------------------------------------------------


@pytest.mark.usefixtures("vacia")
@pytest.mark.parametrize("con_fila_previa", [True, False], ids=["a-con-fila-previa", "b-sin-fila"])
def test_dos_reclamos_simultaneos_por_la_api_dejan_una_sola_cuenta(con_fila_previa: bool) -> None:
    codigo = emitir()
    if con_fila_previa:
        assert reclamar(navegador(), cuerpo("A" * 20, "previo")).status_code == 401
    barrera = threading.Barrier(2)
    estados: list[int] = []
    candado = threading.Lock()

    def correr(login: str) -> None:
        nav = navegador()
        barrera.wait(timeout=10)
        respuesta = reclamar(nav, cuerpo(codigo, login))
        with candado:
            estados.append(respuesta.status_code)

    hilos = [threading.Thread(target=correr, args=(login,)) for login in ("uno", "dos")]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=90)
    assert sorted(estados) == [201, 401]  # nunca dos 201 ni un 500
    assert contar(Usuario) == 1


# --- secretos (S7) ------------------------------------------------------------------------------


@pytest.mark.usefixtures("vacia")
def test_el_codigo_y_la_contrasena_no_aparecen_en_ninguna_parte(caplog, capsys) -> None:
    caplog.set_level(logging.DEBUG)
    clave = "una clave secreta de prueba 7731"
    codigo = emitir()
    plano = codigo.lower()
    nav = navegador()
    respuestas = [
        reclamar(nav, cuerpo("A" * 20, "uno", contrasena=clave)),  # 401
        reclamar(nav, cuerpo(codigo, "uno", contrasena="corta")),  # 422 de política
        reclamar(nav, cuerpo(codigo, "uno", contrasena="z" * 200)),  # 422 fijo
        reclamar(nav, cuerpo(codigo, "uno", contrasena=clave), origen=None),  # 403
        reclamar(navegador(OTRA_IP), cuerpo(codigo, "uno", contrasena=clave)),  # 403
    ]
    for _ in range(4):  # llegar al bloqueo (423)
        respuestas.append(reclamar(nav, cuerpo("B" * 20, "uno", contrasena=clave)))
    respuestas.append(reclamar(nav, cuerpo(codigo, "uno", contrasena=clave)))
    assert {r.status_code for r in respuestas} >= {401, 403, 422, 423}
    cuentas.FRENO.reiniciar()
    with sesion_de_instalacion() as sesion:  # y un éxito, tras el desbloqueo
        sesion.execute(IntentoAcceso.__table__.delete())
        sesion.commit()
    exito = reclamar(nav, cuerpo(codigo, "uno", contrasena=clave))
    assert exito.status_code == 201
    respuestas.append(exito)
    ficha = ficha_de(exito)
    secretos = [codigo, plano, clave, "A" * 20]
    for respuesta in respuestas:
        cuerpo_de_la_respuesta = respuesta.text + json.dumps(dict(respuesta.headers))
        for secreto in secretos:
            assert secreto not in cuerpo_de_la_respuesta.replace(ficha, "<ficha>")
        assert ficha not in respuesta.text  # la ficha viaja solo en la cookie
    with sesion_de_instalacion() as sesion:
        for evento in sesion.scalars(select(EventoAcceso)):
            fila = f"{evento.login_intentado}|{evento.detalle}|{evento.ip_cliente}|{evento.tipo}"
            for secreto in (codigo, clave, ficha):
                assert secreto not in fila
    salida = capsys.readouterr()
    registro = caplog.text + salida.out + salida.err
    for secreto in (codigo, plano, clave, ficha):
        assert secreto not in registro


@pytest.mark.usefixtures("vacia")
def test_el_contador_del_codigo_y_los_eventos_registran_el_fallo_sin_el_codigo() -> None:
    reclamar(navegador(), cuerpo("A" * 20))
    with sesion_de_instalacion() as sesion:
        fila = sesion.get(IntentoAcceso, cuentas.CLAVE_INTENTOS_CODIGO)
        assert fila is not None and fila.fallos_seguidos == 1
        [evento] = sesion.scalars(select(EventoAcceso).where(EventoAcceso.tipo == "fallo")).all()
        assert (evento.login_intentado, evento.detalle) == ("(codigo)", "codigo")
        assert evento.ip_cliente == "127.0.0.1"
