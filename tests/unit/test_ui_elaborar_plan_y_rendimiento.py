"""UC-01 6 y 3b en la pantalla de elaborar (fase C5, pista U: INV-087 e INV-088).

INV-087 (UC-01, paso 6): el proyectista distribuye las partidas en periodos. La pantalla elabora
primero con `plan_secuencial` (el valor por defecto, que deja la linea base como estaba) y ofrece
el plan de trabajo como tabla editable; «Aplicar plan y volver a elaborar» lo pasa a `elaborar`.

`st.data_editor` no se teclea desde `AppTest`: la tabla del plan se reemplaza por
`st.session_state["elaborar_plan__filas"]` y el borrado de la clave del editor, la misma via que
`tests/unit/test_ui_componer.py::_reemplazar_tablas`. La base vive en `tmp_path`, desviada por el
objeto modulo `sys.modules["ui.caso"]`; la salvaguarda de `tests/conftest.py` vigila `data/apu.db`.

Oraculo independiente: la aritmetica a mano de la fixture de la linea base (cantidad del computo
auditado por el precio unitario exacto del motor), no la pantalla ni `generar_curva`.
"""

from __future__ import annotations

import importlib
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import ElementList

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from scripts.seed import sembrar
from tests.fixtures.apu_linea_base import (
    CODIGOS_LINEA_BASE,
    PRECIO_UNITARIO_EXACTO,
    PRESUPUESTO_AUDITADO,
    TOTAL_EXACTO_LINEA_BASE,
)
from tests.fixtures.computo_auditado import items_auditados

SCRIPT = "from ui.paginas.elaborar import render\nrender()\n"

CLAVE_ITEMS = "elaborar_items"
CLAVE_RESULTADO = "elaborar_resultado"
CLAVE_PLAN = "elaborar_plan"
ROTULO_ELABORAR = "Elaborar presupuesto"
ROTULO_APLICAR_PLAN = "Aplicar plan y volver a elaborar"

#: El plan del proyectista: dos semanas, con la tuberia repartida mitad y mitad entre ellas.
PLAN_DOS_SEMANAS = [
    {"periodo": "Semana 1", "codigo_partida": "LB-01-EXC", "fraccion": "1"},
    {"periodo": "Semana 1", "codigo_partida": "LB-02-TUB", "fraccion": "0.5"},
    {"periodo": "Semana 2", "codigo_partida": "LB-02-TUB", "fraccion": "0.5"},
    {"periodo": "Semana 2", "codigo_partida": "LB-03-ENC", "fraccion": "1"},
    {"periodo": "Semana 2", "codigo_partida": "LB-04-CON", "fraccion": "1"},
    {"periodo": "Semana 2", "codigo_partida": "LB-05-REL", "fraccion": "1"},
]


def _total_de(codigo: str) -> Decimal:
    """Aritmetica a mano de la fixture: cantidad auditada por el precio unitario exacto."""
    return sum(
        (
            linea.cantidad * PRECIO_UNITARIO_EXACTO[linea.codigo_partida]
            for linea in PRESUPUESTO_AUDITADO
            if linea.codigo_partida == codigo
        ),
        Decimal(0),
    )


def _por_rotulo(elementos: ElementList, rotulo: str):
    for elemento in elementos:
        if elemento.label == rotulo:
            return elemento
    raise AssertionError(f"ningun elemento {rotulo!r}: {[e.label for e in elementos]}")


@pytest.fixture
def base_sembrada(tmp_path: Path) -> Path:
    base = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return base


def _pantalla(monkeypatch, base: Path) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_ITEMS] = list(items_auditados())
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _elaborado(monkeypatch, base: Path) -> AppTest:
    at = _pantalla(monkeypatch, base)
    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    return at


def _reemplazar_plan(at: AppTest, filas: list[dict[str, str]]) -> None:
    """Simula que el proyectista edita la tabla del plan (ver el docstring del modulo)."""
    at.session_state[f"{CLAVE_PLAN}__filas"] = filas
    if CLAVE_PLAN in at.session_state:
        del at.session_state[CLAVE_PLAN]
    at.run()
    assert not at.exception, [e.value for e in at.exception]


# --- INV-087: el proyectista reparte los periodos (UC-01, paso 6) ------------------------------


def test_por_defecto_el_plan_es_una_partida_por_dia(monkeypatch, base_sembrada):
    """`plan_secuencial` sigue siendo el valor por defecto: la tabla lo precarga, un dia por
    partida y al 100 %, y la curva de la primera elaboracion es la suya."""
    at = _elaborado(monkeypatch, base_sembrada)

    curva = at.session_state[CLAVE_RESULTADO].presupuesto.curva
    assert [punto.periodo for punto in curva] == [
        f"Dia {numero} [{codigo}]" for numero, codigo in enumerate(CODIGOS_LINEA_BASE, start=1)
    ]
    assert at.session_state[f"{CLAVE_PLAN}__filas"] == [
        {"periodo": f"Dia {numero}", "codigo_partida": codigo, "fraccion": "1"}
        for numero, codigo in enumerate(CODIGOS_LINEA_BASE, start=1)
    ]


def test_el_plan_del_proyectista_reparte_los_periodos(monkeypatch, base_sembrada):
    at = _elaborado(monkeypatch, base_sembrada)
    _reemplazar_plan(at, PLAN_DOS_SEMANAS)

    _por_rotulo(at.button, ROTULO_APLICAR_PLAN).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]

    curva = at.session_state[CLAVE_RESULTADO].presupuesto.curva
    assert [punto.periodo for punto in curva] == [
        "Semana 1 [LB-01-EXC, LB-02-TUB]",
        "Semana 2 [LB-02-TUB, LB-03-ENC, LB-04-CON, LB-05-REL]",
    ]
    # Aritmetica a mano: la excavacion entera y media tuberia en la primera semana.
    semana_1 = _total_de("LB-01-EXC") + Decimal("0.5") * _total_de("LB-02-TUB")
    assert curva[0].monto == semana_1
    assert curva[-1].acumulado == TOTAL_EXACTO_LINEA_BASE  # la curva cierra en el total (R2)
    # La tabla conserva el plan del proyectista despues de volver a elaborar.
    assert at.session_state[f"{CLAVE_PLAN}__filas"] == PLAN_DOS_SEMANAS


def test_un_plan_que_no_reparte_toda_partida_se_rechaza_y_conserva_el_presupuesto(
    monkeypatch, base_sembrada
):
    at = _elaborado(monkeypatch, base_sembrada)
    antes = at.session_state[CLAVE_RESULTADO]
    _reemplazar_plan(at, PLAN_DOS_SEMANAS[:-1])  # el relleno queda sin repartir

    _por_rotulo(at.button, ROTULO_APLICAR_PLAN).click().run()
    assert not at.exception, [e.value for e in at.exception]

    errores = [e.value for e in at.error]
    assert any("LB-05-REL" in texto for texto in errores), errores
    assert at.session_state[CLAVE_RESULTADO] is antes  # el presupuesto a la vista no se pierde


def test_las_filas_del_plan_se_agrupan_por_periodo_y_una_a_medias_se_rechaza() -> None:
    from ui.composicion import ComposicionInvalida
    from ui.elaboracion import plan_desde_filas

    filas = [
        *PLAN_DOS_SEMANAS[:2],
        {"periodo": "", "codigo_partida": "", "fraccion": ""},  # fila dinamica en blanco
        *PLAN_DOS_SEMANAS[2:],
    ]
    plan = plan_desde_filas(filas)
    assert [periodo for periodo, _ in plan] == ["Semana 1", "Semana 2"]
    assert plan[0][1] == (("LB-01-EXC", Decimal("1")), ("LB-02-TUB", Decimal("0.5")))

    a_medias = [{"periodo": "Semana 1", "codigo_partida": "LB-01-EXC", "fraccion": ""}]
    with pytest.raises(ComposicionInvalida, match="fila 1"):
        plan_desde_filas(a_medias)
