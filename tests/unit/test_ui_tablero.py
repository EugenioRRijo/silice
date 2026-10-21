"""Tablero del proyecto: `ui/tablero.py` (datos, sin Streamlit) y `ui/paginas/tablero.py` (la
pantalla, con `AppTest`). PLAN_SILICE_UI, tareas 2 y 4; RU-1: sin prueba hasta la auditoría final
(2026-10-13).

Oráculo: la obra ficticia OB-S2 (memoria a mano `tests/fixtures/memorias/control_ob_s2.md`):
costo directo 4 000,00 = materiales 1 800 + equipos 210 + mano de obra 1 990 (§1, tabla de
partidas por cantidad), administración 600,00, utilidad 460,00 y total V = 5 060,00; plan por
semanas A 0,5·0,5, B 0,5·0,5, C 0,5·0,5; PE base 56,60 %; al corte con V-01 y V-02: PV 1 500,
EV 1 200, AC 1 280, SPI 0,8000, CPI 0,9375 y EAC por índice 4 000 / 0,9375 = 4 266,67. Para un
presupuesto sin cifras redondas, TI-001 (total literal 50 503,27 USD del informe publicado).

Cubre lo que la bitácora 2026-10-12 anotó «sin prueba»: el desglose que suma el total, el Pareto
con su fila «Resto», las curvas con y sin control, el control no disponible (con sus motivos),
`tarjetas_de_control` con las claves SPI, CPI y EAC y sus respaldos, y la pantalla sin proyecto,
sin versión, con control y con texto ajeno. Datos ficticios (NORMAS.md §1).
"""

from __future__ import annotations

import hashlib
import importlib
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from aplicacion import tablero
from core.budget import crear_proyecto
from core.budget.valor_ganado import Indicadores
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.catalog.sesion import _activar_claves_foraneas
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from ui.caso import CLAVE_PROYECTO
from ui.paginas.tablero import (
    CLAVE_PROYECTO_VISTO,
    SIN_PROYECTO,
    SIN_PROYECTOS,
    SIN_VERSION,
)
from ui.texto_seguro import texto_seguro

D = Decimal
CELDA = 0.005  # tolerancia por monto presentado (los gráficos reciben `float`)
SCRIPT = "from ui.paginas.tablero import render\n\nrender()\n"
SIN_LINEA_BASE = "Sin línea base de control: declárela en Control de obra."
SIN_VALUACION = "La línea base está declarada; falta la primera valuación."


# --- utilidades --------------------------------------------------------------------------------


@pytest.fixture
def sesion():
    motor = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(motor, "connect", _activar_claves_foraneas)
    crear_esquema(motor)
    with abrir_sesion(motor) as abierta:
        yield abierta
    motor.dispose()


def _indicadores(**cambios) -> Indicadores:
    """Los indicadores de OB-S2 al corte (memoria §3) escritos a mano; `cambios` los altera."""
    datos = dict(
        bac=D(4000), pv=D(1500), ev=D(1200), ac=D(1280), sv=D(-300), cv=D(-80), spi=D("0.8"),
        cpi=D("0.9375"), cpi_corte=None, eac_indice=D(4000) / D("0.9375"), eac_sistema=None,
        vac=None, termino_indice=25, no_disponible={},
    )  # fmt: skip
    datos.update(cambios)
    return Indicadores(**datos)


def _tarjetas(indicadores: Indicadores | None) -> dict[str, tablero.Tarjeta]:
    datos = tablero.DatosControl(indicadores, [], "")
    return {t.rotulo: t for t in tablero.tarjetas_de_control(datos, "USD")}


# --- desglose, Pareto y curvas (puros) -------------------------------------------------------


# --- tarjetas --------------------------------------------------------------------------------


# --- lectura desde la base ---------------------------------------------------------------------


# --- la pantalla ------------------------------------------------------------------------------


def _caso(tmp_path: Path, *, linea_base=False, valuaciones=False, nombre=ob.NOMBRE, monkeypatch):
    ruta = tmp_path / "obra.db"
    preparar_base(ruta)
    monkeypatch.setattr(ob, "NOMBRE", nombre)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as abierta:
            ob.sembrar(abierta)
            if linea_base:
                ob.declarar_linea_base(abierta)
            if valuaciones:
                ob.registrar_v01_y_v02(abierta)
            abierta.commit()
    finally:
        motor.dispose()
    return ruta


def _pantalla(monkeypatch, ruta: Path, *, proyecto: str | None = ob.NOMBRE) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(ruta))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    if proyecto is not None:
        at.session_state[CLAVE_PROYECTO] = proyecto
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _metricas(at: AppTest) -> dict[str, str]:
    return {m.label: m.value for m in at.metric}


def _graficos(at: AppTest) -> int:
    return len(at.get("arrow_vega_lite_chart")) + len(at.get("vega_lite_chart"))


def test_la_pantalla_sin_caso_dice_que_no_hay_proyectos_y_no_crea_la_base(monkeypatch, tmp_path):
    ruta = tmp_path / "no_existe.db"
    at = _pantalla(monkeypatch, ruta)
    assert [i.value for i in at.info] == [SIN_PROYECTOS]
    assert not ruta.exists()


def test_la_pantalla_con_un_caso_sin_proyectos_lo_dice(monkeypatch, tmp_path):
    ruta = tmp_path / "vacio.db"
    preparar_base(ruta)
    at = _pantalla(monkeypatch, ruta, proyecto=None)
    assert [i.value for i in at.info] == [SIN_PROYECTOS]


def test_sin_proyecto_abierto_se_elige_uno_de_solo_lectura(monkeypatch, tmp_path):
    """Corrección 2 de la revisión final: el rol que solo lee elige aquí y no abre el proyecto."""
    ruta = _caso(tmp_path, monkeypatch=monkeypatch)
    at = _pantalla(monkeypatch, ruta, proyecto=None)
    selector = at.selectbox(key=CLAVE_PROYECTO_VISTO)
    assert list(selector.options) == [ob.NOMBRE]
    assert [i.value for i in at.info] == [SIN_PROYECTO]
    selector.select(ob.NOMBRE).run()
    assert not at.exception, [e.value for e in at.exception]
    assert _metricas(at)["Total del contrato"] == "5060.00 USD"
    assert CLAVE_PROYECTO not in at.session_state  # la barra sigue sin proyecto abierto


def test_un_proyecto_sin_version_pide_armarla_en_la_hoja(monkeypatch, tmp_path):
    ruta = tmp_path / "obra.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as abierta:
        crear_proyecto(abierta, "Sin version")
        abierta.commit()
    motor.dispose()
    at = _pantalla(monkeypatch, ruta, proyecto="Sin version")
    assert [i.value for i in at.info] == [SIN_VERSION]
    assert not at.metric


def test_sin_control_pinta_el_presupuesto_el_plan_y_el_motivo(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, _caso(tmp_path, monkeypatch=monkeypatch))
    assert _metricas(at) == {
        "Total del contrato": "5060.00 USD",
        "Costo directo": "4000.00 USD",
        "Punto de equilibrio": "56.60 %",
        "Auditoría": "Cumple",
    }
    assert texto_seguro(SIN_LINEA_BASE) in [i.value for i in at.info]
    rotulos = [m.value for m in at.markdown]
    assert "**Plan acumulado**" in rotulos and "**Valor ganado (PV, EV, AC)**" not in rotulos
    desglose = next(d.value for d in at.dataframe if "Rubro" in d.value.columns)
    assert list(desglose["Monto"]) == [
        "1800.00 USD",
        "210.00 USD",
        "1990.00 USD",
        "600.00 USD",
        "460.00 USD",
    ]
    pareto = next(d.value for d in at.dataframe if "Acumulado" in d.value.columns)
    assert list(pareto["Partida"]) == ["OB-C", "OB-A", "OB-B"]
    versiones = next(d.value for d in at.dataframe if "Vigente" in d.value.columns)
    assert list(versiones["Version"]) == ["OB-001"]
    assert _graficos(at) == 4  # curva, desglose, Pareto y versiones; sin anillos


def test_con_control_pinta_anillos_tarjetas_y_la_curva_pv_ev_ac(monkeypatch, tmp_path):
    ruta = _caso(tmp_path, linea_base=True, valuaciones=True, monkeypatch=monkeypatch)
    at = _pantalla(monkeypatch, ruta)
    metricas = _metricas(at)
    assert metricas["Avance físico (EV/BAC)"] == "30.0 %"
    assert metricas["SPI (plazo)"] == "0.80"
    assert metricas["CPI (costo)"] == "0.94"
    assert metricas["EAC (costo final estimado)"] == "4266.67 USD"
    assert "**Valor ganado (PV, EV, AC)**" in [m.value for m in at.markdown]
    assert {"Avance fisico", "SPI (plazo)", "CPI (costo)"} <= {c.value for c in at.caption}
    assert _graficos(at) == 7  # tres anillos, curva, desglose, Pareto y versiones


def test_con_linea_base_sin_valuaciones_la_pantalla_lo_dice(monkeypatch, tmp_path):
    ruta = _caso(tmp_path, linea_base=True, monkeypatch=monkeypatch)
    at = _pantalla(monkeypatch, ruta)
    assert texto_seguro(SIN_VALUACION) in [i.value for i in at.info]
    assert "SPI (plazo)" not in _metricas(at)


def test_un_nombre_de_proyecto_con_markdown_se_muestra_literal(monkeypatch, tmp_path):
    """RU-9 y foco 5 del plan UI: `*`, `_`, `[`, `<` y `#` sin formato ni enlaces."""
    raro = "Obra *negrita* _x_ [enlace](http://127.0.0.1:9) <b> #1"
    ruta = _caso(tmp_path, nombre=raro, monkeypatch=monkeypatch)
    at = _pantalla(monkeypatch, ruta, proyecto=raro)
    assert [s.value for s in at.subheader] == [texto_seguro(raro)]
    textos = [m.value for m in at.markdown] + [c.value for c in at.caption]
    assert not any(raro in t for t in textos)


def test_la_pantalla_no_escribe_en_el_caso(monkeypatch, tmp_path):
    """RU-10: el tablero es de solo lectura (no registra la instantánea de `abrir_version`)."""
    ruta = _caso(tmp_path, linea_base=True, valuaciones=True, monkeypatch=monkeypatch)
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    _pantalla(monkeypatch, ruta)
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes


def test_un_caso_ilegible_se_informa_sin_traceback(monkeypatch, tmp_path):
    ruta = tmp_path / "roto.db"
    ruta.write_bytes(b"esto no es una base SQLite" * 100)
    at = _pantalla(monkeypatch, ruta)
    assert at.error and not at.metric
