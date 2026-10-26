"""`/v1/control/*` con causas de retraso y atraso por partida (MP-7, Tarea 22).

Sobre la obra de dos partidas de `tests/fixtures/obra_atrasada.py` (línea base desde el lunes
2026-11-02, días hábiles; A: 10 m3 en los días 1 a 5, B: 6 m2 en los días 6 y 7). Lo que se prueba:

- `POST /v1/control/valuaciones` acepta `causa` por línea (una clave de la lista o nula) y rechaza
  una desconocida con 422 sin repetir lo enviado y sin guardar nada;
- `GET /v1/control/valuaciones` da la lista de causas (clave y nombre) para el selector;
- `GET /v1/control/calculo` da `atrasos` con código, días, causa y texto.

Oráculos a mano (las cuentas están en `tests/unit/test_causas.py`): con A en 5 de 10 al día 5,
A termina en el día 10 contra 5 del plan (5 días) y B en el 9 contra 7 (2 días).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import obra_atrasada as obra
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

P = {"proyecto": obra.NOMBRE}
MENSAJE_DESCONOCIDA = "La causa del retraso no está en la lista de causas."


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_causas")
    ruta = carpeta / "dos.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            obra.sembrar_dos_partidas(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return {"instalacion": plantilla_con_cuentas(carpeta), "dos": ruta}


@pytest.fixture(autouse=True)
def _entorno(
    _plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[None]:
    copia = tmp_path / "caso.db"
    copia.write_bytes(_plantillas["dos"].read_bytes())
    monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{copia.as_posix()}")
    copiar_instalacion(_plantillas["instalacion"])
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _arma():
    navegador, ficha = con_cuenta(app, "ana")
    return navegador, protegida(ficha)


def _valuacion(lineas: list[dict[str, object]], **extra) -> dict[str, object]:
    return {
        **P,
        "numero": "V-01",
        "desde": "2026-11-02",
        "hasta": "2026-11-06",
        "fecha": "2026-11-06",
        "inspector": "Ing. Ficticio",
        "lineas": lineas,
        "fuente": obra.FUENTE,
        **extra,
    }


def test_la_lista_de_causas_viene_con_las_valuaciones() -> None:
    navegador, _ = _arma()
    datos = navegador.get("/v1/control/valuaciones", params=P).json()
    assert datos["causas"] == [
        {"clave": "compra_tardia", "nombre": "Compra tardía"},
        {"clave": "precio", "nombre": "Precio"},
        {"clave": "clima", "nombre": "Lluvia o clima"},
        {"clave": "cambio_cliente", "nombre": "Cambio del cliente"},
        {"clave": "falta_personal", "nombre": "Falta de personal"},
        {"clave": "falla_equipo", "nombre": "Falla de equipo"},
        {"clave": "otra", "nombre": "Otra"},
    ]


def test_registrar_con_causa_y_el_calculo_trae_el_atraso_por_partida() -> None:
    navegador, cabeceras = _arma()
    cuerpo = _valuacion([{"partida": "A", "cantidad": "5", "causa": "compra_tardia"}])
    respuesta = navegador.post("/v1/control/valuaciones", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    calculo = navegador.get("/v1/control/calculo", params=P).json()
    assert calculo["atrasos"] == [
        {
            "codigo": "A",
            "dias": 5,
            "causa": "compra_tardia",
            "texto": "A atrasada 5 días: Compra tardía",
        },
        {
            "codigo": "B",
            "dias": 2,
            "causa": None,
            "texto": "B atrasada 2 días: sin causa declarada",
        },
    ]


@pytest.mark.parametrize("linea", [{"causa": None}, {}])
def test_la_causa_nula_o_ausente_se_acepta_sin_causa(linea: dict[str, object]) -> None:
    navegador, cabeceras = _arma()
    cuerpo = _valuacion([{"partida": "A", "cantidad": "5", **linea}])
    respuesta = navegador.post("/v1/control/valuaciones", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    atrasos = navegador.get("/v1/control/calculo", params=P).json()["atrasos"]
    assert atrasos[0] == {
        "codigo": "A",
        "dias": 5,
        "causa": None,
        "texto": "A atrasada 5 días: sin causa declarada",
    }


def test_una_causa_desconocida_da_422_sin_eco_y_no_guarda_la_valuacion() -> None:
    navegador, cabeceras = _arma()
    hostil = "<script>alert('causa')</script>"
    cuerpo = _valuacion([{"partida": "A", "cantidad": "5", "causa": hostil}])
    respuesta = navegador.post("/v1/control/valuaciones", json=cuerpo, headers=cabeceras)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_DESCONOCIDA}
    assert "script" not in respuesta.text
    datos = navegador.get("/v1/control/valuaciones", params=P).json()
    assert datos["filas"] == [] and datos["anulables"] == []


def test_sin_csrf_no_se_registra_la_causa() -> None:
    navegador, _ = con_cuenta(app, "ana")
    cuerpo = _valuacion([{"partida": "A", "cantidad": "5", "causa": "clima"}])
    assert navegador.post("/v1/control/valuaciones", json=cuerpo).status_code == 403


def test_sin_valuaciones_el_calculo_no_trae_atrasos() -> None:
    navegador, _ = _arma()
    calculo = navegador.get("/v1/control/calculo", params=P).json()
    assert calculo["estado"] == "sin_valuaciones"
    assert calculo["atrasos"] == []
