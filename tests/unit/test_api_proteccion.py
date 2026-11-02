"""Piezas puras de la protección de la API (spec S5 §8.3).

Aplicaciones mínimas de FastAPI, sin la base de la instalación: el filtro de redes, el de hosts y
el tope del cuerpo se prueban por separado, con fronteras escritas a mano (límite y límite + 1).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

from api import proteccion


@pytest.mark.parametrize(
    ("host", "esperado"),
    [
        ("127.0.0.1", True),
        ("127.255.255.254", True),
        ("::1", True),
        ("10.0.0.5", True),
        ("192.168.1.30", True),
        ("172.16.0.9", True),
        ("172.31.255.255", True),
        ("172.32.0.1", False),
        ("fe80::1", True),
        ("fd00::5", True),
        ("8.8.8.8", False),
        ("::ffff:8.8.8.8", False),
        ("::ffff:192.168.1.30", True),
        ("2001:4860:4860::8888", False),
        ("testclient", False),
        ("", False),
        (None, False),
    ],
)
def test_ip_permitida(host: str | None, esperado: bool) -> None:
    assert proteccion.ip_permitida(host) is esperado


def test_los_anfitriones_son_el_bucle_local_y_la_ip_elegida() -> None:
    assert proteccion.anfitriones_permitidos(None) == ["127.0.0.1", "localhost"]
    assert proteccion.anfitriones_permitidos("192.168.1.20") == [
        "127.0.0.1",
        "localhost",
        "192.168.1.20",
    ]
    for rara in ("0.0.0.0", "::", "no-es-ip", "8.8.8.8", "fd00::1", "127.0.0.1", ""):
        assert proteccion.anfitriones_permitidos(rara) == ["127.0.0.1", "localhost"]


def test_en_producto_lo_dice_la_variable() -> None:
    assert proteccion.en_producto({"SILICE_PRODUCTO": "1"}) is True
    assert proteccion.en_producto({"SILICE_PRODUCTO": "0"}) is False
    assert proteccion.en_producto({"SILICE_PRODUCTO": "si"}) is False
    assert proteccion.en_producto({}) is False


def test_la_documentacion_se_apaga_solo_en_el_producto() -> None:
    assert proteccion.opciones_documentacion({"SILICE_PRODUCTO": "1"}) == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }
    assert proteccion.opciones_documentacion({}) == {}


def _app_minima() -> FastAPI:
    app = FastAPI()

    @app.get("/x")
    def _x() -> dict[str, str]:
        return {"ok": "si"}

    @app.post("/eco")
    async def _eco(request: Request) -> dict[str, int]:
        return {"bytes": len(await request.body())}

    @app.websocket("/ws")
    async def _ws(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text("hola")
        await websocket.close()

    return app


def test_proteger_reemplaza_el_filtro_de_hosts_de_s3_por_el_suyo() -> None:
    app = _app_minima()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])
    proteccion.proteger(app, {"SILICE_DIRECCION": "192.168.1.20"})
    asignados = [m for m in app.user_middleware if m.cls is TrustedHostMiddleware]
    assert len(asignados) == 1
    cliente = TestClient(app, base_url="http://192.168.1.20:8000", client=("192.168.1.30", 1))
    assert cliente.get("/x").status_code == 200
    ajeno = TestClient(app, base_url="http://otro.ejemplo", client=("192.168.1.30", 1))
    assert ajeno.get("/x").status_code == 400


def test_sin_direccion_solo_el_bucle_local_es_anfitrion() -> None:
    app = _app_minima()
    proteccion.proteger(app, {})
    local = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1))
    assert local.get("/x").status_code == 200
    por_ip = TestClient(app, base_url="http://192.168.1.20:8000", client=("192.168.1.30", 1))
    assert por_ip.get("/x").status_code == 400


def test_una_ip_publica_recibe_403_con_detalle() -> None:
    app = _app_minima()
    proteccion.proteger(app, {})
    cliente = TestClient(app, base_url="http://127.0.0.1:8000", client=("8.8.8.8", 1))
    respuesta = cliente.get("/x")
    assert respuesta.status_code == 403 and "red local" in respuesta.json()["detalle"]


def test_un_websocket_desde_una_ip_publica_se_cierra_con_1008() -> None:
    app = _app_minima()
    proteccion.proteger(app, {})
    publico = TestClient(app, base_url="http://127.0.0.1:8000", client=("8.8.8.8", 1))
    with pytest.raises(WebSocketDisconnect) as cierre:
        with publico.websocket_connect("ws://127.0.0.1:8000/ws") as ws:
            ws.receive_text()
    assert cierre.value.code == 1008
    local = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1))
    with local.websocket_connect("ws://127.0.0.1:8000/ws") as ws:
        assert ws.receive_text() == "hola"


def _app_con_tope(limite: int) -> TestClient:
    app = _app_minima()
    app.add_middleware(proteccion.LimiteDeCuerpo, limite=limite)
    return TestClient(app)


def test_el_tope_deja_pasar_el_limite_exacto_y_corta_uno_mas() -> None:
    cliente = _app_con_tope(10)
    assert cliente.post("/eco", content=b"x" * 10).json() == {"bytes": 10}
    respuesta = cliente.post("/eco", content=b"x" * 11)
    assert respuesta.status_code == 413 and "20 MiB" in respuesta.json()["detalle"]


def test_el_tope_cuenta_los_bytes_cuando_no_hay_content_length() -> None:
    """Un cuerpo por partes (`Transfer-Encoding: chunked`) no declara su tamaño: se cuenta."""
    cliente = _app_con_tope(10)

    def partes(total: int):
        for _ in range(total):
            yield b"x"

    assert cliente.post("/eco", content=partes(10)).json() == {"bytes": 10}
    assert cliente.post("/eco", content=partes(11)).status_code == 413


def test_el_cuerpo_por_partes_de_mas_del_tope_en_una_ruta_con_cuerpo_json_es_413() -> None:
    """Defecto real: si la ruta lee el cuerpo como JSON, FastAPI convertia la excepcion del tope
    en un 400 «There was an error parsing the body» (en ingles, clave `detail`). Debe ser el 413
    con el texto fijo y la clave `detalle`, igual que con `Content-Length`."""
    app = _app_minima()

    @app.post("/json")
    async def _json(datos: dict) -> dict[str, int]:
        return {"claves": len(datos)}

    app.add_middleware(proteccion.LimiteDeCuerpo, limite=100)
    cliente = TestClient(app)

    def partes(total: int):
        yield b'{"a":"'
        for _ in range(total):
            yield b"x"
        yield b'"}'

    esperado = {"detalle": "El cuerpo de la peticion excede el maximo de 20 MiB."}
    respuesta = cliente.post(
        "/json", content=partes(200), headers={"Content-Type": "application/json"}
    )
    assert respuesta.status_code == 413 and respuesta.json() == esperado
    assert cliente.post("/json", json={"a": "x" * 200}).json() == esperado  # con Content-Length
    ok = cliente.post("/json", content=partes(50), headers={"Content-Type": "application/json"})
    assert ok.status_code == 200 and ok.json() == {"claves": 1}  # dentro del tope pasa


def test_el_tope_de_la_api_es_20_mib() -> None:
    assert proteccion.LIMITE_CUERPO == 20_971_520
