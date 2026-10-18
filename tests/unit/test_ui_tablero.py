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
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from core.budget import crear_proyecto, elaborar
from core.budget.actualizacion import descartar_version
from core.budget.valor_ganado import Indicadores
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor
from core.catalog.sesion import _activar_claves_foraneas
from operacion.base_datos import preparar_base
from tests.fixtures import caso_ti001 as ti
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz
from tests.fixtures.caso_s2 import sembrar_caso_s2
from aplicacion import control, tablero
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
SIN_LINEA_BASE = "Sin linea base de control: declarela en Control de obra."
SIN_VALUACION = "La linea base esta declarada; falta la primera valuacion."


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


def test_el_desglose_de_ob_s2_es_el_de_la_memoria_y_suma_el_total():
    presupuesto = ob.elaborar_ob_s2().presupuesto
    filas = tablero.filas_de_desglose(presupuesto)
    assert [(f["Rubro"], f["Monto"], f["Peso"]) for f in filas] == [
        ("Materiales", "1800.00 USD", "35.6 %"),  # 200 × 3 + 100 × 12
        ("Equipos", "210.00 USD", "4.2 %"),  # 100 × 1,20 + 200 × 0,15 + 100 × 0,60
        ("Mano de obra", "1990.00 USD", "39.3 %"),  # 100 × 8,80 + 200 × 1,85 + 100 × 7,40
        ("Administracion", "600.00 USD", "11.9 %"),  # 4 000 × 0,15
        ("Utilidad", "460.00 USD", "9.1 %"),  # 4 600 × 0,10
    ]
    assert abs(sum(f["monto"] for f in filas) - 5060.0) <= CELDA


def test_el_desglose_de_ti001_suma_el_total_literal_del_informe():
    presupuesto = ti.elaborar_caso().presupuesto
    filas = tablero.filas_de_desglose(presupuesto)
    assert len(filas) == 5
    assert abs(sum(f["monto"] for f in filas) - 50503.27) <= 0.01  # total publicado (30/09/2026)
    assert all(f["monto"] >= 0 for f in filas)


def test_un_presupuesto_de_total_cero_no_tiene_desglose_ni_pareto():
    """Foco 2 del plan UI: sin división por cero; el anillo y el Pareto quedan vacíos."""
    vacio = ob.elaborar_ob_s2().presupuesto
    sin_partidas = type(vacio)(
        codigo=vacio.codigo, fecha=vacio.fecha, moneda=vacio.moneda, partidas=(), curva=()
    )
    assert sin_partidas.total == D(0)
    assert tablero.filas_de_desglose(sin_partidas) == []
    assert tablero.filas_pareto(sin_partidas) == []


def test_el_pareto_con_resto_suma_el_total_y_cierra_en_cien():
    """A 1 265, B 1 265 y C 2 530 (cantidad × u × 1,265). Con n = 2: C, luego A (el empate se
    ordena por código) y «Resto (1)» con B."""
    presupuesto = ob.elaborar_ob_s2().presupuesto
    filas = tablero.filas_pareto(presupuesto, 2)
    assert [(f["Partida"], f["Total"], f["Peso"], f["Acumulado"]) for f in filas] == [
        ("OB-C", "2530.00 USD", "50.0 %", "50.0 %"),
        ("OB-A", "1265.00 USD", "25.0 %", "75.0 %"),
        ("Resto (1)", "1265.00 USD", "25.0 %", "100.0 %"),
    ]
    assert filas[-1]["Descripcion"] == "las demas partidas"
    assert abs(sum(f["monto"] for f in filas) - 5060.0) <= CELDA


def test_el_pareto_sin_resto_cuando_n_alcanza_a_todas_las_partidas():
    presupuesto = ob.elaborar_ob_s2().presupuesto
    filas = tablero.filas_pareto(presupuesto, 3)  # frontera: n = número de partidas
    assert [f["Partida"] for f in filas] == ["OB-C", "OB-A", "OB-B"]
    assert filas[-1]["Acumulado"] == "100.0 %"
    assert tablero.PARTIDAS_EN_PARETO == 10
    assert len(tablero.filas_pareto(presupuesto)) == 3  # 3 < 10: sin «Resto»


def test_el_pareto_suma_los_renglones_de_una_misma_partida():
    """Dos renglones de OB-A (100 y 50 m3) son una sola barra: 150 × 12,65 = 1 897,50."""
    extra = ob.items()[0]
    otro = type(extra)(
        extra.codigo_partida, extra.descripcion, extra.unidad, D(50), "memoria-ob-s2:OB-A-2",
        extra.origen_tipo, extra.dominio,
    )  # fmt: skip
    presupuesto = elaborar(
        [*ob.items(), otro], ob.composiciones(), ob.PARAMETROS, codigo="OB-X", fecha=ob.FECHA,
        moneda=ob.MONEDA,
    ).presupuesto  # fmt: skip
    filas = {f["Partida"]: f for f in tablero.filas_pareto(presupuesto)}
    assert set(filas) == {"OB-A", "OB-B", "OB-C"}
    assert filas["OB-A"]["Total"] == "1897.50 USD"


def test_sin_control_la_curva_es_el_plan_acumulado_del_presupuesto():
    """Precio: S1 0,5 × 1 265 = 632,50; S2 + 632,50 + 632,50; S3 + 632,50 + 1 265; S4 + 1 265."""
    presupuesto = ob.elaborar_ob_s2().presupuesto
    filas = tablero.filas_de_curvas(presupuesto, tablero.DatosControl(None, [], "sin control"))
    assert [(f["Orden"], f["Serie"]) for f in filas] == [(n, "Plan") for n in range(1, 5)]
    for fila, esperado in zip(filas, (632.5, 1897.5, 3795.0, 5060.0), strict=True):
        assert abs(fila["Acumulado"] - esperado) <= CELDA


def test_con_control_la_curva_es_pv_ev_ac_y_salta_el_ac_que_falta():
    """RU-12: con control no se dibuja el plan. Un AC `None` (costo sin tasa) no se dibuja."""
    curva = [
        {"Periodo": "Semana 1", "PV": D(500), "EV": D(400), "AC": None},
        {"Periodo": "Semana 2", "PV": D(1500), "EV": D(1200), "AC": D(1280)},
    ]
    datos = tablero.DatosControl(_indicadores(), curva, "")
    filas = tablero.filas_de_curvas(ob.elaborar_ob_s2().presupuesto, datos)
    assert [(f["Orden"], f["Periodo"], f["Serie"], f["Acumulado"]) for f in filas] == [
        (1, "Semana 1", "PV", 500.0),
        (1, "Semana 1", "EV", 400.0),
        (2, "Semana 2", "PV", 1500.0),
        (2, "Semana 2", "EV", 1200.0),
        (2, "Semana 2", "AC", 1280.0),
    ]
    assert "Plan" not in {f["Serie"] for f in filas}


# --- tarjetas --------------------------------------------------------------------------------


def test_sin_indicadores_no_hay_tarjetas_de_control():
    assert tablero.tarjetas_de_control(tablero.DatosControl(None, [], "motivo"), "USD") == []


def test_las_tarjetas_de_control_de_ob_s2_al_corte():
    tarjetas = _tarjetas(_indicadores())
    assert [(t.rotulo, t.valor, t.detalle) for t in tarjetas.values()] == [
        ("Avance fisico (EV/BAC)", "30.0 %", ""),  # 1 200 / 4 000
        ("SPI (plazo)", "0.80", ""),
        ("CPI (costo)", "0.94", ""),  # 0,9375 sube a 0,94
        ("EAC (costo final estimado)", "4266.67 USD", ""),  # 4 000 / 0,9375
    ]


def test_un_eac_disponible_no_lleva_el_motivo_del_eac_del_sistema():
    """`no_disponible["EAC"]` habla del EAC **del sistema** (sin precios del corte); la tarjeta
    muestra el EAC por índice, que sí está: su ayuda no puede decir que falta."""
    tarjeta = _tarjetas(_indicadores(no_disponible={"EAC": "sin precios del corte"}))[
        "EAC (costo final estimado)"
    ]
    assert (tarjeta.valor, tarjeta.detalle) == ("4266.67 USD", "")


def test_sin_ac_el_cpi_y_el_eac_dicen_el_motivo_del_ac():
    """Un costo en Bs sin tasa del BCV: AC `None`; `indicadores` copia su motivo a CV, CPI, EAC
    y VAC (`setdefault`)."""
    motivo = "el costo del 2026-11-13 en Bs no tiene tasa aplicable"
    claves = dict.fromkeys(("AC", "CV", "CPI", "EAC", "VAC"), motivo)
    tarjetas = _tarjetas(
        _indicadores(ac=None, cv=None, cpi=None, eac_indice=None, no_disponible=claves)
    )
    assert (tarjetas["CPI (costo)"].valor, tarjetas["CPI (costo)"].detalle) == (
        "no disponible",
        motivo,
    )
    eac = tarjetas["EAC (costo final estimado)"]
    assert (eac.valor, eac.detalle) == ("no disponible", motivo)


def test_con_ac_cero_el_eac_dice_por_que_falta_el_cpi():
    """AC = 0: CPI y EAC por índice no existen por el CPI; sin precios del corte, la clave «EAC»
    (del sistema) dice otra cosa y no es el motivo de esta tarjeta."""
    tarjetas = _tarjetas(
        _indicadores(
            ac=D(0),
            cv=D(1200),
            cpi=None,
            eac_indice=None,
            no_disponible={
                "CPI": "AC = 0: aun no hay costos reales",
                "EAC": "sin precios del corte",
            },
        )  # fmt: skip
    )
    assert tarjetas["CPI (costo)"].detalle == "AC = 0: aun no hay costos reales"
    eac = tarjetas["EAC (costo final estimado)"]
    assert (eac.valor, eac.detalle) == ("no disponible", "AC = 0: aun no hay costos reales")


def test_sin_pv_el_spi_dice_su_motivo_y_el_avance_con_bac_cero_no_esta():
    motivo = "PV = 0: el corte es anterior a todo trabajo planificado"
    tarjetas = _tarjetas(_indicadores(pv=D(0), spi=None, no_disponible={"SPI": motivo}))
    assert (tarjetas["SPI (plazo)"].valor, tarjetas["SPI (plazo)"].detalle) == (
        "no disponible",
        motivo,
    )
    assert tablero.avance_fisico(_indicadores(bac=D(0))) is None
    assert tablero.avance_fisico(None) is None
    assert _tarjetas(_indicadores(bac=D(0)))["Avance fisico (EV/BAC)"].valor == "no disponible"


# --- lectura desde la base ---------------------------------------------------------------------


def test_sin_version_guardada_no_hay_tablero(sesion):
    crear_proyecto(sesion, "Proyecto vacio")
    assert tablero.leer_tablero(sesion, Catalogo(sesion), "Proyecto vacio") is None


def test_el_tablero_sin_linea_base_trae_el_presupuesto_y_dice_por_que_no_hay_control(sesion):
    ob.sembrar(sesion)
    datos = tablero.leer_tablero(sesion, Catalogo(sesion), ob.NOMBRE)
    assert (datos.proyecto, datos.codigo, datos.fecha) == (ob.NOMBRE, ob.CODIGO, ob.FECHA)
    assert datos.control == tablero.DatosControl(None, [], SIN_LINEA_BASE)
    tarjetas = {t.rotulo: t for t in tablero.tarjetas_del_presupuesto(datos)}
    assert tarjetas["Total del contrato"].valor == "5060.00 USD"
    assert tarjetas["Costo directo"].valor == "4000.00 USD"
    assert tarjetas["Punto de equilibrio"].valor == "56.60 %"  # 2 864,15 / 5 060 (memoria §1)
    # El informe de OB-S2 trae R1 en ADVERTENCIA por partida (rendimientos supuestos): cumple.
    auditoria = tarjetas["Auditoria"]
    assert (auditoria.valor, auditoria.detalle) == ("CUMPLE", "3 advertencia")


def test_con_linea_base_y_sin_valuaciones_el_control_lo_dice(sesion):
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    datos = tablero.leer_control(sesion, Catalogo(sesion), ob.NOMBRE)
    assert datos == tablero.DatosControl(None, [], SIN_VALUACION)


def test_con_valuaciones_el_control_trae_los_indicadores_y_la_curva_pv_ev_ac(sesion):
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    ob.registrar_v01_y_v02(sesion)
    datos = tablero.leer_tablero(sesion, Catalogo(sesion), ob.NOMBRE)
    ind = datos.control.indicadores
    assert datos.control.motivo == ""
    for valor, esperado in ((ind.pv, 1500), (ind.ev, 1200), (ind.ac, 1280)):
        assert abs(valor - D(esperado)) <= D("0.005")
    filas = tablero.filas_de_curvas(datos.elaboracion.presupuesto, datos.control)
    esperadas = [
        (1, "PV", 500.0), (1, "EV", 400.0), (1, "AC", 0.0),
        (2, "PV", 1500.0), (2, "EV", 1200.0), (2, "AC", 1280.0),
    ]  # fmt: skip
    assert [(f["Orden"], f["Serie"]) for f in filas] == [(o, s) for o, s, _ in esperadas]
    for fila, (_, _, acumulado) in zip(filas, esperadas, strict=True):
        assert abs(fila["Acumulado"] - acumulado) <= CELDA
    tarjetas = {t.rotulo: t for t in tablero.tarjetas_de_control(datos.control, "USD")}
    assert tarjetas["SPI (plazo)"].valor == "0.80" and tarjetas["CPI (costo)"].valor == "0.94"
    eac = tarjetas["EAC (costo final estimado)"]
    assert (eac.valor, eac.detalle) == ("4266.67 USD", "")  # sin precios, el índice sí está


@pytest.mark.parametrize("error", [control.ControlInvalido, ValueError, LookupError])
def test_un_control_que_no_se_puede_calcular_da_su_motivo_y_no_rompe(sesion, monkeypatch, error):
    """Corrección 3 de la revisión final: `leer_control` captura `ValueError` y `LookupError`."""
    ob.sembrar(sesion)
    ob.declarar_linea_base(sesion)
    ob.registrar_v01_y_v02(sesion)

    def falla(*_args, **_kwargs):
        raise error("la linea base se invalido por un cambio de moneda")

    monkeypatch.setattr(control, "calcular_el_control", falla)
    datos = tablero.leer_control(sesion, Catalogo(sesion), ob.NOMBRE)
    assert datos == tablero.DatosControl(
        None, [], "la linea base se invalido por un cambio de moneda"
    )


def test_el_comparativo_trae_las_versiones_y_omite_la_descartada(sesion):
    """OB-R01 revalora los materiales de B (3 → 4) y C (12 → 14,10): costo directo 1 000 + 200 ×
    6 + 100 × 22,10 = 4 410 y total 4 410 × 1,265 = 5 578,65."""
    ob.sembrar(sesion)
    rz.sembrar_revaloracion(sesion)
    filas = tablero.filas_comparativo(sesion, ob.NOMBRE)
    assert [(f["Version"], f["Costo directo"], f["Total"]) for f in filas] == [
        ("OB-001", "4000.00 USD", "5060.00 USD"),
        ("OB-R01", "4410.00 USD", "5578.65 USD"),
    ]
    assert filas[0]["Motivo"] == "elaborada"
    assert sum(1 for f in filas if f["Vigente"] == "si") == 1
    assert abs(filas[1]["total"] - 5578.65) <= CELDA
    descartar_version(sesion, ob.NOMBRE, rz.REVALORADA, date(2026, 11, 14))
    assert [f["Version"] for f in tablero.filas_comparativo(sesion, ob.NOMBRE)] == ["OB-001"]


def test_el_comparativo_de_una_decision_de_recuperacion_dice_su_motivo(sesion):
    sembrar_caso_s2(sesion)
    filas = tablero.filas_comparativo(sesion, ob.NOMBRE)
    assert [(f["Version"], f["Motivo"], f["Vigente"]) for f in filas] == [
        ("OB-001", "elaborada", ""),
        ("OB-002", "recuperacion", "si"),
    ]
    assert filas[1]["Total"] == "5060.00 USD"  # la decisión cambia el plan, no las cantidades


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
        "Auditoria": "CUMPLE",
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
    assert metricas["Avance fisico (EV/BAC)"] == "30.0 %"
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
