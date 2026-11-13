"""La pestaña APU de la Hoja muestra el desperdicio de cada material (F5 vial, punto 1).

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §4 (opción B) y §13,
«Lo que falta»: Componer ya guarda la cantidad con desperdicio y su traza (la neta y el
porcentaje); la Hoja la mostraba solo como la cantidad. `GET /v1/hoja/borradores/{id}/vistas/apu`
devuelve ahora, en `detalle.desperdicios`, la fila de Materiales y el texto «neta + porcentaje»
de cada línea cuya descripción, unidad y cantidad son las de la traza vigente de la partida.

Solo lectura: quien revisa también lo ve, y leerlo no escribe en la base del caso.

Datos FICTICIOS (la obra OF-001). Oráculo a mano: la llave de AF-LLAVE lleva 1 pieza; una traza
de 0,8 piezas con 25 % de desperdicio da 0,8 × 1,25 = 1, la misma cantidad.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from api import caso_web, dependencias
from api.main import app
from aplicacion.desperdicio import TrazaDesperdicio, guardar_trazas
from core.catalog import abrir_sesion, crear_motor
from operacion import config
from operacion.base_datos import preparar_base
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from tests.fixtures.sesion_web import (
    con_cuenta,
    copiar_instalacion,
    plantilla_con_cuentas,
    protegida,
)

D = Decimal
LLAVE = "Llave de paso de bola PVC 1/2 pulg [PLOG26]"


@pytest.fixture(scope="module")
def _casos(tmp_path_factory) -> dict[str, Path]:
    carpeta = tmp_path_factory.mktemp("hoja_desperdicio")
    return {
        "instalacion": plantilla_con_cuentas(carpeta),
        "of001": plantilla_of001(carpeta / "of001.db"),
    }


@pytest.fixture(autouse=True)
def _caso(_casos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.delenv(dependencias.VARIABLE_BASE, raising=False)
    copiar_instalacion(_casos["instalacion"])
    ruta = config.ruta_caso_por_defecto()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_casos["of001"], ruta)
    preparar_base(ruta)
    caso_web.olvidar_todo()
    yield ruta
    caso_web.olvidar_todo()
    dependencias.cerrar_motores()


def _con_traza(ruta: Path, traza: TrazaDesperdicio) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            guardar_trazas(sesion, "AF-LLAVE", [traza], ahora=datetime(2026, 11, 13, 9))
            sesion.commit()
    finally:
        motor.dispose()


def _volcado(ruta: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)) as bd:
        tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: sorted(bd.execute(f'SELECT * FROM "{t}"').fetchall(), key=repr) for t in tablas}


def _detalle(login: str) -> dict:
    navegador, ficha = con_cuenta(app, login)
    abierto = navegador.post(
        "/v1/hoja/borradores",
        json={"proyecto": NOMBRE_OF001, "version": "001"},
        headers=protegida(ficha),
    )
    assert abierto.status_code == 201, abierto.text
    vista = navegador.get(
        f"/v1/hoja/borradores/{abierto.json()['id']}/vistas/apu", params={"partida": "AF-LLAVE"}
    )
    assert vista.status_code == 200, vista.text
    return vista.json()["detalle"]


def test_sin_traza_no_hay_desperdicios(_caso: Path) -> None:
    assert _detalle("ana")["desperdicios"] == []


def test_la_linea_con_traza_trae_su_neta_y_su_porcentaje(_caso: Path) -> None:
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    detalle = _detalle("ana")
    assert detalle["desperdicios"] == [{"fila": 1, "texto": "0,8 + 25 %"}]
    assert detalle["grupos"][0]["filas"][0]["cantidad"] == "1"


def test_una_traza_de_otra_cantidad_no_se_muestra(_caso: Path) -> None:
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("1"), D("4"), D("1.04")))
    assert _detalle("ana")["desperdicios"] == []


def test_quien_revisa_lo_ve_sin_escribir_en_la_base(_caso: Path) -> None:
    # quien arma abre la versión una vez (la prepara: UC-15e); después revisa solo lee
    _detalle("ana")
    _con_traza(_caso, TrazaDesperdicio(LLAVE, "pieza", D("0.8"), D("25"), D("1.000")))
    antes = _volcado(_caso)
    assert _detalle("rita")["desperdicios"] == [{"fila": 1, "texto": "0,8 + 25 %"}]
    assert _volcado(_caso) == antes
