"""`aplicacion/estilo.py` (PLAN_SILICE_UI, tarea 1; RU-1: sin prueba hasta la auditoría final,
2026-10-13).

* Los formatos redondean a la mitad hacia arriba solo al presentar (NORMAS.md §2) y dicen «no
  disponible» ante `None`; las fronteras se escriben a mano (x,xx5 sube; x,xx49 baja).
* La paleta es una sola copia: los rubros y las series son exactamente los que arma
  `aplicacion.tablero`.
* `aplicacion/estilo.py` y `aplicacion/tablero.py` no importan Streamlit ni pandas (restricción
  global del plan).

Retiro de Streamlit (F4): se fueron con `ui/graficos.py` y `.streamlit/config.toml` las pruebas de
los gráficos de Altair y del tema de Streamlit.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from aplicacion import estilo
from tests.fixtures.arquitectura import RAIZ, importaciones

D = Decimal


# --- aplicacion/estilo.py -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (D("1234.565"), "1234.57 USD"),  # la mitad sube (ROUND_HALF_UP)
        (D("1234.5649"), "1234.56 USD"),
        (D("0.005"), "0.01 USD"),
        (D("0.0049"), "0.00 USD"),
        (D("-60"), "-60.00 USD"),
        (D("5060"), "5060.00 USD"),
    ],
)
def test_dinero_a_dos_decimales_con_su_moneda(valor, esperado):
    assert estilo.dinero(valor, "USD") == esperado


@pytest.mark.parametrize(
    ("fraccion", "esperado"),
    [
        (D("0.15"), "15.0 %"),
        (D("0.0005"), "0.1 %"),  # 0,05 % sube a 0,1 %
        (D("0.00049"), "0.0 %"),
        (D("1"), "100.0 %"),
        (D("1200") / D("4000"), "30.0 %"),
    ],
)
def test_porcentaje_con_un_decimal(fraccion, esperado):
    assert estilo.porcentaje(fraccion) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(D("0.9375"), "0.94"), (D("0.8"), "0.80"), (D("0.995"), "1.00"), (D("0.9949"), "0.99")],
)
def test_indice_con_dos_decimales(valor, esperado):
    assert estilo.indice(valor) == esperado


def test_none_es_no_disponible_en_los_tres_formatos():
    assert estilo.dinero(None, "USD") == "no disponible"
    assert estilo.porcentaje(None) == "no disponible"
    assert estilo.indice(None) == "no disponible"
    assert estilo.NO_DISPONIBLE == "no disponible"


def test_la_paleta_es_hexadecimal_y_cubre_los_rubros_y_las_series_del_tablero():
    colores = [
        estilo.COLOR_PRIMARIO,
        estilo.COLOR_TENUE,
        estilo.COLOR_BIEN,
        estilo.COLOR_ATENCION,
        *estilo.COLORES_RUBRO.values(),
        *estilo.COLORES_SERIE.values(),
    ]
    assert all(re.fullmatch(r"#[0-9A-F]{6}", c) for c in colores), colores
    # Los cinco rubros del desglose y las cuatro series de la curva (`aplicacion.tablero`).
    assert list(estilo.COLORES_RUBRO) == [
        "Materiales",
        "Equipos",
        "Mano de obra",
        "Administración",
        "Utilidad",
    ]
    assert list(estilo.COLORES_SERIE) == ["Plan", "PV", "EV", "AC"]
    assert len(set(estilo.COLORES_SERIE.values())) == 4  # cada serie se distingue


@pytest.mark.parametrize("modulo", ["aplicacion/estilo.py", "aplicacion/tablero.py"])
def test_los_modulos_del_tablero_no_importan_streamlit_ni_pandas(modulo):
    prohibidos = {
        m for m in importaciones(RAIZ / modulo) if m.split(".")[0] in ("streamlit", "pandas")
    }
    assert prohibidos == set()
