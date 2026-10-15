"""`ui/estilo.py` y `ui/graficos.py` (PLAN_SILICE_UI, tareas 1 y 3; RU-1: sin prueba hasta la
auditoría final, 2026-10-13).

* Los formatos redondean a la mitad hacia arriba solo al presentar (NORMAS.md §2) y dicen «no
  disponible» ante `None`; las fronteras se escriben a mano (x,xx5 sube; x,xx49 baja).
* La paleta es una sola copia: el tema de `.streamlit/config.toml` repite `COLOR_PRIMARIO`, y los
  rubros y las series son exactamente los que arma `ui.tablero`.
* Los gráficos de Altair llevan los datos en línea, sin DataFrame, y validan contra el esquema de
  Vega-Lite (`to_dict()` valida); el anillo recorta la fracción a [0, 1]; la leyenda de la curva
  solo trae las series presentes, en el orden de la paleta.
* `ui/estilo.py`, `ui/tablero.py` y `ui/graficos.py` no importan Streamlit ni pandas (restricción
  global del plan).
"""

from __future__ import annotations

import json
import re
import tomllib
from decimal import Decimal

import pytest

from tests.fixtures.arquitectura import RAIZ, importaciones
from ui import estilo, graficos

D = Decimal
TOLERANCIA = 1e-9  # los datos de un gráfico son `float`


# --- ui/estilo.py ---------------------------------------------------------------------------------


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
    # Los cinco rubros del desglose y las cuatro series de la curva (`ui.tablero`).
    assert list(estilo.COLORES_RUBRO) == [
        "Materiales",
        "Equipos",
        "Mano de obra",
        "Administracion",
        "Utilidad",
    ]
    assert list(estilo.COLORES_SERIE) == ["Plan", "PV", "EV", "AC"]
    assert len(set(estilo.COLORES_SERIE.values())) == 4  # cada serie se distingue


def test_el_tema_de_streamlit_repite_el_color_primario():
    texto = (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    tema = tomllib.loads(texto)["theme"]
    assert tema["primaryColor"] == estilo.COLOR_PRIMARIO


@pytest.mark.parametrize("modulo", ["ui/estilo.py", "ui/tablero.py", "ui/graficos.py"])
def test_los_modulos_del_tablero_no_importan_streamlit_ni_pandas(modulo):
    prohibidos = {
        m for m in importaciones(RAIZ / modulo) if m.split(".")[0] in ("streamlit", "pandas")
    }
    assert prohibidos == set()


# --- ui/graficos.py -------------------------------------------------------------------------------


def _valores_del_anillo(fraccion: float) -> dict[str, float]:
    especificacion = graficos.anillo(fraccion, "texto").to_dict()
    return {v["parte"]: v["valor"] for v in especificacion["layer"][0]["data"]["values"]}


@pytest.mark.parametrize(
    ("fraccion", "lleno"),
    [(0.3, 0.3), (0.0, 0.0), (1.0, 1.0), (1.5, 1.0), (-0.2, 0.0)],
)
def test_el_anillo_recorta_la_fraccion_a_cero_uno(fraccion, lleno):
    valores = _valores_del_anillo(fraccion)
    assert abs(valores["a"] - lleno) <= TOLERANCIA
    assert abs(valores["b"] - (1 - lleno)) <= TOLERANCIA


def test_el_anillo_lleva_el_texto_al_centro_y_el_color_pedido():
    especificacion = graficos.anillo(0.5, "0.80", color=estilo.COLOR_ATENCION).to_dict()
    arcos, centro = especificacion["layer"]
    assert centro["data"]["values"] == [{"t": "0.80"}]
    assert arcos["encoding"]["color"]["scale"]["range"] == [
        estilo.COLOR_ATENCION,
        estilo.COLOR_TENUE,
    ]
    por_defecto = graficos.anillo(0.5, "x").to_dict()["layer"][0]
    assert por_defecto["encoding"]["color"]["scale"]["range"][0] == estilo.COLOR_PRIMARIO


FILAS_DESGLOSE = [
    {"Rubro": "Materiales", "Monto": "1800.00 USD", "Peso": "35.6 %", "monto": 1800.0},
    {"Rubro": "Utilidad", "Monto": "460.00 USD", "Peso": "9.1 %", "monto": 460.0},
]


def test_el_desglose_lleva_los_datos_en_linea_y_la_paleta_de_rubros():
    especificacion = graficos.desglose(FILAS_DESGLOSE).to_dict()
    assert especificacion["data"]["values"] == FILAS_DESGLOSE
    color = especificacion["encoding"]["color"]
    assert color["scale"]["domain"] == list(estilo.COLORES_RUBRO)
    assert color["scale"]["range"] == list(estilo.COLORES_RUBRO.values())
    assert especificacion["encoding"]["theta"]["field"] == "monto"
    assert [t["field"] for t in especificacion["encoding"]["tooltip"]] == ["Rubro", "Monto", "Peso"]


def _curva(series: list[str]) -> dict:
    filas = [
        {"Orden": 1, "Periodo": "Semana 1", "Serie": s, "Acumulado": float(i)}
        for i, s in enumerate(series)
    ]
    return graficos.curvas(filas).to_dict()


@pytest.mark.parametrize(
    ("series", "dominio"),
    [
        (["Plan"], ["Plan"]),
        (["AC", "EV", "PV"], ["PV", "EV", "AC"]),  # el orden es el de la paleta, no el de llegada
        (["PV", "EV"], ["PV", "EV"]),  # el AC falta donde un costo no tiene tasa
    ],
)
def test_la_curva_solo_pone_en_la_leyenda_las_series_presentes(series, dominio):
    escala = _curva(series)["encoding"]["color"]["scale"]
    assert escala["domain"] == dominio
    assert escala["range"] == [estilo.COLORES_SERIE[s] for s in dominio]


def test_el_pareto_ordena_por_monto_y_deja_la_descripcion_en_el_tooltip():
    filas = [
        {
            "Partida": "OB-C",
            "Descripcion": "*Relleno* [x](http://127.0.0.1:9)",
            "Total": "2530.00 USD",
            "Peso": "50.0 %",
            "Acumulado": "50.0 %",
            "monto": 2530.0,
        }
    ]
    especificacion = graficos.pareto(filas).to_dict()
    assert especificacion["encoding"]["y"]["sort"] == "-x"
    assert "Descripcion" in [t["field"] for t in especificacion["encoding"]["tooltip"]]
    # RU-9: el texto ajeno va en los datos (tooltip), nunca en un título.
    titulos = json.dumps({k: v for k, v in especificacion.items() if k != "data"})
    assert "Relleno" not in titulos


def test_las_versiones_resaltan_la_vigente():
    filas = [
        {"Version": "OB-001", "Fecha": "2026-11-02", "Motivo": "elaborada", "Total": "x",
         "Vigente": "", "total": 5060.0},
        {"Version": "OB-002", "Fecha": "2026-11-16", "Motivo": "recuperacion", "Total": "y",
         "Vigente": "si", "total": 5180.0},
    ]  # fmt: skip
    especificacion = graficos.versiones(filas).to_dict()
    color = especificacion["encoding"]["color"]
    assert color["condition"]["test"] == "(datum.Vigente === 'si')"
    assert color["condition"]["value"] == estilo.COLOR_PRIMARIO
    assert color["value"] == estilo.COLOR_TENUE
    assert especificacion["data"]["values"] == filas
