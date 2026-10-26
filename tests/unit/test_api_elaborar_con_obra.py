"""Elaborar valora con la lista de la obra elegida (Tarea 12 del plan de montar un presupuesto).

`POST /presupuestos/calcular` gana `proyecto` (opcional, el código o el nombre de la obra): con él,
`elaborar_desde_catalogo` valora con `lista_para_el_proyecto` (la lista para armar de la carpeta o,
si la obra está en la otra moneda, su conversión con la tasa del BCV) y el presupuesto sale en la
moneda de esa lista, la de la obra; así lo que se ve en Elaborar es lo que la Hoja valorará al
llevarlo. Sigue sin guardar nada: la conversión se deshace al terminar. Sin `proyecto`, como antes
(`tests/integration/test_api_ola2_elaborar.py`).

Datos FICTICIOS: la carpeta en Bs de `tests/fixtures/carpeta_bs_con_obras.py`. Oráculo: el APU de
OBRA-04 (material 12,00, equipo 5,00 y jornal 9,00 Bs) convertido A MANO con la tasa 40,00
(0,3; 0,125 y 0,225 USD) y calculado con el motor de costos del núcleo (`calcular_apu`, la fuente
del precio unitario), con los parámetros de costo por omisión, a dos decimales.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import caso_web, dependencias
from api.rutas import presupuestos as rutas_presupuestos
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.costing.motor import calcular_apu
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from operacion import config
from tests.fixtures.app_de_prueba import app_con
from tests.fixtures.carpeta_aprobaciones import COMPOSICIONES
from tests.fixtures.carpeta_bs_con_obras import CASA_USD, VIVIENDA, carpeta_en_bs
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

APP = app_con(rutas_presupuestos.router)
RUTA = "/presupuestos/calcular"
D = Decimal
CENTINELA = "VALOR-CENTINELA"
SIN_TASA = "No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar."
SIN_OBRA = "Esa obra no está en esta carpeta de trabajo: elíjala de nuevo en el selector de obra."

#: OBRA-04 con sus precios en Bs divididos A MANO entre 40,00 Bs/USD.
OBRA_04_EN_USD = ComposicionAPU(
    codigo_partida="OBRA-04",
    descripcion="Paredes de bloque de arcilla",
    unidad="m2",
    rendimiento=D("10"),
    materiales=(LineaMaterial("Material de OBRA-04", "m2", D("1"), D("0.3")),),
    equipos=(LineaEquipo("Equipo de OBRA-04", D("1"), D("0.125"), D("1")),),
    mano_obra=(LineaManoObra("Obrero", D("2"), D("0.225")),),
)


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("api_elaborar_con_obra")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "bs": carpeta_en_bs(carpeta / "bs.db", con_tasa=False),
        "bs_con_tasa": carpeta_en_bs(carpeta / "bs_con_tasa.db", con_tasa=True),
    }


@pytest.fixture(autouse=True)
def _entorno(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["bs_con_tasa"], ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _poner(origen: Path) -> Path:
    dependencias.cerrar_motores()
    ruta = config.ruta_caso_por_defecto()
    shutil.copyfile(origen, ruta)
    return ruta


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _codigo_de(ruta: Path, nombre: str) -> str:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        ((id_,),) = bd.execute("SELECT id FROM proyecto WHERE nombre = ?", (nombre,)).fetchall()
    return str(id_)


def _calcular(navegador: TestClient, ficha: str, moneda: str, **extra):
    cuerpo = {
        "codigo": "P-001",
        "fecha": "2026-10-25",
        "moneda": moneda,
        "items": [
            {
                "codigo_partida": "OBRA-04",
                "descripcion": "Paredes de bloque de arcilla",
                "unidad": "m2",
                "cantidad": "10",
                "origen_id": "FILA-1",
                "origen_tipo": "tabular",
                "dominio": "civil",
            }
        ],
        **extra,
    }
    return navegador.post(RUTA, json=cuerpo, headers=protegida(ficha))


def _a_dos(valor: Decimal) -> str:
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def test_con_una_obra_en_usd_en_carpeta_bs_valora_con_la_lista_convertida_y_no_guarda(
    _entorno: Path,
) -> None:
    navegador, ficha = con_cuenta(APP, "ana")
    antes = _volcado(_entorno)

    respuesta = _calcular(navegador, ficha, "Bs", proyecto=_codigo_de(_entorno, CASA_USD))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["moneda"] == "USD"
    ((partida,),) = [[p] for p in cuerpo["partidas"]]
    esperado = calcular_apu(OBRA_04_EN_USD, ParametrosCosto()).precio_unitario
    assert partida["precio_unitario"] == _a_dos(esperado)
    assert _volcado(_entorno) == antes  # la conversión no queda escrita


def test_con_una_obra_en_la_moneda_de_la_carpeta_valora_con_su_lista_y_su_moneda() -> None:
    navegador, ficha = con_cuenta(APP, "ana")

    respuesta = _calcular(navegador, ficha, "USD", proyecto=VIVIENDA)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["moneda"] == "Bs"
    esperado = calcular_apu(COMPOSICIONES["OBRA-04"], ParametrosCosto()).precio_unitario
    assert [p["precio_unitario"] for p in cuerpo["partidas"]] == [_a_dos(esperado)]


def test_sin_tasa_una_obra_en_usd_es_409_con_el_texto_de_la_tasa(_casos: dict[str, Path]) -> None:
    ruta = _poner(_casos["bs"])
    navegador, ficha = con_cuenta(APP, "ana")
    antes = _volcado(ruta)

    respuesta = _calcular(navegador, ficha, "USD", proyecto=CASA_USD)

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": SIN_TASA}
    assert _volcado(ruta) == antes


def test_una_obra_que_no_existe_es_404_sin_eco() -> None:
    navegador, ficha = con_cuenta(APP, "ana")

    respuesta = _calcular(navegador, ficha, "USD", proyecto=CENTINELA)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detalle": SIN_OBRA}
    assert CENTINELA not in respuesta.text


def test_sin_obra_conserva_la_moneda_que_se_pide() -> None:
    navegador, ficha = con_cuenta(APP, "ana")

    respuesta = _calcular(navegador, ficha, "USD")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["moneda"] == "USD"
