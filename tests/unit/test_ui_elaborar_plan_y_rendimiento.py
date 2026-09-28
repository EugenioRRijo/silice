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


# --- INV-088: sin rendimiento vigente, se propone el del historico (UC-01, flujo 3b) ------------

CLAVE_TIPO = "elaborar_tipo_rendimiento_LB-02-TUB"
CLAVE_REGISTRAR = "elaborar_registrar_rendimiento_LB-02-TUB"


@pytest.fixture
def base_sin_estimado(base_sembrada: Path) -> Path:
    """La base sembrada con `LB-02-TUB` sin estimado y dos medidos (`tests/fixtures`)."""
    from tests.fixtures.sin_rendimiento_vigente import dejar_sin_estimado

    motor = crear_motor(f"sqlite:///{base_sembrada.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            dejar_sin_estimado(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return base_sembrada


def _estimados_de_la_tuberia(base: Path) -> list[tuple[Decimal, object, str]]:
    """Los rendimientos ESTIMADOS de `LB-02-TUB` en la base, leidos por el catalogo."""
    from core.catalog import Catalogo
    from core.contracts.apu import TipoRendimiento
    from tests.fixtures.sin_rendimiento_vigente import CODIGO_SIN_ESTIMADO

    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return [
                (r.valor, r.fecha, r.condiciones)
                for r in Catalogo(sesion).rendimientos(CODIGO_SIN_ESTIMADO)
                if r.tipo is TipoRendimiento.ESTIMADO
            ]
    finally:
        motor.dispose()


def _sin_rendimiento(monkeypatch, base: Path) -> AppTest:
    """La pantalla a la fecha de la fixture, tras pulsar «Elaborar presupuesto»."""
    from tests.fixtures.sin_rendimiento_vigente import FECHA_PRESUPUESTO

    at = _pantalla(monkeypatch, base)
    _por_rotulo(at.sidebar.date_input, "Fecha").set_value(FECHA_PRESUPUESTO)
    at.run()
    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_sin_rendimiento_vigente_se_propone_el_del_historico_con_su_dispersion(
    monkeypatch, base_sin_estimado
):
    at = _sin_rendimiento(monkeypatch, base_sin_estimado)

    assert at.session_state[CLAVE_RESULTADO] is None  # no hay presupuesto sin ese rendimiento
    assert "Rendimientos por declarar" in [s.value for s in at.subheader]
    textos = [m.value for m in at.markdown]
    # El MEDIDO mas reciente del historico (100, no 90), con su tipo declarado.
    assert any("LB-02-TUB" in t and "100.00" in t and "medido" in t for t in textos), textos
    notas = [c.value for c in at.caption]
    # Dispersion a mano: dos medidos, 90 y 100 -> media 95, rango [90, 100].
    assert any("2 observaciones" in t and "95.00" in t and "[90.00, 100.00]" in t for t in notas), (
        notas
    )
    assert at.radio(key=CLAVE_TIPO).value is None  # el tipo no se presume: se exige declararlo


def test_sin_declarar_el_tipo_no_se_registra_nada(monkeypatch, base_sin_estimado):
    at = _sin_rendimiento(monkeypatch, base_sin_estimado)
    at.button(key=CLAVE_REGISTRAR).click().run()
    assert not at.exception, [e.value for e in at.exception]

    assert any("declare" in e.value.lower() for e in at.error), [e.value for e in at.error]
    assert _estimados_de_la_tuberia(base_sin_estimado) == []


def test_declarado_medido_no_se_usa_tal_cual_y_no_se_registra(monkeypatch, base_sin_estimado):
    at = _sin_rendimiento(monkeypatch, base_sin_estimado)
    at.radio(key=CLAVE_TIPO).set_value("medido")
    at.button(key=CLAVE_REGISTRAR).click().run()
    assert not at.exception, [e.value for e in at.exception]

    assert any("estimado" in e.value for e in at.error), [e.value for e in at.error]
    assert _estimados_de_la_tuberia(base_sin_estimado) == []
    assert at.session_state[CLAVE_RESULTADO] is None


def test_declarado_estimado_se_registra_y_se_vuelve_a_elaborar(monkeypatch, base_sin_estimado):
    from tests.fixtures.sin_rendimiento_vigente import FECHA_PRESUPUESTO

    at = _sin_rendimiento(monkeypatch, base_sin_estimado)
    at.radio(key=CLAVE_TIPO).set_value("estimado")
    at.button(key=CLAVE_REGISTRAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]

    ((valor, fecha, condiciones),) = _estimados_de_la_tuberia(base_sin_estimado)
    assert (valor, fecha) == (Decimal("100"), FECHA_PRESUPUESTO)
    assert "UC-01 3b" in condiciones  # RF-33: el rendimiento se registra con sus condiciones
    # Con el 100 propuesto, el APU de la tuberia es el de la linea base: el total tambien.
    assert at.session_state[CLAVE_RESULTADO].presupuesto.total == TOTAL_EXACTO_LINEA_BASE
    assert "Rendimientos por declarar" not in [s.value for s in at.subheader]


# --- U-1 y U-3 de la revision: sin lista vigente no es 3b ----------------------------------------


def _rendimientos_en(base: Path) -> int:
    """Cuantos rendimientos hay en la base (de cualquier partida y tipo)."""
    from sqlalchemy import func, select

    from core import models

    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return sesion.scalar(select(func.count()).select_from(models.Rendimiento))
    finally:
        motor.dispose()


def test_sin_lista_vigente_se_muestra_su_error_y_no_se_ofrece_3b(monkeypatch, base_sembrada):
    """Un `CatalogoIncompleto` real: el presupuesto se fecha antes de la lista (y de los estimados)
    de la linea base. Lo que falta es la lista: su mensaje, sin bloque 3b y sin escribir nada."""
    from datetime import date

    from tests.fixtures.apu_linea_base import FECHA_LINEA_BASE

    anterior = date(2026, 1, 1)
    assert anterior < FECHA_LINEA_BASE
    rendimientos = _rendimientos_en(base_sembrada)

    at = _pantalla(monkeypatch, base_sembrada)
    _por_rotulo(at.sidebar.date_input, "Fecha").set_value(anterior)
    at.run()
    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()
    assert not at.exception, [e.value for e in at.exception]

    errores = [e.value for e in at.error]
    assert any("lista de precios" in texto for texto in errores), errores
    assert "Rendimientos por declarar" not in [s.value for s in at.subheader]
    assert at.session_state[CLAVE_RESULTADO] is None
    assert _rendimientos_en(base_sembrada) == rendimientos


def test_un_insumo_sin_precio_muestra_su_error_y_no_se_ofrece_3b(monkeypatch, base_sembrada):
    """Otro `CatalogoIncompleto` real que no es de rendimiento: el cemento sin precio en la lista
    vigente. Todas las partidas tienen su estimado: el mensaje de siempre, sin bloque 3b."""
    from tests.fixtures.sin_rendimiento_vigente import INSUMO_SIN_PRECIO, quitar_precio

    motor = crear_motor(f"sqlite:///{base_sembrada.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            quitar_precio(sesion)
            sesion.commit()
    finally:
        motor.dispose()

    at = _pantalla(monkeypatch, base_sembrada)
    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()
    assert not at.exception, [e.value for e in at.exception]

    errores = [e.value for e in at.error]
    assert any(INSUMO_SIN_PRECIO in texto for texto in errores), errores
    assert "Rendimientos por declarar" not in [s.value for s in at.subheader]
    assert at.session_state[CLAVE_RESULTADO] is None


# --- U-2 de la revision: la declaracion no pasa de una partida a la siguiente --------------------


@pytest.fixture
def base_con_dos_sin_estimado(base_sin_estimado: Path) -> Path:
    """Tambien el encofrado sin estimado, con un medido de 16 m2 por dia (el de su APU)."""
    from datetime import date

    from tests.fixtures.sin_rendimiento_vigente import dejar_sin_estimado

    motor = crear_motor(f"sqlite:///{base_sin_estimado.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            dejar_sin_estimado(sesion, "LB-03-ENC", ((date(2026, 5, 5), Decimal("16")),))
            sesion.commit()
    finally:
        motor.dispose()
    return base_sin_estimado


def _radio_de(at: AppTest, codigo: str):
    return _por_rotulo(at.radio, f"Tipo declarado del rendimiento de {codigo}")


def test_con_dos_partidas_el_tipo_de_la_segunda_no_se_presume(
    monkeypatch, base_con_dos_sin_estimado
):
    at = _sin_rendimiento(monkeypatch, base_con_dos_sin_estimado)
    assert _radio_de(at, "LB-02-TUB").value is None
    assert _radio_de(at, "LB-03-ENC").value is None

    _radio_de(at, "LB-02-TUB").set_value("estimado")
    registrar = [b for b in at.button if b.label == "Registrar y volver a elaborar"]
    registrar[0].click().run()  # el de la tuberia, primera en el orden del computo
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]

    # Queda solo el encofrado, y su tipo sigue sin declarar: no hereda el de la tuberia.
    assert [r.label for r in at.radio] == ["Tipo declarado del rendimiento de LB-03-ENC"]
    assert _radio_de(at, "LB-03-ENC").value is None

    _radio_de(at, "LB-03-ENC").set_value("estimado")
    _por_rotulo(at.button, "Registrar y volver a elaborar").click().run()
    assert not at.exception, [e.value for e in at.exception]
    # Con los dos rendimientos de sus APU (100 y 16), el total es el de la linea base.
    assert at.session_state[CLAVE_RESULTADO].presupuesto.total == TOTAL_EXACTO_LINEA_BASE


# --- U-4 de la revision: propuesta None y fila del plan malformada en la pagina -----------------


def test_sin_ningun_historico_no_hay_propuesta_y_se_remite_a_componer(monkeypatch, base_sembrada):
    from tests.fixtures.sin_rendimiento_vigente import dejar_sin_historico

    motor = crear_motor(f"sqlite:///{base_sembrada.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            dejar_sin_historico(sesion, "LB-01-EXC")
            sesion.commit()
    finally:
        motor.dispose()
    rendimientos = _rendimientos_en(base_sembrada)

    at = _elaborado_sin_asertar_errores(monkeypatch, base_sembrada)

    assert "Rendimientos por declarar" in [s.value for s in at.subheader]
    errores = [e.value for e in at.error]
    assert any("LB-01-EXC" in t and "Componer una partida" in t for t in errores), errores
    assert all("LB-01-EXC" not in r.label for r in at.radio)
    assert _rendimientos_en(base_sembrada) == rendimientos


def _elaborado_sin_asertar_errores(monkeypatch, base: Path) -> AppTest:
    at = _pantalla(monkeypatch, base)
    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_una_fila_del_plan_malformada_se_rechaza_en_la_pagina(monkeypatch, base_sembrada):
    at = _elaborado(monkeypatch, base_sembrada)
    antes = at.session_state[CLAVE_RESULTADO]
    malformada = [*PLAN_DOS_SEMANAS[:-1], {**PLAN_DOS_SEMANAS[-1], "fraccion": "1,5"}]
    _reemplazar_plan(at, malformada)

    _por_rotulo(at.button, ROTULO_APLICAR_PLAN).click().run()
    assert not at.exception, [e.value for e in at.exception]

    errores = [e.value for e in at.error]
    assert any("fila 6" in texto for texto in errores), errores
    assert at.session_state[CLAVE_RESULTADO] is antes


# --- Duda 6 de la revision: el plan que vuelve al secuencial se avisa ----------------------------

AVISO_PLAN_REINICIADO = "volvio a una partida por dia"


def test_volver_a_elaborar_avisa_que_el_plan_vuelve_al_secuencial(monkeypatch, base_sembrada):
    """Cada elaboracion sin el plan del proyectista (el boton, aceptar una propuesta de 3a o
    registrar un rendimiento de 3b) vuelve a `plan_secuencial`: si descarta un plan editado, lo
    dice en vez de descartarlo en silencio."""
    at = _elaborado(monkeypatch, base_sembrada)
    assert not [c.value for c in at.caption if AVISO_PLAN_REINICIADO in c.value]

    _reemplazar_plan(at, PLAN_DOS_SEMANAS)
    _por_rotulo(at.button, ROTULO_APLICAR_PLAN).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not [c.value for c in at.caption if AVISO_PLAN_REINICIADO in c.value]

    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    avisos = [c.value for c in at.caption if AVISO_PLAN_REINICIADO in c.value]
    assert len(avisos) == 1, [c.value for c in at.caption]
    assert len(at.session_state[CLAVE_RESULTADO].presupuesto.curva) == len(CODIGOS_LINEA_BASE)
