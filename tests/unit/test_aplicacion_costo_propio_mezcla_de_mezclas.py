"""Una mezcla que lleva otra mezcla producida el mismo mes (tanda 2026-11-19, hueco declarado en la
prueba en vivo del 2026-11-18): el costo por tonelada calcula primero la componente.

Datos FICTICIOS: la planta de noviembre de `tests/fixtures/costo_propio.py` (`AGR-12` y `AGR-34` a
5 USD/t: cantera 1.000 / 200 t; `MZ-1` con `RECETA_A`) mas mezclas nuevas cuyos codigos van ANTES
de `MZ-1` en el orden alfabetico, que es el orden en que hoy se recorren. Oraculos a mano:

- `AA-0` (0,5 t de `MZ-1` propio + 0,5 t de `AGR-34` propio), 50 t el 15/11. La planta (1.200)
  se reparte entre 150 t de mezcla: 8/t. `MZ-1` = 0,94 x 5 + 0,05 x 600 + 8 x 0,5 + 8 = 46,70;
  `AA-0` = 0,5 x 46,70 + 0,5 x 5 + 8 = 23,35 + 2,50 + 8 = 33,85.
- Cadena `AA-0` -> `AB-0` -> `MZ-1`: `AB-0` (0,5 t de `MZ-1` + 0,5 t de `AGR-34`), 40 t;
  `AA-0` (0,5 t de `AB-0` + 0,5 t de `AGR-34`), 60 t. Planta 1.200 / 200 t = 6. `MZ-1` = 4,70 +
  30 + 4 + 6 = 44,70; `AB-0` = 22,35 + 2,50 + 6 = 30,85; `AA-0` = 15,425 + 2,50 + 6 = 23,925.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from aplicacion.costo_propio import calcular_periodo
from produccion.inventario import crear_material
from produccion.receta import Componente, producir_con_receta, registrar_receta
from tests.fixtures import costo_propio as cp

D = Decimal


@pytest.fixture
def ins() -> Iterator[Session]:
    with cp.instalacion_en_memoria() as sesion:
        yield sesion


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    with cp.carpeta_del_caso(tmp_path) as sesion:
        yield sesion


def _mezcla(ins: Session, codigo: str, de: str, toneladas: str, dia: int) -> None:
    """La mezcla `codigo`: 0,5 t de la mezcla `de` y 0,5 t de `AGR-34`, producida el `dia`/11."""
    crear_material(ins, codigo=codigo, nombre=codigo, unidad_venta="t", existencia_minima=D(0))
    registrar_receta(
        ins,
        codigo,
        (Componente(de, D("0.5"), "t", "propio"), Componente("AGR-34", D("0.5"), "t", "propio")),
        fuente="dosificacion ficticia",
        vigente_desde=cp.OCTUBRE,
        usuario=cp.USUARIO,
        ahora=cp.AHORA,
    )
    producir_con_receta(ins, codigo, D(toneladas), cp.dia(dia), usuario=cp.USUARIO, ahora=cp.AHORA)


def test_la_mezcla_que_lleva_otra_mezcla_del_mes_la_calcula_primero(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    _mezcla(ins, "AA-0", "MZ-1", "50", 15)
    calculo = calcular_periodo(ins, caso, cp.PERIODO, "USD", usuario=cp.USUARIO, ahora=cp.AHORA)
    assert calculo.por_tonelada == {
        "AGR-12": D("5"),
        "AGR-34": D("5"),
        "MZ-1": D("46.70"),
        "AA-0": D("33.85"),
    }
    # el costo de MZ-1 es el de este mes, no el de otro calculo
    assert json.loads(calculo.instantanea)["entradas"]["de_otro_calculo"] == {}


def test_una_cadena_de_mezclas_se_calcula_de_la_hoja_a_la_raiz(ins, caso) -> None:
    cp.noviembre_usd(ins, caso)
    _mezcla(ins, "AB-0", "MZ-1", "40", 15)
    _mezcla(ins, "AA-0", "AB-0", "60", 20)
    calculo = calcular_periodo(ins, caso, cp.PERIODO, "USD", usuario=cp.USUARIO, ahora=cp.AHORA)
    assert calculo.por_tonelada["MZ-1"] == D("44.70")
    assert calculo.por_tonelada["AB-0"] == D("30.85")
    assert calculo.por_tonelada["AA-0"] == D("23.925")
