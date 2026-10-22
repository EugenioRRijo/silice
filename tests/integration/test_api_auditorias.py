"""`POST /v1/auditorias`: clave de API, tope de cuerpo, hosts y lector estricto (RF-88, RNF-16;
spec S3 §10 y §13.2). La instalación es la `instalacion.db` temporal de la suite.

Adaptado al código real (bitácora S3-4 y nota de la tarea 21): `api/seguridad.py` no existe; la
clave, el tope de 20 MiB y los hosts son los de `api.proteccion` (PR #73) y los hosts extra los
pone `SILICE_DIRECCION` (`anfitriones_permitidos`), no `SILICE_HOSTS_PERMITIDOS`.

Los esperados salen de la memoria del ejemplo (`tests/fixtures/canonico/ejemplo_v1.py`: PU
41,83987500; total 836,79750000) y de aritmética aparte, no de la ruta."""

from __future__ import annotations

import asyncio
import copy
import json
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api import proteccion
from api.main import app
from api.rutas.auditorias import servicios_de_la_api
from auditoria.reauditoria import ReferenciaDeMercado, Servicios
from operacion.instalacion import sesion_de_instalacion
from seguridad import claves_api
from seguridad.modelo import EventoAcceso
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1
from tests.fixtures.claves_api import ANFITRION, CABECERA, IP_LOCAL, crear_clave_de_prueba

HOY = "2026-11-10"


@pytest.fixture
def api():
    """`(cliente, clave)`; la clave de API ya existe en la instalación temporal y es válida."""
    clave = crear_clave_de_prueba()
    app.dependency_overrides[servicios_de_la_api] = lambda: Servicios()
    try:
        with TestClient(app, base_url=ANFITRION, client=IP_LOCAL) as cliente:
            yield cliente, clave
    finally:
        app.dependency_overrides.clear()


def cuerpo(**cambios) -> bytes:
    objeto = {"documento": copy.deepcopy(EJEMPLO_V1), "fecha_evaluacion": HOY}
    objeto.update(cambios)
    return json.dumps(objeto).encode()


def post(cliente, clave, datos: bytes, **cabeceras):
    return cliente.post(
        "/v1/auditorias",
        content=datos,
        headers={CABECERA: clave, "content-type": "application/json", **cabeceras},
    )


def _eventos() -> int:
    with sesion_de_instalacion() as bd:
        return bd.query(EventoAcceso).count()


def test_con_clave_valida_devuelve_el_informe_y_los_montos_como_texto(api) -> None:
    cliente, clave = api
    r = post(cliente, clave, cuerpo())
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["fecha_evaluacion"] == HOY and datos["termino"] is True
    assert datos["total_recalculado"] == "836.79750000" and datos["diferencias"] == []
    assert datos["contextos"] == ["R1-R7", "R11-R12"]
    assert datos["avisos"] == []
    assert isinstance(datos["total_recalculado"], str)  # los montos viajan como texto


def test_la_misma_peticion_da_siempre_el_mismo_informe(api) -> None:
    cliente, clave = api
    assert post(cliente, clave, cuerpo()).json() == post(cliente, clave, cuerpo()).json()


def test_la_ruta_no_guarda_nada_en_la_instalacion(api) -> None:
    """Solo la clave toca la instalación (último uso): ningún evento nuevo por auditar."""
    cliente, clave = api
    post(cliente, clave, cuerpo())  # primer uso: renueva `ultimo_uso`
    antes = _eventos()
    assert post(cliente, clave, cuerpo()).status_code == 200
    assert _eventos() == antes


def test_declarado_contra_recalculado_se_informa_con_su_monto(api) -> None:
    cliente, clave = api
    documento = copy.deepcopy(EJEMPLO_V1)
    documento["renglones"][0]["precio_unitario"] = "99.00"
    r = post(cliente, clave, cuerpo(documento=documento))
    assert r.status_code == 200, r.text
    diferencias = r.json()["diferencias"]
    assert [d["campo"] for d in diferencias] == ["precio_unitario"]  # el total declarado cuadra
    [d] = diferencias
    assert (d["declarado"], d["recalculado"]) == ("99.00", "41.83987500")
    # (99,00 - 41,839875) x 20 = 57,160125 x 20 = 1143,2025 (a mano)
    assert Decimal(d["monto"]) == Decimal("1143.2025")
    assert r.json()["total_recalculado"] == "836.79750000"  # no cree lo declarado


def test_una_cifra_mandada_como_numero_json_se_acepta_si_cumple_el_patron(api) -> None:
    """La ruta devuelve a texto los `Decimal` del lector estricto: `20.0` como número vale."""
    cliente, clave = api
    texto = cuerpo().decode().replace('"cantidad": "20"', '"cantidad": 20.0', 1)
    assert '"cantidad": 20.0' in texto
    r = post(cliente, clave, texto.encode())
    assert r.status_code == 200, r.text


def test_con_el_anexo_de_espacio_corren_r8_a_r10_r15_y_r17(api) -> None:
    from adapters.espacio.serie import espacio_a_objeto
    from tests.fixtures.espacio_of001 import espacio_of001

    cliente, clave = api
    r = post(cliente, clave, cuerpo(anexo_espacio=espacio_a_objeto(espacio_of001())))
    assert r.status_code == 200, r.text
    assert r.json()["contextos"] == ["R1-R7", "R8-R10", "R15", "R17", "R11-R12"]
    reglas = [h["regla"] for h in r.json()["no_declarados"]]
    assert reglas.count("R8") == 33  # memoria diferencias_s3.md §4: 33 R8 de OF-001
    assert not {"R9", "R10", "R15", "R17"} & set(reglas)


def test_un_anexo_de_espacio_que_no_es_objeto_es_422(api) -> None:
    cliente, clave = api
    assert post(cliente, clave, cuerpo(anexo_espacio=[1, 2])).status_code == 422


def test_r11_usa_los_servicios_de_la_instalacion_que_revisa(api) -> None:
    cliente, clave = api
    documento = copy.deepcopy(EJEMPLO_V1)
    documento["composiciones"][0]["lineas"][0]["referencia"] = "MP-0042"
    app.dependency_overrides[servicios_de_la_api] = lambda: Servicios(
        referencia_de=lambda c: ReferenciaDeMercado("MP-0042", Decimal("10.00"), "USD", None)
    )
    r = post(cliente, clave, cuerpo(documento=documento))
    [r11] = [
        h
        for h in r.json()["no_declarados"]
        if h["regla"] == "R11" and h["severidad"] == "ADVERTENCIA"
    ]
    # Arena 14,00 contra 10,00: 14/10 - 1 = +40 %
    assert "MP-0042" in r11["descripcion"] and "+40.00 %" in r11["descripcion"]


def test_sin_clave_o_con_una_mala_o_revocada_es_401_con_el_mismo_mensaje(api) -> None:
    """Ola 0a (sesión 2b, RM-3): la ruta acepta la clave o la sesión del navegador. Con la
    cabecera de la clave (vacía, mala o revocada) responde y registra como antes; sin cabecera ni
    cookie es el 401 de la sesión (`exigir_clave_o_sesion`, RS2-5), sin evento: nadie presentó una
    clave. Antes de la ola 0a ese caso también era «clave ausente» con su evento."""
    cliente, clave = api
    with sesion_de_instalacion() as bd:
        revocada, fila = claves_api.crear(bd, "otra", "admin", datetime(2026, 11, 10, 9))
        claves_api.revocar(bd, fila.id, "admin", datetime(2026, 11, 10, 9))
    antes = _eventos()
    mensajes = set()
    for presentada in ("", "no-es-una-clave", "ABCDEFGH.inventada", revocada):
        r = cliente.post("/v1/auditorias", content=cuerpo(), headers={CABECERA: presentada})
        assert r.status_code == 401, presentada
        mensajes.add(r.json()["detalle"])
    assert mensajes == {proteccion.MENSAJE_SIN_CLAVE}
    assert _eventos() == antes + 4  # cada rechazo de una clave queda en el registro
    sin_nada = cliente.post("/v1/auditorias", content=cuerpo())
    assert sin_nada.status_code == 401 and _eventos() == antes + 4
    assert post(cliente, clave, cuerpo()).status_code == 200  # la buena sigue sirviendo


def test_toda_ruta_menos_salud_exige_la_clave(api) -> None:
    """Recorre las rutas publicadas en OpenAPI: ninguna responde sin clave salvo `/salud`."""
    cliente, _ = api
    rutas = [
        (p, m)
        for p, ops in app.openapi()["paths"].items()
        # /v1/sesion: acceso por cuenta (RT-9); /v1/primer-arranque*: públicas, solo el propio
        # equipo, con `Origin` y código (BCP-1; sus pruebas: test_api_primer_arranque.py)
        if p not in {"/salud", "/v1/sesion", "/v1/primer-arranque", "/v1/primer-arranque/reclamo"}
        for m in ops
        if m in {"get", "post", "put", "patch", "delete"}
    ]
    assert ("/v1/auditorias", "post") in rutas
    for ruta, metodo in rutas:
        r = cliente.request(metodo.upper(), ruta.replace("{", "x").replace("}", ""))
        assert r.status_code == 401, (metodo, ruta, r.status_code)
    assert cliente.get("/salud").status_code == 200


def test_un_host_ajeno_se_rechaza_contra_el_dns_rebinding(api) -> None:
    cliente, clave = api
    r = cliente.post(
        "/v1/auditorias",
        content=cuerpo(),
        headers={CABECERA: clave, "host": "evil.example.com"},
    )
    assert r.status_code == 400


def test_los_hosts_extra_los_pone_la_direccion_privada_del_equipo() -> None:
    assert proteccion.anfitriones_permitidos(None) == ["127.0.0.1", "localhost"]
    assert proteccion.anfitriones_permitidos("192.168.1.20") == [
        "127.0.0.1",
        "localhost",
        "192.168.1.20",
    ]
    assert proteccion.anfitriones_permitidos("8.8.8.8") == ["127.0.0.1", "localhost"]  # pública
    assert proteccion.anfitriones_permitidos("0.0.0.0") == ["127.0.0.1", "localhost"]
    assert proteccion.anfitriones_permitidos("obra.local") == ["127.0.0.1", "localhost"]


@pytest.mark.parametrize(
    "malo",
    [
        b'{"documento": NaN, "fecha_evaluacion": "2026-11-10"}',
        b'{"documento": {}, "documento": {}, "fecha_evaluacion": "2026-11-10"}',
        b'{"documento": {"x": 1E+999999999}, "fecha_evaluacion": "2026-11-10"}',
        b"[" * 65 + b"]" * 65,
        b'{"documento": {}}',
        b'{"documento": {}, "fecha_evaluacion": "ayer"}',
        b'{"fecha_evaluacion": "2026-11-10"}',
        b'{"documento": [], "fecha_evaluacion": "2026-11-10"}',
        b'{"documento": {}, "fecha_evaluacion": "2026-11-10"}',
        b"no es json",
    ],
)
def test_json_hostil_o_incompleto_es_422_y_no_llega_al_motor(api, malo: bytes) -> None:
    cliente, clave = api
    r = post(cliente, clave, malo)
    assert r.status_code == 422 and "detalle" in r.json()


def test_64_niveles_se_leen_y_65_no(api) -> None:
    """Frontera del anidamiento: 64 niveles pasan el lector (falla luego por la forma, 422 por
    otra razón) y 65 se rechazan por profundidad."""
    cliente, clave = api
    con_64 = post(cliente, clave, b"[" * 64 + b"]" * 64).json()["detalle"]
    con_65 = post(cliente, clave, b"[" * 65 + b"]" * 65).json()["detalle"]
    assert con_64 != con_65
    assert "64" in con_65 or "nivel" in con_65.lower()


def test_una_cifra_con_exponente_dentro_del_documento_es_422(api) -> None:
    cliente, clave = api
    documento = copy.deepcopy(EJEMPLO_V1)
    documento["parametros"]["fcas"] = "1E+999999999"
    assert post(cliente, clave, cuerpo(documento=documento)).status_code == 422


def test_el_cuerpo_de_exactamente_20_mib_pasa_y_con_un_byte_mas_es_413(api) -> None:
    cliente, clave = api
    base = cuerpo()
    justo = base + b" " * (proteccion.LIMITE_CUERPO - len(base))
    assert len(justo) == 20 * 1024 * 1024
    assert post(cliente, clave, justo).status_code == 200
    mas = post(cliente, clave, justo + b" ")
    assert mas.status_code == 413 and "20 MiB" in mas.json()["detalle"]


def test_el_middleware_corta_el_cuerpo_sin_leerlo_entero() -> None:
    """Con el cuerpo en trozos y sin `Content-Length`, deja de leer al pasar el tope."""
    leidos, respuestas = [], []
    trozos = [{"type": "http.request", "body": b"x" * 100, "more_body": True} for _ in range(1000)]

    async def app_vacia(scope, receive, send):
        while True:
            mensaje = await receive()
            leidos.append(len(mensaje["body"]))
            if not mensaje.get("more_body"):
                break

    async def recibir():
        return trozos.pop(0)

    async def enviar(mensaje):
        respuestas.append(mensaje)

    mw = proteccion.LimiteDeCuerpo(app_vacia, limite=1000)
    asyncio.run(mw({"type": "http", "headers": []}, recibir, enviar))
    assert respuestas[0]["status"] == 413 and len(leidos) == 10  # 10 x 100 B = 1000 B pasan
    assert len(trozos) == 1000 - 11  # el undécimo trozo ya excedió; el resto no se leyó


def test_un_content_length_mayor_que_el_tope_se_rechaza_sin_llamar_a_la_app() -> None:
    llamadas, respuestas = [], []

    async def app_vacia(scope, receive, send):
        llamadas.append(1)

    async def enviar(mensaje):
        respuestas.append(mensaje)

    async def nada():
        raise AssertionError("no debía leer el cuerpo")

    mw = proteccion.LimiteDeCuerpo(app_vacia, limite=1000)
    asyncio.run(mw({"type": "http", "headers": [(b"content-length", b"1001")]}, nada, enviar))
    assert llamadas == [] and respuestas[0]["status"] == 413
    respuestas.clear()
    asyncio.run(mw({"type": "http", "headers": [(b"content-length", b"1000")]}, nada, enviar))
    assert llamadas == [1] and respuestas == []  # exactamente el tope: pasa a la app


def test_la_reevaluacion_a_otra_fecha_cambia_solo_r12(api) -> None:
    cliente, clave = api
    documento = copy.deepcopy(EJEMPLO_V1)
    for linea in documento["composiciones"][0]["lineas"]:
        linea["precio_origen"]["fecha_precio"] = "2026-09-01"
    pronto = post(cliente, clave, cuerpo(documento=documento, fecha_evaluacion="2026-09-10"))
    tarde = post(cliente, clave, cuerpo(documento=documento, fecha_evaluacion=HOY))
    pronto, tarde = pronto.json(), tarde.json()
    assert not [h for h in pronto["no_declarados"] if h["regla"] == "R12"]
    r12 = [h for h in tarde["no_declarados"] if h["regla"] == "R12"]
    assert len(r12) == 3 and all("70 dias al 10/11/2026" in h["descripcion"] for h in r12)
    otras = [(h["regla"], h["severidad"]) for h in pronto["no_declarados"]]
    assert otras == [(h["regla"], h["severidad"]) for h in tarde["no_declarados"] if h not in r12]


def test_r12_frontera_de_los_30_dias(api) -> None:
    """Plazo de vigencia 30 días (S1-R6): 30 días no marca; 31 marca las tres líneas."""
    cliente, clave = api

    def r12_al(fecha_precio: str) -> int:
        documento = copy.deepcopy(EJEMPLO_V1)
        for linea in documento["composiciones"][0]["lineas"]:
            linea["precio_origen"]["fecha_precio"] = fecha_precio
        datos = post(cliente, clave, cuerpo(documento=documento)).json()
        return sum(1 for h in datos["no_declarados"] if h["regla"] == "R12")

    assert r12_al("2026-10-11") == 0  # 30 días al 10/11/2026
    assert r12_al("2026-10-10") == 3  # 31 días
