"""`GET /v1/vial/reportes/{tipo}`: cómputos, APU con origen, costo de producción y resumen con IVA
(Tarea 21 del plan vial). Datos FICTICIOS.

La carpeta es `vivienda.db` (la «Vivienda Demo 80 m2», VIV-002, de `tests/fixtures/
carpeta_aprobaciones.py`); los tramos son los de `data/samples/vial/via_ficticia.csv` (T1: mezcla de
la carpeta 1.200 x 7,30 x 0,05 x 2,35 = 1.029,3 t) y el costo de producción es el de noviembre de
2026 en USD de `tests/fixtures/costo_propio.py` (`AGR-12` a 5 USD/t, `MZ-1` a 50,70). El resumen
compara con el motor (`calcular_apu`) sobre las composiciones del fixture: subtotal = suma de
cantidad x precio unitario, IVA 16 %. Mismo acceso que las vecinas de `/v1/vial`: `editar_hoja`
(arma); rita 403; sin sesión 401.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from api import caso_web, dependencias
from api.main import app
from aplicacion.costo_propio import calcular_periodo
from core.catalog import abrir_sesion, crear_motor
from core.costing import calcular_apu
from operacion import config
from operacion.base_datos import preparar_base
from operacion.instalacion import sesion_de_instalacion
from tests.fixtures import costo_propio as cp
from tests.fixtures.carpeta_aprobaciones import (
    COMPOSICIONES,
    OBRA,
    PARAMETROS,
    PARTIDAS,
    guardar_version,
    sembrar_vivienda,
)
from tests.fixtures.sesion_web import (
    cliente,
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
ANA = "Ana <ana>"
MUESTRA = Path(__file__).resolve().parents[2] / "data" / "samples" / "vial" / "via_ficticia.csv"
RAIZ = "/v1/vial/reportes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MEZCLA = "C-000.000.009"


@pytest.fixture(scope="module")
def _plantillas(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("plantillas_reportes_viales")
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
def _entorno(_plantillas, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_plantillas["instalacion"])
    casos = config.carpeta_casos()
    casos.mkdir(parents=True, exist_ok=True)
    (casos / "vivienda.db").write_bytes(_plantillas["vivienda.db"].read_bytes())
    dependencias.cerrar_motores()
    caso_web.olvidar_todo()
    yield
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


@pytest.fixture
def calculo() -> int:
    """El cálculo de noviembre de 2026 (USD), en la instalación y la carpeta de la prueba."""
    motor = crear_motor(f"sqlite:///{(config.carpeta_casos() / 'vivienda.db').as_posix()}")
    try:
        with abrir_sesion(motor) as caso, sesion_de_instalacion() as ins:
            cp.noviembre_usd(ins, caso)
            guardado = calcular_periodo(ins, caso, cp.PERIODO, "USD", usuario="ana", ahora=cp.AHORA)
            caso.commit()
            ins.commit()
            return guardado.id
    finally:
        motor.dispose()


@pytest.fixture
def ana() -> tuple[TestClient, str]:
    navegador, ficha = con_cuenta(app, "ana")
    elegida = navegador.post(
        "/v1/casos/actual", json={"nombre": "vivienda.db"}, headers=protegida(ficha)
    )
    assert elegida.status_code == 200, elegida.text
    return navegador, ficha


def _con_tramos(cuenta) -> None:
    navegador, ficha = cuenta
    r = navegador.post(
        "/v1/vial/tramos/importar",
        params={"proyecto": OBRA, "version": "VIV-002"},
        files={"archivo": ("via.csv", MUESTRA.read_bytes(), "text/csv")},
        headers=protegida(ficha),
    )
    assert r.status_code == 200, r.text


def _pedir(cuenta, tipo: str, **params):
    base = {"proyecto": OBRA, "version": "VIV-002"}
    return cuenta[0].get(f"{RAIZ}/{tipo}", params={**base, **params})


def _libro(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    return load_workbook(BytesIO(respuesta.content))


def _filas(libro, hoja: str) -> list[tuple]:
    assert hoja in libro.sheetnames, libro.sheetnames
    return [f for f in libro[hoja].iter_rows(values_only=True) if any(f)]


def test_computos_con_las_cantidades_de_la_muestra(ana) -> None:
    _con_tramos(ana)
    r = _pedir(ana, "computos")
    libro = _libro(r)
    assert r.headers["content-type"] == XLSX
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["content-disposition"].startswith('attachment; filename="computos_')
    assert libro.sheetnames == ["Portada", "Tramos", "Cómputos por tramo", "Totales por partida"]
    datos = _filas(libro, "Cómputos por tramo")[1:]
    assert len(datos) == 20
    assert {(f[0], f[1]): D(str(f[4])) for f in datos}[("T1", MEZCLA)] == D("1029.3")


def test_computos_de_una_version_sin_tramos_422_llano(ana) -> None:
    r = _pedir(ana, "computos")
    assert r.status_code == 422, r.text
    assert "no tiene tramos" in r.json()["detalle"]


def test_resumen_con_iva_de_la_mano(ana) -> None:
    libro = _libro(_pedir(ana, "resumen"))
    subtotal = sum(
        (D(cantidad) * calcular_apu(COMPOSICIONES[codigo], PARAMETROS).precio_unitario)
        for codigo, _descripcion, _unidad, cantidad, *_ in PARTIDAS
    )
    esperado = subtotal.quantize(D("0.01"), ROUND_HALF_UP)
    iva = (subtotal * D("0.16")).quantize(D("0.01"), ROUND_HALF_UP)
    resumen = {f[0]: f[1] for f in _filas(libro, "Resumen")}
    assert D(str(resumen["Subtotal sin IVA"])) == esperado
    assert D(str(resumen["IVA (16 %)"])) == iva
    assert D(str(resumen["Total con IVA"])) == esperado + iva
    assert resumen["Moneda"] == "Bs"


def test_apu_con_origen_trae_las_seis_partidas(ana) -> None:
    libro = _libro(_pedir(ana, "apu"))
    assert libro.sheetnames == ["Portada", "Partidas", "APU con origen", "Conciliación"]
    assert len(_filas(libro, "Partidas")) == 1 + len(PARTIDAS)
    conceptos = {f[2] for f in _filas(libro, "APU con origen")[1:]}
    assert {f"Material de {p[0]}" for p in PARTIDAS} <= conceptos


def test_apu_con_origen_concilia_los_tramos_que_el_presupuesto_no_tiene(ana) -> None:
    """Con tramos guardados que el presupuesto no tiene, CV2 lo dice (ERROR, observado 0)."""
    _con_tramos(ana)
    texto = " ".join(str(c) for f in _filas(_libro(_pedir(ana, "apu")), "Conciliación") for c in f)
    assert "CV2" in texto


def test_costo_de_produccion_de_la_mano(ana, calculo) -> None:
    libro = _libro(_pedir(ana, "produccion", periodo=cp.PERIODO))
    assert libro.sheetnames[:3] == ["Portada", "Cálculos", "Costo por tonelada"]
    por_producto = {f[2]: (f[0], D(str(f[4]))) for f in _filas(libro, "Costo por tonelada")[1:]}
    assert por_producto["AGR-12"] == (calculo, D(5))
    assert por_producto["MZ-1"] == (calculo, D("50.70"))


def test_costo_de_produccion_de_un_periodo_sin_calculos_404(ana) -> None:
    r = _pedir(ana, "produccion", periodo="2026-01")
    assert r.status_code == 404, r.text
    assert "2026-01" in r.json()["detalle"]


def test_costo_de_produccion_sin_periodo_o_con_periodo_malo_422(ana) -> None:
    assert _pedir(ana, "produccion").status_code == 422
    assert _pedir(ana, "produccion", periodo="2026-13").status_code == 422


def test_tipo_desconocido_404(ana) -> None:
    assert _pedir(ana, "inventado").status_code == 404


def test_sin_obra_o_sin_version_422(ana) -> None:
    r = ana[0].get(f"{RAIZ}/computos", params={"version": "VIV-002"})
    assert r.status_code == 422, r.text
    r = ana[0].get(f"{RAIZ}/resumen", params={"proyecto": OBRA})
    assert r.status_code == 422, r.text


def test_version_que_no_existe_404(ana) -> None:
    assert _pedir(ana, "resumen", version="NO-EXISTE").status_code == 404


def test_rita_no_descarga(ana) -> None:
    rita, _ = con_cuenta(app, "rita")
    r = rita.get(f"{RAIZ}/resumen", params={"proyecto": OBRA, "version": "VIV-002"})
    assert r.status_code == 403, r.text


def test_sin_credenciales_401() -> None:
    r = cliente(app).get(f"{RAIZ}/resumen", params={"proyecto": OBRA, "version": "VIV-002"})
    assert r.status_code == 401
