"""`/v1/produccion/costos`: costos del periodo por la API (Tarea 1 del plan vial). Datos FICTICIOS.

Dos entradas: la clave de API (el usuario guardado es `USUARIO_API`) y la sesion web, con la accion
`registrar_costos_produccion` es de arma y administrador; `rita` (revisa) recibe 403. Los montos
viajan como texto con punto: la coma decimal es cosa del front. Oraculo a mano: dos costos USD de la
cantera, 1250.50 y 300, suman 1550.50.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.dependencias import USUARIO_API
from produccion.modelo import Costo
from seguridad import cuentas
from tests.fixtures.produccion_api import Web, cliente_con_clave, contar
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_produccion"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    copiar_instalacion(_instalacion_migrada)
    yield
    cuentas.FRENO.reiniciar()


@pytest.fixture
def http() -> TestClient:
    return cliente_con_clave()


HORA_DEL_SERVIDOR = datetime(2026, 11, 20, 9, 0, 0)


def _cuerpo(**cambios) -> dict:
    base = {
        "periodo": "2026-11",
        "centro": "cantera",
        "concepto": "gasoil",
        "monto": "1250.50",
        "moneda": "USD",
        "fecha": "2026-11-03",
        "fuente": "factura 12 (ficticia)",
        "nota": "",
    }
    return {**base, **cambios}


def test_alta_y_lista(http) -> None:
    r = http.post("/v1/produccion/costos", json=_cuerpo())
    assert r.status_code == 201, r.text
    nuevo = r.json()["id"]
    segundo = http.post("/v1/produccion/costos", json=_cuerpo(monto="300", concepto="equipo"))
    assert segundo.status_code == 201
    lista = http.get("/v1/produccion/costos", params={"periodo": "2026-11"})
    assert lista.status_code == 200, lista.text
    filas = lista.json()
    assert [f["monto"] for f in filas] == ["1250.50", "300"]
    primera = filas[0]
    assert primera["id"] == nuevo
    assert (primera["centro"], primera["concepto"], primera["moneda"]) == (
        "cantera",
        "gasoil",
        "USD",
    )
    assert (primera["fecha"], primera["fuente"], primera["anulado"]) == (
        "2026-11-03",
        "factura 12 (ficticia)",
        False,
    )
    assert primera["usuario"] == USUARIO_API
    total = sum(Decimal(f["monto"]) for f in filas if f["centro"] == "cantera")
    assert total == Decimal("1550.50")
    assert http.get("/v1/produccion/costos", params={"periodo": "2026-10"}).json() == []


def test_anular_conserva_la_fila_y_la_saca_de_la_lista(http) -> None:
    i = http.post("/v1/produccion/costos", json=_cuerpo()).json()["id"]
    r = http.post(f"/v1/produccion/costos/{i}/anular", json={"motivo": "duplicado"})
    assert r.status_code == 201, r.text
    assert r.json()["id"] != i
    assert http.get("/v1/produccion/costos", params={"periodo": "2026-11"}).json() == []
    todos = http.get(
        "/v1/produccion/costos", params={"periodo": "2026-11", "incluir_anulados": "true"}
    )
    assert len(todos.json()) == 2
    assert contar(Costo) == 2
    otra = http.post(f"/v1/produccion/costos/{i}/anular", json={"motivo": "otra"})
    assert otra.status_code == 409, otra.text


def test_anular_uno_que_no_existe_es_404(http) -> None:
    r = http.post("/v1/produccion/costos/999/anular", json={"motivo": "x"})
    assert r.status_code == 404, r.text


def test_monto_no_decimal_422(http) -> None:
    r = http.post("/v1/produccion/costos", json=_cuerpo(monto="diez"))
    assert r.status_code == 422, r.text
    assert "monto" in r.json()["detalle"]
    assert contar(Costo) == 0


def test_monto_con_coma_422(http) -> None:
    r = http.post("/v1/produccion/costos", json=_cuerpo(monto="1250,50"))
    assert r.status_code == 422, r.text
    assert contar(Costo) == 0


@pytest.mark.parametrize(
    "cambio",
    [
        {"concepto": "voladura"},
        {"centro": "oficina"},
        {"moneda": "EUR"},
        {"monto": "-1"},
        {"fuente": " "},
        {"fecha": "2026-12-01"},
        {"periodo": "2026-13"},
        {"fecha": "03/11/2026"},
    ],
)
def test_datos_invalidos_422_y_no_se_guarda_nada(http, cambio: dict) -> None:
    r = http.post("/v1/produccion/costos", json=_cuerpo(**cambio))
    assert r.status_code == 422, r.text
    assert contar(Costo) == 0


def test_periodo_invalido_en_la_consulta_422(http) -> None:
    assert http.get("/v1/produccion/costos", params={"periodo": "noviembre"}).status_code == 422


def test_con_sesion_arma_y_administrador_registran(_instalacion_de_la_prueba) -> None:
    for quien in ("ana", "admin"):
        web = Web(quien)
        r = web.post("/v1/produccion/costos", json=_cuerpo(fuente=f"factura de {quien}"))
        assert r.status_code == 201, r.text
    filas = Web("ana").get("/v1/produccion/costos", params={"periodo": "2026-11"}).json()
    assert len(filas) == 2
    assert len({f["usuario"] for f in filas}) == 2


def test_revisa_recibe_403(_instalacion_de_la_prueba) -> None:
    rita = Web("rita")
    r = rita.post("/v1/produccion/costos", json=_cuerpo())
    assert r.status_code == 403, r.text
    assert rita.get("/v1/produccion/costos", params={"periodo": "2026-11"}).status_code == 403
    anular = rita.post("/v1/produccion/costos/1/anular", json={"motivo": "x"})
    assert anular.status_code == 403
    assert contar(Costo) == 0


def test_una_escritura_con_sesion_sin_csrf_se_rechaza(_instalacion_de_la_prueba) -> None:
    web = Web("ana")
    r = web.cliente.post("/v1/produccion/costos", json=_cuerpo())
    assert r.status_code == 403, r.text
    assert contar(Costo) == 0


@pytest.fixture
def reloj(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """El reloj del servidor, fijo: `registrado` sale de el y no del cuerpo."""
    monkeypatch.setattr("api.rutas.produccion._ahora", lambda: HORA_DEL_SERVIDOR)
    return HORA_DEL_SERVIDOR


def test_registrado_es_la_hora_del_servidor_y_el_ahora_del_cuerpo_se_ignora(http, reloj) -> None:
    r = http.post("/v1/produccion/costos", json={**_cuerpo(), "ahora": "2000-01-01T00:00:00"})
    assert r.status_code == 201, r.text
    i = r.json()["id"]
    http.post(
        f"/v1/produccion/costos/{i}/anular",
        json={"motivo": "duplicado", "ahora": "1999-01-01T00:00:00"},
    )
    filas = http.get(
        "/v1/produccion/costos", params={"periodo": "2026-11", "incluir_anulados": "true"}
    ).json()
    assert [f["registrado"] for f in filas] == ["2026-11-20T09:00:00"] * 2


def test_anular_sin_motivo_422(http) -> None:
    i = http.post("/v1/produccion/costos", json=_cuerpo()).json()["id"]
    for motivo in ("", "   "):
        r = http.post(f"/v1/produccion/costos/{i}/anular", json={"motivo": motivo})
        assert r.status_code == 422, r.text
    assert contar(Costo) == 1


def test_la_lista_trae_el_motivo_de_la_anulacion(http) -> None:
    i = http.post("/v1/produccion/costos", json=_cuerpo()).json()["id"]
    n = http.post(f"/v1/produccion/costos/{i}/anular", json={"motivo": "duplicado"}).json()["id"]
    filas = http.get(
        "/v1/produccion/costos", params={"periodo": "2026-11", "incluir_anulados": "true"}
    ).json()
    assert {f["id"]: (f["motivo"], f["anula_id"]) for f in filas} == {
        i: ("", None),
        n: ("duplicado", i),
    }


def test_totales_por_centro_y_moneda(http) -> None:
    """Oraculo a mano: cantera 1250.50 + 300 USD = 1550.50; planta 800 Bs aparte; el anulado y su
    anulacion no suman."""
    http.post("/v1/produccion/costos", json=_cuerpo())
    http.post("/v1/produccion/costos", json=_cuerpo(monto="300", concepto="equipo"))
    http.post(
        "/v1/produccion/costos",
        json=_cuerpo(centro="planta", concepto="nomina", monto="800", moneda="Bs"),
    )
    malo = http.post("/v1/produccion/costos", json=_cuerpo(monto="77")).json()["id"]
    http.post(f"/v1/produccion/costos/{malo}/anular", json={"motivo": "duplicado"})
    r = http.get("/v1/produccion/costos/totales", params={"periodo": "2026-11"})
    assert r.status_code == 200, r.text
    assert r.json() == [
        {"centro": "cantera", "moneda": "USD", "total": "1550.50"},
        {"centro": "planta", "moneda": "Bs", "total": "800"},
    ]


def test_totales_de_un_periodo_vacio_o_invalido(http) -> None:
    assert http.get("/v1/produccion/costos/totales", params={"periodo": "2026-10"}).json() == []
    assert (
        http.get("/v1/produccion/costos/totales", params={"periodo": "noviembre"}).status_code
        == 422
    )


def test_totales_revisa_recibe_403(_instalacion_de_la_prueba) -> None:
    r = Web("rita").get("/v1/produccion/costos/totales", params={"periodo": "2026-11"})
    assert r.status_code == 403, r.text
