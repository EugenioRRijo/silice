"""`/v1/produccion/recetas` y producir con receta por la API (Tarea 3 del plan vial). FICTICIOS.

Dos entradas: la clave de API (usuario `USUARIO_API`) y la sesion web (arma y administrador; `rita`,
que revisa, recibe 403 en la tabla de acceso por ruta). Cantidades como texto con punto. La hora de
registro la pone el servidor: un `ahora` en el cuerpo se ignora. Oraculo a mano: producir 100 t de
`MZ-1` con 0,94 t de `AGR-12` por tonelada deja la existencia de `AGR-12` en -94.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.dependencias import USUARIO_API
from operacion.instalacion import sesion_de_instalacion
from produccion.modelo import Movimiento, RecetaRegistrada
from seguridad import cuentas
from tests.fixtures.produccion_api import Web, cliente_con_clave, contar
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

HORA_DEL_SERVIDOR = datetime(2026, 11, 20, 9, 0, 0)


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


@pytest.fixture
def reloj(monkeypatch) -> None:
    monkeypatch.setattr("api.rutas.produccion._ahora", lambda: HORA_DEL_SERVIDOR)


def _material(http, codigo: str, unidad: str = "t", **extra) -> None:
    cuerpo = {"codigo": codigo, "nombre": codigo, "unidad_venta": unidad, "existencia_minima": "0"}
    r = http.post("/v1/produccion/materiales", json={**cuerpo, **extra})
    assert r.status_code == 201, r.text


def _planta(http) -> None:
    _material(http, "AGR-12")
    _material(http, "MZ-1")


def _receta(**cambios) -> dict:
    base = {
        "producto": "MZ-1",
        "componentes": [
            {"codigo": "AGR-12", "cantidad_por_t": "0.94", "unidad": "t", "tipo": "propio"},
            {"codigo": "CA-30", "cantidad_por_t": "0.05", "unidad": "t", "tipo": "comprado"},
            {"codigo": "GO", "cantidad_por_t": "8", "unidad": "l", "tipo": "comprado"},
        ],
        "fuente": "dosificacion ficticia 1",
        "vigente_desde": "2026-10-01",
    }
    return {**base, **cambios}


def _existencias(http) -> dict[str, str]:
    r = http.get("/v1/produccion/existencias")
    assert r.status_code == 200, r.text
    return {f["codigo"]: f["existencia"] for f in r.json()}


def test_registrar_y_leer_la_receta_vigente(http) -> None:
    r = http.post("/v1/produccion/recetas", json=_receta())
    assert r.status_code == 201, r.text
    nueva = r.json()["id"]
    otra = http.post(
        "/v1/produccion/recetas",
        json=_receta(vigente_desde="2026-11-01", fuente="dosificacion ficticia 2"),
    )
    assert otra.status_code == 201 and otra.json()["id"] != nueva
    de_octubre = http.get(
        "/v1/produccion/recetas/vigente", params={"producto": "MZ-1", "fecha": "2026-10-15"}
    )
    assert de_octubre.status_code == 200, de_octubre.text
    cuerpo = de_octubre.json()
    assert (cuerpo["id"], cuerpo["producto"], cuerpo["vigente_desde"]) == (
        nueva,
        "MZ-1",
        "2026-10-01",
    )
    assert cuerpo["fuente"] == "dosificacion ficticia 1"
    assert cuerpo["componentes"][0] == {
        "codigo": "AGR-12",
        "cantidad_por_t": "0.94",
        "unidad": "t",
        "tipo": "propio",
    }
    assert [c["codigo"] for c in cuerpo["componentes"]] == ["AGR-12", "CA-30", "GO"]


def test_sin_receta_vigente_es_404(http) -> None:
    http.post("/v1/produccion/recetas", json=_receta())
    r = http.get(
        "/v1/produccion/recetas/vigente", params={"producto": "MZ-1", "fecha": "2026-09-30"}
    )
    assert r.status_code == 404 and "MZ-1" in r.json()["detalle"]


def test_la_suma_mala_y_los_datos_invalidos_son_422_y_no_guardan(http) -> None:
    mala = _receta(
        componentes=[
            {"codigo": "AGR-12", "cantidad_por_t": "0.90", "unidad": "t", "tipo": "propio"},
            {"codigo": "CA-30", "cantidad_por_t": "0.05", "unidad": "t", "tipo": "comprado"},
        ]
    )
    r = http.post("/v1/produccion/recetas", json=mala)
    assert r.status_code == 422 and "suman 0,95 t" in r.json()["detalle"]
    texto = _receta()
    texto["componentes"][0]["cantidad_por_t"] = "mucho"
    assert http.post("/v1/produccion/recetas", json=texto).status_code == 422
    numero = _receta()
    numero["componentes"][0]["cantidad_por_t"] = 0.94  # un numero JSON no es texto
    assert http.post("/v1/produccion/recetas", json=numero).status_code == 422
    assert (
        http.post("/v1/produccion/recetas", json=_receta(vigente_desde="ayer")).status_code == 422
    )
    assert http.post("/v1/produccion/recetas", json=_receta(fuente=" ")).status_code == 422
    assert contar(RecetaRegistrada) == 0


def test_producir_con_receta_consume_el_agregado_propio(http) -> None:
    _planta(http)
    http.post("/v1/produccion/recetas", json=_receta())
    r = http.post(
        "/v1/produccion/producciones",
        json={"producto": "MZ-1", "toneladas": "100", "fecha": "2026-10-15"},
    )
    assert r.status_code == 201, r.text
    assert len(r.json()["movimientos"]) == 2
    assert _existencias(http) == {"AGR-12": "-94", "MZ-1": "100"}
    assert contar(Movimiento) == 2


def test_producir_sin_receta_vigente_es_422_y_no_deja_nada(http) -> None:
    _planta(http)
    r = http.post(
        "/v1/produccion/producciones",
        json={"producto": "MZ-1", "toneladas": "100", "fecha": "2026-10-15"},
    )
    assert r.status_code == 422 and "MZ-1" in r.json()["detalle"]
    texto = http.post(
        "/v1/produccion/producciones",
        json={"producto": "MZ-1", "toneladas": "cien", "fecha": "2026-10-15"},
    )
    assert texto.status_code == 422
    assert contar(Movimiento) == 0


def test_producido_del_periodo_en_toneladas(http) -> None:
    _material(http, "ARENA", "m3", densidad_t_m3="1.60")
    _material(http, "PIEDRA")
    for codigo, cantidad in (("ARENA", "100"), ("PIEDRA", "50")):
        r = http.post(
            "/v1/produccion/movimientos",
            json={
                "material_codigo": codigo,
                "tipo": "entrada",
                "fecha": "2026-10-03",
                "cantidad": cantidad,
            },
        )
        assert r.status_code == 201, r.text
    r = http.get("/v1/produccion/producido", params={"periodo": "2026-10"})
    assert r.status_code == 200, r.text
    assert [(f["codigo"], Decimal(f["toneladas"])) for f in r.json()] == [
        ("ARENA", Decimal("160")),
        ("PIEDRA", Decimal("50")),
    ]
    assert http.get("/v1/produccion/producido", params={"periodo": "2026-13"}).status_code == 422
    assert http.get("/v1/produccion/producido", params={"periodo": "2026-11"}).json() == []


def test_la_hora_de_registro_es_la_del_servidor(http, reloj) -> None:
    _planta(http)
    cuerpo = {**_receta(), "ahora": "2000-01-01T00:00:00"}
    assert http.post("/v1/produccion/recetas", json=cuerpo).status_code == 201
    r = http.post(
        "/v1/produccion/producciones",
        json={
            "producto": "MZ-1",
            "toneladas": "100",
            "fecha": "2026-10-15",
            "ahora": "1999-01-01T00:00:00",
        },
    )
    assert r.status_code == 201, r.text
    with sesion_de_instalacion() as sesion:
        assert sesion.query(RecetaRegistrada).one().registrado == HORA_DEL_SERVIDOR
        assert {m.registrado for m in sesion.query(Movimiento)} == {HORA_DEL_SERVIDOR}


def test_el_usuario_guardado_es_el_de_la_clave_o_el_de_la_sesion(http) -> None:
    http.post("/v1/produccion/recetas", json=_receta())
    web = Web("ana")
    assert (
        web.post("/v1/produccion/recetas", json=_receta(vigente_desde="2026-11-01")).status_code
        == 201
    )
    with sesion_de_instalacion() as sesion:
        usuarios = [r.usuario for r in sesion.query(RecetaRegistrada).order_by(RecetaRegistrada.id)]
    assert usuarios[0] == USUARIO_API
    assert usuarios[1] != USUARIO_API and "ana" in usuarios[1]


def test_la_receta_se_guarda_aparte_de_la_anterior(http) -> None:
    http.post("/v1/produccion/recetas", json=_receta())
    http.post("/v1/produccion/recetas", json=_receta(fuente="correccion ficticia"))
    assert contar(RecetaRegistrada) == 2
