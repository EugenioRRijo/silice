"""AppTest de la moneda en Parametros y del origen/erosion en Precios (S1, Tarea 10).

Misma base de OF-001 que `test_ui_hoja.py`, copiada a `tmp_path`. La conversion usa la tasa del BCV
de **hoy** (la pantalla evalua a `date.today()`), asi que la prueba la registra con esa fecha.
"""

from __future__ import annotations

import importlib
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_motor
from core.catalog.indices import Observacion, definicion_tasa, registrar_importacion
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from ui.paginas.hoja import CLAVE_PESTANA, CLAVE_PROYECTO

SCRIPT = "from ui.paginas.hoja import render\nrender()\n"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("ui_moneda") / "of001.db")


@pytest.fixture
def base(_plantilla, tmp_path):
    copia = tmp_path / "of001.db"
    shutil.copy(_plantilla, copia)
    return copia


def _tasa_de_hoy(base: Path) -> None:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            registrar_importacion(
                sesion,
                definicion_tasa("venta"),
                [Observacion(date.today(), Decimal("860.18"))],
                archivo="FUENTE.md",
                huella="f" * 64,
                fuente="https://www.bcv.org.ve/",
                fecha_descarga=date.today(),
                responsable="Admin",
                filas_leidas=1,
                filas_rechazadas=0,
            )
            sesion.commit()
    finally:
        motor.dispose()


def _abrir(monkeypatch, base: Path, pestana: str) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_PROYECTO] = NOMBRE_OF001
    at.session_state[CLAVE_PESTANA] = pestana
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _convertir(at: AppTest) -> AppTest:
    next(t for t in at.text_input if t.label == "Por que se cambia la moneda (fuente)").set_value(
        "cambio de moneda del contrato"
    )
    next(t for t in at.text_input if t.label == "Responsable del cambio").set_value("Ing. Prueba")
    next(b for b in at.button if b.label == "Convertir la version").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _versiones(base: Path) -> list[str]:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return sorted(sesion.scalars(select(models.Presupuesto.codigo)))
    finally:
        motor.dispose()


def test_parametros_muestra_la_moneda_del_proyecto(monkeypatch, base):
    at = _abrir(monkeypatch, base, "Parámetros")
    assert any("Moneda del proyecto" in m.value for m in at.markdown)
    assert any(b.label == "Convertir la version" for b in at.button)


def test_convertir_sin_tasa_reciente_lo_dice_y_no_escribe(monkeypatch, base):
    antes = _versiones(base)
    at = _convertir(_abrir(monkeypatch, base, "Parámetros"))
    assert any("No se convirtio nada" in e.value for e in at.error), [e.value for e in at.error]
    assert _versiones(base) == antes


def test_convertir_con_tasa_de_hoy_crea_una_version_nueva(monkeypatch, base):
    _tasa_de_hoy(base)
    antes = _versiones(base)
    at = _convertir(_abrir(monkeypatch, base, "Parámetros"))
    assert not at.error, [e.value for e in at.error]
    despues = _versiones(base)
    assert len(despues) == len(antes) + 1 and set(antes) <= set(despues)


def test_precios_muestra_origen_y_erosion(monkeypatch, base):
    at = _abrir(monkeypatch, base, "Precios")
    tabla = next(d.value for d in at.dataframe if "Referencia" in d.value.columns)
    esperadas = {
        "Moneda original",
        "Precio original",
        "Fuente de la tasa",
        "Fuente",
        "Propio/heredado",
        "Erosion USD",
        "Erosion Bs",
        "Erosion %",
        "Erosion por indice",
        "Estado",
    }
    assert esperadas <= set(tabla.columns)
