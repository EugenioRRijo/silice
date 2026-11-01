"""Llevar los tramos a una obra que YA existe: cada partida debe poder valorarse. FICTICIO.

Reproduce el bloqueo de la pasada de navegador del 31/10/2026 (carpeta de demostración, DEMO-001):
llevar respondía 200 («Se llevaron 20 renglones») porque solo miraba que la partida estuviera en el
catálogo, pero la Hoja valora cada APU con la lista de la VERSIÓN abierta y a la fecha de esa
versión (`hoja_edicion._completar` → `hoja.completar_composiciones`, que calla el
`CatalogoIncompleto`). Si el APU se compuso en Componer en otra fecha, sus precios quedaron en la
lista de esa fecha y su rendimiento con esa fecha: la Hoja no lo puede valorar y los 20 renglones
quedan PENDIENTE, «sin composición de APU», sin decir por qué.

La obra es la «Vivienda Demo 80 m2» (`tests/fixtures/carpeta_aprobaciones.py`): VIV-002 sobre
«Lista Bs de prueba», al 01/10/2026. Las 15 partidas viales se componen POR LA API de Componer
(`POST /v1/composicion/guardar`), como lo haría una persona, con un material cada una:

- con fecha 31/10/2026 (hoy): los precios van a una lista derivada de esa fecha y el rendimiento
  queda al 31/10: llevar debe responder 409, decir qué partidas, qué insumos y en qué lista
  faltan, y no llevar nada;
- con fecha 01/10/2026 (la de la versión): los precios van a «Lista Bs de prueba» y el
  rendimiento a esa fecha: llevar da 200 y la auditoría de la Hoja no tiene ningún PENDIENTE (es
  lo que Eugenio prepara para mostrar Llevar en una carpeta existente).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.main import app
from api.rutas import hoja as rutas_hoja
from api.rutas import vial as rutas
from aplicacion import hoja_borradores
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.carpeta_aprobaciones import FECHA, OBRA, guardar_version, sembrar_vivienda
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

ANA = "Ana <ana>"
MARTES = datetime(2026, 10, 20, 10, 30)
HOY = date(2026, 10, 31)
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"

#: Las 15 partidas viales (código, descripción, unidad) de `data/samples/vial/README.md`.
PARTIDAS = (
    ("C-000.000.001", "Fresado de pavimento asfáltico", "m3"),
    ("C-000.000.002", "Base granular compactada", "m3"),
    ("C-000.000.003", "Sub-base granular compactada", "m3"),
    ("C-000.000.004", "Riego de imprimación", "m2"),
    ("C-000.000.005", "Ligante del riego de imprimación", "l"),
    ("C-000.000.006", "Riego de adherencia", "m2"),
    ("C-000.000.007", "Ligante del riego de adherencia", "l"),
    ("C-000.000.008", "Carpeta de concreto asfáltico", "m2"),
    ("C-000.000.009", "Mezcla asfáltica de la carpeta", "t"),
    ("C-000.000.010", "Bacheo con mezcla asfáltica", "m3"),
    ("C-000.000.011", "Mezcla asfáltica del bacheo", "t"),
    ("C-000.000.012", "Demarcación con línea continua", "m"),
    ("C-000.000.013", "Demarcación con línea discontinua", "m"),
    ("C-000.000.014", "Transporte de mezcla asfáltica desde la planta", "t·km"),
    ("C-000.000.015", "Pintura de demarcación", "l"),
)


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_vial_valorable")
    ruta = carpeta / "via.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as s:
            obra = sembrar_vivienda(s, usuario=ANA)
            guardar_version(s, obra, "VIV-002", usuario=ANA)
    finally:
        motor.dispose()
    return {"instalacion": plantilla_con_cuentas(carpeta), "via.db": ruta}


@pytest.fixture(autouse=True)
def _entorno(_plantillas: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / "via.db").write_bytes(_plantillas["via.db"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    hoja_borradores.olvidar_todo()
    monkeypatch.setattr(rutas, "ahora", lambda: MARTES)
    monkeypatch.setattr(rutas, "_hoy", lambda: HOY)
    monkeypatch.setattr(rutas_hoja, "_hoy", lambda: HOY)
    yield
    hoja_borradores.olvidar_todo()
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def ana() -> tuple[TestClient, str]:
    navegador, ficha = con_cuenta(app, "ana")
    elegida = navegador.post("/v1/casos/actual", json={"nombre": "via.db"}, headers=protegida(ficha))
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


def _componer(cuenta, fecha: date) -> None:
    """Las 15 partidas viales por Componer, con un material inventado cada una, a `fecha`."""
    navegador, ficha = cuenta
    for codigo, descripcion, unidad in PARTIDAS:
        respuesta = navegador.post(
            "/v1/composicion/guardar",
            json={
                "codigo": codigo,
                "descripcion": descripcion,
                "unidad": unidad,
                "dominio": "civil",
                "rendimiento": "10",
                "fecha": fecha.isoformat(),
                "condiciones": "Obra vial ficticia de la prueba",
                "materiales": [
                    {
                        "descripcion": f"Material vial {codigo} (ficticio)",
                        "unidad": unidad,
                        "cantidad": "1",
                        "precio": "3",
                    }
                ],
            },
            headers=protegida(ficha),
        )
        assert respuesta.status_code == 200, respuesta.text


def _importar_y_llevar(cuenta):
    navegador, ficha = cuenta
    importado = navegador.post(
        "/v1/vial/tramos/importar",
        params={"proyecto": OBRA, "version": "VIV-002"},
        files={"archivo": ("via.csv", MUESTRA.read_bytes(), "text/csv")},
        headers=protegida(ficha),
    )
    assert importado.status_code == 200, importado.text
    return navegador.post(
        "/v1/vial/tramos/llevar",
        json={"proyecto": OBRA, "version": "VIV-002"},
        headers=protegida(ficha),
    )


def _borradores(navegador: TestClient) -> list[dict]:
    respuesta = navegador.get("/v1/hoja/borradores")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["borradores"]


def test_apu_compuestos_en_otra_fecha_dan_409_con_partidas_insumos_y_lista(ana) -> None:
    """El caso de la pasada de navegador: compuestos hoy, la versión es del 01/10/2026."""
    assert HOY != FECHA
    _componer(ana, HOY)

    respuesta = _importar_y_llevar(ana)

    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"
    detalle = respuesta.json()["detalle"]
    assert "No se llevó nada" in detalle
    assert "«Lista Bs de prueba»" in detalle  # la lista de la versión, la que usa la Hoja
    assert "VIV-002" in detalle and "01/10/2026" in detalle
    for codigo, _descripcion, _unidad in PARTIDAS:
        assert f"«{codigo}»" in detalle
    assert "Material vial C-000.000.009 (ficticio)" in detalle  # qué insumo falta
    assert "31/10/2026" in detalle  # dónde están sus precios (la lista derivada de hoy)
    assert "Componer" in detalle  # qué hacer
    assert _borradores(ana[0]) == []  # nada llevado: ni siquiera un borrador abierto


def test_apu_compuestos_a_la_fecha_de_la_version_se_llevan_y_no_quedan_pendientes(ana) -> None:
    """Lo que Eugenio prepara: componer las partidas con la fecha de la versión."""
    navegador, _ = ana
    _componer(ana, FECHA)

    respuesta = _importar_y_llevar(ana)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["renglones"] == 20
    id_ = respuesta.json()["borrador_id"]
    informe = navegador.get(f"/v1/hoja/borradores/{id_}/vistas/auditoria")
    assert informe.status_code == 200, informe.text
    pendientes = [h for h in informe.json()["hallazgos"] if h["regla"] == "PENDIENTE"]
    assert pendientes == []
