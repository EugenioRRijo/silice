"""`/v1/produccion/calculos`: costo por tonelada del periodo por la API (Tarea 4 del plan vial).

Datos FICTICIOS, la planta de noviembre de 2026 de `tests/fixtures/costo_propio.py`, sembrada por la
API (materiales, receta, producciones y costos) y, en la carpeta del caso, la lista de precios y las
tasas. Oraculos a mano: cantera 1.000 USD / 200 t de agregados = 5; planta 1.200 / 100 t = 12;
mezcla 0,94 x 5 + 0,05 x 600 + 8 x 0,5 + 12 = 50,70. Con pesos 0,6 y 0,4: 600 / 150 = 4,
400 / 50 = 8 y mezcla 0,94 x 4 + 46 = 49,76. Cantidades y montos como texto; la hora de registro es
la del servidor (un `ahora` en el cuerpo se ignora).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import dependencias
from api.dependencias import USUARIO_API
from operacion.base_datos import preparar_base
from operacion.config import ruta_caso_por_defecto
from produccion.modelo import Calculo
from seguridad import cuentas
from tests.fixtures import costo_propio as cp
from tests.fixtures.hoja_versiones_api import base
from tests.fixtures.produccion_api import Web, cliente_con_clave, contar
from tests.fixtures.sesion_web import copiar_instalacion, plantilla_con_cuentas

HORA_DEL_SERVIDOR = datetime(2026, 12, 1, 7, 30, 0)
CALCULOS = "/v1/produccion/calculos"


@pytest.fixture(scope="module")
def _instalacion_migrada(tmp_path_factory) -> Path:
    return plantilla_con_cuentas(tmp_path_factory.mktemp("plantilla_produccion"))


@pytest.fixture(autouse=True)
def _instalacion_de_la_prueba(_instalacion_migrada: Path):
    copiar_instalacion(_instalacion_migrada)
    yield
    cuentas.FRENO.reiniciar()
    dependencias.cerrar_motores()  # en Windows un motor abierto retiene el archivo del caso


@pytest.fixture
def http() -> TestClient:
    return cliente_con_clave()


@pytest.fixture
def reloj(monkeypatch) -> None:
    monkeypatch.setattr("api.rutas.produccion._ahora", lambda: HORA_DEL_SERVIDOR)


def _carpeta(lista: bool = True, tasas: dict | None = None) -> None:
    ruta = ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    preparar_base(ruta)
    with base(ruta) as caso:
        if lista:
            cp.lista(caso, "USD", cp.dia(1), cp.LISTA_USD)
        cp.tasas(caso, tasas or {})
        caso.commit()


def _ok(r, estado: int = 201) -> dict:
    assert r.status_code == estado, r.text
    return r.json()


def _planta(http) -> None:
    for codigo in ("AGR-12", "AGR-34", "MZ-1"):
        cuerpo = {"codigo": codigo, "nombre": codigo, "unidad_venta": "t", "existencia_minima": "0"}
        _ok(http.post("/v1/produccion/materiales", json=cuerpo))
    componentes = [
        {"codigo": "AGR-12", "cantidad_por_t": "0.94", "unidad": "t", "tipo": "propio"},
        {"codigo": "CA-30", "cantidad_por_t": "0.05", "unidad": "t", "tipo": "comprado"},
        {"codigo": "GO", "cantidad_por_t": "8", "unidad": "l", "tipo": "comprado"},
    ]
    receta = {
        "producto": "MZ-1",
        "componentes": componentes,
        "fuente": "dosificacion ficticia",
        "vigente_desde": "2026-10-01",
    }
    _ok(http.post("/v1/produccion/recetas", json=receta))
    for codigo, cantidad in (("AGR-12", "150"), ("AGR-34", "50")):
        movimiento = {
            "material_codigo": codigo,
            "tipo": "entrada",
            "fecha": "2026-11-05",
            "cantidad": cantidad,
        }
        _ok(http.post("/v1/produccion/movimientos", json=movimiento))
    produccion = {"producto": "MZ-1", "toneladas": "100", "fecha": "2026-11-10"}
    _ok(http.post("/v1/produccion/producciones", json=produccion))


def _costo(http, centro: str, monto: str, moneda: str, fecha: str) -> int:
    cuerpo = {
        "periodo": "2026-11",
        "centro": centro,
        "concepto": "otro",
        "monto": monto,
        "moneda": moneda,
        "fecha": fecha,
        "fuente": "factura ficticia",
    }
    return _ok(http.post("/v1/produccion/costos", json=cuerpo))["id"]


def _noviembre(http) -> None:
    _planta(http)
    _costo(http, "cantera", "1000", "USD", "2026-11-03")
    _costo(http, "planta", "1200", "USD", "2026-11-12")


def _productos(cuerpo: dict) -> list[tuple[str, Decimal, str]]:
    return [(p["codigo"], Decimal(p["por_tonelada"]), p["presentado"]) for p in cuerpo["productos"]]


def test_calcular_y_volver_a_leer_el_calculo(http, reloj) -> None:
    _carpeta()
    _noviembre(http)
    cuerpo = _ok(
        http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD", "ahora": "2020-01-01"})
    )
    assert _productos(cuerpo) == [
        ("AGR-12", Decimal("5"), "5.00"),
        ("AGR-34", Decimal("5"), "5.00"),
        ("MZ-1", Decimal("50.70"), "50.70"),
    ]
    assert (cuerpo["periodo"], cuerpo["moneda"]) == ("2026-11", "USD")
    assert cuerpo["registrado"] == "2026-12-01T07:30:00"
    assert cuerpo["usuario"] == USUARIO_API
    assert len(cuerpo["huella"]) == 64
    assert cuerpo["instantanea"]["resultado"]["por_tonelada"]["MZ-1"] == "50.70"
    assert _ok(http.get(f"{CALCULOS}/{cuerpo['id']}"), 200) == cuerpo
    assert contar(Calculo) == 1


def test_recalcular_es_otro_calculo_con_la_misma_huella(http) -> None:
    _carpeta()
    _noviembre(http)
    primero = _ok(http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD"}))
    segundo = _ok(http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD"}))
    assert primero["id"] != segundo["id"] and primero["huella"] == segundo["huella"]


def test_con_pesos(http) -> None:
    _carpeta()
    _noviembre(http)
    pesos = {"AGR-12": "0.6", "AGR-34": "0.4"}
    cuerpo = _ok(http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD", "pesos": pesos}))
    assert _productos(cuerpo) == [
        ("AGR-12", Decimal("4"), "4.00"),
        ("AGR-34", Decimal("8"), "8.00"),
        ("MZ-1", Decimal("49.76"), "49.76"),
    ]


def test_un_costo_sin_tasa_de_su_dia_es_422_y_no_guarda_nada(http) -> None:
    _carpeta(tasas={cp.dia(6): cp.TASA})
    _noviembre(http)
    sabado = _costo(http, "cantera", "100", "Bs", "2026-11-07")
    r = http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD"})
    assert r.status_code == 422, r.text
    assert f"n.º {sabado} del 07/11/2026" in r.json()["detalle"]
    assert contar(Calculo) == 0


def test_periodo_sin_produccion_es_422(http) -> None:
    _carpeta()
    _costo(http, "cantera", "1000", "USD", "2026-11-03")
    r = http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD"})
    assert r.status_code == 422, r.text
    assert r.json()["detalle"] == "No hubo producción en 2026-11."
    assert contar(Calculo) == 0


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"periodo": "2026-11", "moneda": "EUR"},
        {"periodo": "2026-13", "moneda": "USD"},
        {"periodo": "2026-11", "moneda": "USD", "pesos": {"AGR-12": "seis", "AGR-34": "0.4"}},
    ],
    ids=["moneda", "periodo", "peso no decimal"],
)
def test_datos_invalidos_son_422(http, cuerpo) -> None:
    _carpeta()
    _noviembre(http)
    r = http.post(CALCULOS, json=cuerpo)
    assert r.status_code == 422, r.text
    assert contar(Calculo) == 0


def test_el_tope_de_pesos_es_50() -> None:
    """`MAX_PESOS`: 50 pesos se admiten en el cuerpo y 51 no (la validacion es del esquema)."""
    from pydantic import ValidationError

    from api.rutas.produccion_planta import CalculoDeCostoEntrada

    def cuerpo(n: int) -> dict:
        return {
            "periodo": "2026-11",
            "moneda": "USD",
            "pesos": {f"P-{i}": "0.02" for i in range(n)},
        }

    assert len(CalculoDeCostoEntrada.model_validate(cuerpo(50)).pesos) == 50
    with pytest.raises(ValidationError, match="50"):
        CalculoDeCostoEntrada.model_validate(cuerpo(51))


def test_cincuenta_y_un_pesos_por_la_api_son_422_sin_guardar(http) -> None:
    pesos = {f"P-{i}": "0.02" for i in range(51)}
    r = http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD", "pesos": pesos})
    assert r.status_code == 422, r.text
    assert contar(Calculo) == 0


def test_un_calculo_con_la_moneda_alterada_es_422(http) -> None:
    import sqlite3
    from contextlib import closing

    from operacion.config import ruta_instalacion

    _carpeta()
    _noviembre(http)
    calculo = _ok(http.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD"}))
    with closing(sqlite3.connect(ruta_instalacion())) as bd:
        bd.execute("UPDATE prod_calculo SET moneda = 'Bs' WHERE id = ?", (calculo["id"],))
        bd.commit()
    r = http.get(f"{CALCULOS}/{calculo['id']}")
    assert r.status_code == 422, r.text
    assert "alterado" in r.json()["detalle"]


def test_un_calculo_inexistente_es_404(http) -> None:
    r = http.get(f"{CALCULOS}/99")
    assert r.status_code == 404, r.text
    assert "detalle" in r.json()


def test_con_sesion_web_el_usuario_es_la_cuenta(http, reloj) -> None:
    _carpeta()
    _noviembre(http)
    ana = Web("ana")
    cuerpo = _ok(ana.post(CALCULOS, json={"periodo": "2026-11", "moneda": "USD"}))
    assert cuerpo["usuario"] != USUARIO_API and "ana" in cuerpo["usuario"]
    assert _ok(ana.get(f"{CALCULOS}/{cuerpo['id']}"), 200)["id"] == cuerpo["id"]
