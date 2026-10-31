"""`/v1/vial`: los tramos de una versión por la API (Tarea 8 del plan vial). Datos FICTICIOS.

La carpeta es `vivienda.db` (la «Vivienda Demo 80 m2», VIV-001 y VIV-002, de
`tests/fixtures/carpeta_aprobaciones.py`) y las cuentas las de `tests/fixtures/sesion_web.py`. Los
tramos viajan con las cifras como texto con punto (la coma es cosa del front). Oráculos a mano
(Tarea 7): un tramo de 0 a 1 km de 7,3 m con carpeta de 0,05 m a 2,35 t/m3 y planta a 12 km da 7 300
m2, 857,75 t y 10 293 t·km. Versión aprobada: 409 como el resto de la API; CSV con una fila mala:
422 con el número de fila y nada guardado.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import vial as rutas
from aplicacion import aprobaciones
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import (
    OBRA,
    guardar_version,
    sembrar_vivienda,
)
from tests.fixtures.produccion_api import cliente_con_clave
from tests.fixtures.sesion_web import (
    MENSAJE_PERMISO,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
ANA = "Ana <ana>"
MARTES = datetime(2026, 10, 20, 10, 30)
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"
RAIZ = "/v1/vial"
SOLO_CUENTA = "Los tramos se guardan con una cuenta; la clave de API no sirve."

TRAMO = {
    "id": "T1",
    "progresiva_ini_km": "0",
    "progresiva_fin_km": "1",
    "ancho_m": "7.3",
    "distancia_planta_km": "12",
    "capas": [
        {"tipo": "carpeta", "espesor_m": "0.05", "densidad_t_m3": "2.35", "dosis_l_m2": None},
        {"tipo": "base_granular", "espesor_m": "0.20", "densidad_t_m3": None, "dosis_l_m2": None},
        {"tipo": "riego_adherencia", "espesor_m": None, "densidad_t_m3": None, "dosis_l_m2": "0.5"},
    ],
    "demarcacion": [{"tipo": "continua", "lineas": 2}],
}


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_vial")
    vivienda = carpeta / "vivienda.db"
    preparar_base(vivienda)
    motor = crear_motor(f"sqlite:///{vivienda.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            obra = sembrar_vivienda(s, usuario=ANA)
            guardar_version(s, obra, "VIV-002", usuario=ANA)
    finally:
        motor.dispose()
    return {"instalacion": plantilla_con_cuentas(carpeta), "vivienda.db": vivienda}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / "vivienda.db").write_bytes(_plantillas["vivienda.db"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    monkeypatch.setattr(rutas, "ahora", lambda: MARTES)
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def ana() -> tuple[TestClient, str]:
    navegador, ficha = con_cuenta(app, "ana")
    elegida = navegador.post(
        "/v1/casos/actual", json={"nombre": "vivienda.db"}, headers=protegida(ficha)
    )
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


def _params(version: str = "VIV-001") -> dict[str, str]:
    return {"proyecto": OBRA, "version": version}


def _leer(cuenta, version: str = "VIV-001"):
    navegador, _ = cuenta
    return navegador.get(f"{RAIZ}/tramos", params=_params(version))


def _guardar(cuenta, tramos: list[dict], version: str = "VIV-001", fuente: str = ""):
    navegador, ficha = cuenta
    return navegador.put(
        f"{RAIZ}/tramos",
        params=_params(version),
        json={"tramos": tramos, "fuente": fuente},
        headers=protegida(ficha),
    )


def _importar(cuenta, contenido: bytes, nombre: str = "via.csv", version: str = "VIV-001"):
    navegador, ficha = cuenta
    return navegador.post(
        f"{RAIZ}/tramos/importar",
        params=_params(version),
        files={"archivo": (nombre, contenido, "text/csv")},
        headers=protegida(ficha),
    )


def _cantidad(cuerpo: dict, unidad: str, parte: str) -> Decimal:
    (fila,) = [
        c
        for c in cuerpo["cantidades"]
        if c["unidad"] == unidad and parte in c["descripcion"] and c["tramo"] == "T1"
    ]
    return D(fila["cantidad"])


def _filas_guardadas() -> int:
    with closing(sqlite3.connect(config.carpeta_casos() / "vivienda.db")) as conexion:
        return conexion.execute("SELECT COUNT(*) FROM vial_tramos_guardado").fetchone()[0]


def test_version_sin_tramos(ana) -> None:
    r = _leer(ana)
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    assert r.json() == {
        "proyecto": OBRA,
        "version": "VIV-001",
        "editable": True,
        "bloqueo": None,
        "guardado": None,
        "tramos": [],
        "cantidades": [],
    }


def test_guardar_y_leer_con_sus_cantidades(ana) -> None:
    r = _guardar(ana, [TRAMO], fuente="plano 3 (ficticio)")
    assert r.status_code == 200, r.text
    leido = _leer(ana).json()
    assert leido == r.json()
    assert [t["id"] for t in leido["tramos"]] == ["T1"]
    assert leido["tramos"][0]["ancho_m"] == "7.3"
    assert leido["tramos"][0]["capas"][0] == TRAMO["capas"][0]
    assert leido["guardado"] == {
        "usuario": ANA,
        "fecha_hora": "2026-10-20T10:30:00",
        "fuente": "plano 3 (ficticio)",
    }
    assert _cantidad(leido, "m2", "Carpeta") == D("7300")
    assert _cantidad(leido, "t", "Mezcla") == D("857.75")
    assert _cantidad(leido, "t·km", "Transporte") == D("10293")
    (transporte,) = [c for c in leido["cantidades"] if c["unidad"] == "t·km"]
    assert transporte["origen_id"] == "tramo:T1:capa:1"
    assert transporte["regla"] == "longitud*ancho*espesor*densidad*distancia"


def test_las_cantidades_no_pierden_cifras(ana) -> None:
    _guardar(ana, [TRAMO])
    leido = _leer(ana).json()
    assert all(isinstance(c["cantidad"], str) for c in leido["cantidades"])
    assert all(isinstance(v, str) for t in leido["tramos"] for v in (t["ancho_m"],))


def test_un_valor_que_no_es_decimal_es_422(ana) -> None:
    malo = {**TRAMO, "ancho_m": "siete"}
    r = _guardar(ana, [malo])
    assert r.status_code == 422, r.text
    assert "ancho_m" in r.text
    assert _filas_guardadas() == 0


def test_un_tramo_invertido_es_422_con_su_id(ana) -> None:
    r = _guardar(ana, [{**TRAMO, "progresiva_ini_km": "2", "progresiva_fin_km": "1"}])
    assert r.status_code == 422
    assert "T1" in r.json()["detalle"]
    assert _filas_guardadas() == 0


def test_la_coma_en_la_frontera_no_se_acepta(ana) -> None:
    r = _guardar(ana, [{**TRAMO, "ancho_m": "7,3"}])
    assert r.status_code == 422, r.text


def test_version_o_proyecto_inexistente_es_404(ana) -> None:
    assert _leer(ana, "XXX-001").status_code == 404
    navegador, _ = ana
    r = navegador.get(f"{RAIZ}/tramos", params={"proyecto": "No existe", "version": "VIV-001"})
    assert r.status_code == 404


def test_version_aprobada_da_409_y_no_se_edita(ana) -> None:
    assert _guardar(ana, [TRAMO]).status_code == 200
    ruta = config.carpeta_casos() / "vivienda.db"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            envio = aprobaciones.enviar(s, OBRA, "VIV-001", nota="ok", usuario=ANA, ahora=MARTES)
            aprobaciones.dictaminar(
                s, envio.id, resultado="aprobada", notas="", usuario="Rita <rita>", ahora=MARTES
            )
    finally:
        motor.dispose()
    dependencias.cerrar_motores()
    leido = _leer(ana).json()
    assert leido["editable"] is False
    assert leido["bloqueo"].startswith("La versión VIV-001 está aprobada")
    r = _guardar(ana, [])
    assert r.status_code == 409, r.text
    assert r.json()["detalle"] == leido["bloqueo"]
    assert _importar(ana, MUESTRA.read_bytes()).status_code == 409
    assert _filas_guardadas() == 1
    assert [t["id"] for t in _leer(ana).json()["tramos"]] == ["T1"]


def test_importar_csv(ana) -> None:
    r = _importar(ana, MUESTRA.read_bytes(), "via_ficticia.csv")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert [t["id"] for t in cuerpo["tramos"]] == ["T1", "T2", "T3"]
    assert cuerpo["tramos"][0]["ancho_m"] == "7.30"
    assert cuerpo["guardado"]["fuente"] == "Importado de via_ficticia.csv"
    assert _leer(ana).json() == cuerpo


def test_importar_csv_con_fila_mala_no_guarda_nada(ana) -> None:
    _guardar(ana, [TRAMO])
    malo = MUESTRA.read_text(encoding="utf-8").replace("T2;1,2;2,0;6,50", "T2;2,0;1,2;6,50")
    r = _importar(ana, malo.encode("utf-8"), "via_mala.csv")
    assert r.status_code == 422, r.text
    assert "fila 7" in r.json()["detalle"]
    assert _filas_guardadas() == 1  # sigue el guardado de antes
    assert [t["id"] for t in _leer(ana).json()["tramos"]] == ["T1"]


def test_importar_un_archivo_que_no_es_csv_es_415(ana) -> None:
    r = _importar(ana, b"x", "via.xlsx")
    assert r.status_code == 415, r.text


def test_importar_un_archivo_enorme_es_413(ana) -> None:
    r = _importar(ana, b"a" * (2 * 1024 * 1024 + 1), "via.csv")
    assert r.status_code == 413, r.text


def test_obras_con_tramos(ana) -> None:
    navegador, _ = ana
    assert navegador.get(f"{RAIZ}/obras").json() == {"obras": []}
    _guardar(ana, [TRAMO])
    obras = navegador.get(f"{RAIZ}/obras").json()["obras"]
    assert len(obras) == 1 and isinstance(obras[0], int)


def test_la_clave_de_api_no_escribe(ana) -> None:
    r = cliente_con_clave().put(
        f"{RAIZ}/tramos", params=_params(), json={"tramos": [], "fuente": ""}
    )
    assert r.status_code == 403
    assert r.json()["detalle"] == SOLO_CUENTA
    r = cliente_con_clave().post(
        f"{RAIZ}/tramos/importar",
        params=_params(),
        files={"archivo": ("via.csv", MUESTRA.read_bytes(), "text/csv")},
    )
    assert r.status_code == 403


def test_rita_no_edita(ana) -> None:
    rita, ficha = con_cuenta(app, "rita")
    r = rita.put(
        f"{RAIZ}/tramos",
        params=_params(),
        json={"tramos": [], "fuente": ""},
        headers=protegida(ficha),
    )
    assert r.status_code == 403
    assert r.json()["detalle"] == MENSAJE_PERMISO
