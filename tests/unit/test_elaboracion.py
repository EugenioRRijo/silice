"""La orquestacion de la elaboracion fuera de la pagina de componer (INV-043, 11b y 11c).

`ui/elaboracion.py` no importa Streamlit: se prueba como funciones sobre una base en `tmp_path`
sembrada con `scripts.seed.sembrar` (la salvaguarda de `tests/conftest.py` vigila `data/apu.db`).
Los oraculos son la fixture de la linea base, no el nucleo que se orquesta.
"""

from __future__ import annotations

import dataclasses
import io
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pytest

from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from scripts.seed import sembrar
from tests.fixtures.apu_linea_base import FECHA_LINEA_BASE, MONEDA, TOTAL_EXACTO_LINEA_BASE
from tests.fixtures.computo_auditado import items_auditados
from ui.elaboracion import elaborar_desde_catalogo, items_desde_filas, libro_excel


@pytest.fixture(scope="module")
def base_sembrada(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("elaboracion") / "caso.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return base


@contextmanager
def _catalogo(base: Path) -> Iterator[Catalogo]:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            yield Catalogo(sesion)
    finally:
        motor.dispose()


# --- items_desde_filas ------------------------------------------------------------------------


def _filas_y_partidas():
    """Las filas de la tabla de cantidades y las partidas que las respaldan, desde la fixture.

    Las partidas son dobles con los atributos que lee `items_desde_filas` (descripcion, unidad y
    dominio de `models.Partida`), tomados del propio item: asi el oraculo es la fixture.
    """
    items = items_auditados()
    filas = [
        {
            "codigo_partida": item.codigo_partida,
            "cantidad": str(item.cantidad),
            "origen_id": item.origen_id,
        }
        for item in items
    ]
    partidas = {
        item.codigo_partida: SimpleNamespace(
            descripcion=item.descripcion, unidad=item.unidad, dominio=str(item.dominio)
        )
        for item in items
    }
    return items, filas, partidas


def test_las_filas_del_computo_auditado_dan_sus_items_sin_avisos() -> None:
    items, filas, partidas = _filas_y_partidas()
    obtenidos, avisos = items_desde_filas(filas, partidas)
    # La tabla de cantidades no captura especificaciones: el item manual no las trae.
    assert obtenidos == [dataclasses.replace(item, especificaciones={}) for item in items]
    assert avisos == []


def test_una_fila_con_la_cantidad_vacia_da_un_aviso_que_cita_su_fila() -> None:
    _, filas, partidas = _filas_y_partidas()
    filas[1] = {**filas[1], "cantidad": ""}
    obtenidos, avisos = items_desde_filas(filas, partidas)
    assert len(obtenidos) == len(filas) - 1
    assert len(avisos) == 1
    assert avisos[0].startswith("cantidades de obra, fila 2:")


def test_una_fila_en_blanco_no_es_un_aviso() -> None:
    _, _, partidas = _filas_y_partidas()
    blanca = {"codigo_partida": None, "cantidad": "nan", "origen_id": ""}
    assert items_desde_filas([blanca], partidas) == ([], [])


# --- elaborar_desde_catalogo ------------------------------------------------------------------


def test_elaborar_la_linea_base_da_el_total_de_la_fixture(base_sembrada: Path) -> None:
    with _catalogo(base_sembrada) as catalogo:
        resultado = elaborar_desde_catalogo(
            catalogo, items_auditados(), "P-001", FECHA_LINEA_BASE, MONEDA
        )
    assert resultado.presupuesto.total == TOTAL_EXACTO_LINEA_BASE
    assert resultado.presupuesto.codigo == "P-001"


# --- libro_excel ------------------------------------------------------------------------------


def test_el_libro_se_abre_y_tiene_la_hoja_de_auditoria(base_sembrada: Path) -> None:
    with _catalogo(base_sembrada) as catalogo:
        resultado = elaborar_desde_catalogo(
            catalogo, items_auditados(), "P-001", FECHA_LINEA_BASE, MONEDA
        )
    libro, nombre = libro_excel(resultado)
    assert nombre.endswith(".xlsx")
    assert "Auditoria" in openpyxl.load_workbook(io.BytesIO(libro)).sheetnames
