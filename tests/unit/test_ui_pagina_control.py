"""Pantalla «Control de obra» (UC-19 y UC-20; spec S2 §5.5) con `AppTest`.

Una base de OB-S2 en `tmp_path`, abierta con `preparar_base` (RV-5); el caso se desvía parchando el
objeto módulo de `ui.caso`. `st.data_editor` no se teclea desde `AppTest`, así que el registro con
líneas se prueba en `tests/integration/test_ui_control.py` y aquí solo su rechazo sin líneas.
"""

from __future__ import annotations

import hashlib
import importlib
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures import reajuste_ob_s2 as rz
from ui.caso import ACCION_REGISTRAR_VALUACION, CLAVE_ACCION, CLAVE_PROYECTO
from ui.paginas.control import CLAVE_PESTANA, PESTANAS
from ui.texto_seguro import texto_seguro

SCRIPT = "from ui.paginas.control import render\n\nrender()\n"


def _caso(tmp_path: Path, *, linea_base=True, valuaciones=True, revaloracion=False) -> Path:
    ruta = tmp_path / "obra.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            if linea_base:
                ob.declarar_linea_base(sesion)
            if valuaciones:
                ob.registrar_v01_y_v02(sesion)
            if revaloracion:
                rz.sembrar_revaloracion(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


def _contar(ruta: Path, modelo) -> int:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return sesion.scalar(select(func.count()).select_from(modelo))
    finally:
        motor.dispose()


def _pantalla(monkeypatch, ruta: Path, estado=None, *, proyecto=ob.NOMBRE) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(ruta))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    if proyecto is not None:
        at.session_state[CLAVE_PROYECTO] = proyecto
    for clave, valor in (estado or {}).items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _pestana(at: AppTest, nombre: str) -> AppTest:
    at.session_state[CLAVE_PESTANA] = nombre
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _texto(at: AppTest) -> str:
    return " ".join(
        [m.value for m in at.markdown]
        + [c.value for c in at.caption]
        + [e.value for e in at.error]
        + [s.value for s in at.success]
        + [i.value for i in at.info]
        + [w.value for w in at.warning]
    )


def _tabla(at: AppTest, titulo_columna: str) -> list[dict]:
    for df in at.dataframe:
        if titulo_columna in df.value.columns:
            return df.value.to_dict("records")
    raise AssertionError(f"ninguna tabla trae la columna {titulo_columna!r}")


def test_sin_proyecto_abierto_pide_abrir_uno(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, _caso(tmp_path), proyecto=None)
    assert any("Abra un proyecto" in i.value for i in at.info)


def test_sin_linea_base_solo_ofrece_declararla_y_las_demas_pestanas_lo_dicen(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, _caso(tmp_path, linea_base=False, valuaciones=False))
    assert any("no tiene linea base de control" in i.value for i in at.info)
    for pestana in PESTANAS[1:]:
        _pestana(at, pestana)
        assert any("Declare primero la linea base" in i.value for i in at.info), pestana


def test_declarar_la_linea_base_desde_la_pantalla(monkeypatch, tmp_path):
    ruta = _caso(tmp_path, linea_base=False, valuaciones=False)
    at = _pantalla(monkeypatch, ruta)
    at.text_input(key="control_lb_desde").input("2026-11-02")
    at.text_input(key="control_lb_inicio").input("2026-11-02")
    at.text_input(key="control_lb_fuente").input(ob.FUENTE)
    at.text_input(key="control_lb_responsable").input(ob.RESPONSABLE)
    at.button(key="control_lb_declarar").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Linea base declarada." in s.value for s in at.success)
    assert _contar(ruta, models.LineaBaseControl) == 1
    vigente = next(m.value for m in at.markdown if "Linea base vigente" in m.value)
    assert "perspectiva costo" in vigente and texto_seguro("versión OB-001") in vigente


def test_una_linea_base_mal_declarada_se_muestra_como_error_y_no_escribe(monkeypatch, tmp_path):
    ruta = _caso(tmp_path, linea_base=False, valuaciones=False)
    at = _pantalla(monkeypatch, ruta)
    at.text_input(key="control_lb_desde").input("02/11/2026")
    at.button(key="control_lb_declarar").click().run()
    assert any("no es una fecha" in e.value for e in at.error)
    assert _contar(ruta, models.LineaBaseControl) == 0


def test_la_pestana_linea_base_muestra_la_vigente_y_los_parametros_con_su_naturaleza(
    monkeypatch, tmp_path
):
    at = _pantalla(monkeypatch, _caso(tmp_path))
    assert any("Linea base vigente" in m.value for m in at.markdown)
    filas = {f["Parametro"]: f for f in _tabla(at, "Naturaleza")}
    assert filas["spi_error"]["Valor"] == "0.90"
    assert filas["spi_error"]["Naturaleza"] == "SUPUESTO_DECLARADO"
    assert filas["penalizacion_diaria"]["Naturaleza"] == "DATO_DEL_CONTRATO"


def test_las_valuaciones_se_listan_con_su_fecha_de_registro_y_su_estado(monkeypatch, tmp_path):
    at = _pestana(_pantalla(monkeypatch, _caso(tmp_path)), "Valuaciones")
    filas = _tabla(at, "Registrada")
    assert [f["Numero"] for f in filas] == ["V-01", "V-02"]
    assert filas[0]["Registrada"] == "2026-11-09 09:00" and filas[0]["Estado"] == "sin hallazgos"
    assert "solo anularla la saca del calculo" in _texto(at)


def test_registrar_sin_lineas_se_rechaza_con_su_mensaje(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    at = _pestana(_pantalla(monkeypatch, ruta), "Valuaciones")
    at.text_input(key="control_v_numero").input("V-03")
    at.text_input(key="control_v_desde").input("2026-11-16")
    at.text_input(key="control_v_hasta").input("2026-11-20")
    at.text_input(key="control_v_fuente").input("acta")
    at.text_input(key="control_v_responsable").input("Ing.")
    at.button(key="control_v_registrar").click().run()
    assert any("al menos una linea" in e.value for e in at.error)
    assert _contar(ruta, models.Valuacion) == 2


def test_anular_una_valuacion_la_saca_de_la_lista_de_las_que_cuentan(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    at = _pestana(_pantalla(monkeypatch, ruta), "Valuaciones")
    at.selectbox(key="control_a_valuacion").select_index(1)
    at.text_input(key="control_a_motivo").input("no aprobada")
    at.text_input(key="control_a_responsable").input("Ing.")
    at.button(key="control_a_anular").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Valuacion anulada" in s.value for s in at.success)
    assert _contar(ruta, models.AnulacionValuacion) == 1
    assert [f["Numero"] for f in _tabla(at, "Registrada")] == ["V-01"]


def test_el_boton_de_la_barra_abre_la_pestana_valuaciones(monkeypatch, tmp_path):
    at = _pantalla(monkeypatch, _caso(tmp_path), {CLAVE_ACCION: ACCION_REGISTRAR_VALUACION})
    assert at.session_state[CLAVE_PESTANA] == "Valuaciones"
    assert any("Registrar una valuacion" in e.label for e in at.expander)


def test_valor_ganado_muestra_la_tabla_y_la_curva(monkeypatch, tmp_path):
    at = _pestana(_pantalla(monkeypatch, _caso(tmp_path)), "Valor ganado")
    filas = {f["Indicador"]: f for f in _tabla(at, "Indicador")}
    assert filas["PV (USD)"]["Valor"] == "1500.00" and filas["EV (USD)"]["Valor"] == "1200.00"
    assert filas["SPI"]["Valor"] == "0.8000" and filas["CPI"]["Valor"] == "0.9375"
    assert filas["Desvio de precio (USD)"]["Valor"] == "no disponible"  # sin precios del corte
    assert "definiciones del sistema (S2-R11)" in _texto(at)
    assert len(at.get("vega_lite_chart")) == 1


def test_con_la_comprobacion_directa_la_separacion_aparece(monkeypatch, tmp_path):
    at = _pestana(_pantalla(monkeypatch, _caso(tmp_path, revaloracion=True)), "Valor ganado")
    at.selectbox(key="control_metodo").select("Comprobacion directa (version revalorada)").run()
    at.selectbox(key="control_pc_version").select("OB-R01").run()
    assert not at.exception, [e.value for e in at.exception]
    filas = {f["Indicador"]: f for f in _tabla(at, "Indicador")}
    assert filas["Desvio de precio (USD)"]["Valor"] == "-60.00"
    assert filas["Desvio de consumo (USD)"]["Valor"] == "-20.00"


def test_alertas_y_reproyeccion_se_ven_al_abrir_sin_pedirlas(monkeypatch, tmp_path):
    at = _pestana(_pantalla(monkeypatch, _caso(tmp_path)), "Alertas y reproyección")
    alertas = {f["Alerta"]: f for f in _tabla(at, "Alerta")}
    assert alertas["AL-1"]["Severidad"] == "ERROR" and alertas["AL-3"]["Severidad"] == "ERROR"
    texto = _texto(at)
    assert "Termino por el plan reproyectado: día 23 (2026-12-02)" in texto
    assert "Termino por el indice: día 25 (2026-12-04)" in texto
    assert "Sin estudio de reajuste guardado: V' = V" in texto
    plan = _tabla(at, "OB-C")
    assert plan[2]["OB-C"] == "0.4000" and len(plan) == 5


def test_un_corte_con_un_costo_en_bs_sin_tasa_avisa_que_el_ac_no_esta_disponible(
    monkeypatch, tmp_path
):
    ruta = _caso(tmp_path)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    with abrir_sesion(motor) as sesion:
        from core.budget.valuaciones import registrar_costo

        registrar_costo(
            sesion, ob.NOMBRE, monto=ob.COSTO_REAL, moneda="Bs", fecha=date(2026, 11, 13),
            fuente="factura", responsable="Ing.",
        )  # fmt: skip
        sesion.commit()
    motor.dispose()
    at = _pestana(_pantalla(monkeypatch, ruta), "Valor ganado")
    assert any("no tiene tasa aplicable" in w.value for w in at.warning)
    filas = {f["Indicador"]: f for f in _tabla(at, "Indicador")}
    assert filas["AC (USD)"]["Valor"] == "no disponible"


def test_recuperacion_calcula_a_pedido_y_elegir_crea_la_version(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    at = _pestana(_pantalla(monkeypatch, ruta), "Recuperación")
    assert not at.dataframe  # nada se calcula hasta que se pide
    at.button(key="control_r_calcular").click().run()
    assert not at.exception, [e.value for e in at.exception]
    filas = {f["Opcion"]: f for f in _tabla(at, "Opcion")}
    assert filas["Mas cuadrillas"]["Termino"] == "día 17"
    assert filas["Partidas en paralelo"]["Nota"].startswith("ninguna partida sin empezar")
    assert any("art. 182" in c.value for c in at.caption)
    at.radio(key="control_r_elegida").set_value(
        next(o for o in at.radio(key="control_r_elegida").options if "cuadrillas" in o.lower())
    )
    at.text_input(key="control_r_fuente").input("decision ficticia")
    at.text_input(key="control_r_responsable").input("Ing.")
    at.button(key="control_r_elegir").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Version OB-002 creada" in s.value for s in at.success)
    assert _contar(ruta, models.DecisionRecuperacion) == 1
    assert [f["Version"] for f in _tabla(at, "Corte")] == ["OB-002"]


def test_elegir_sin_fuente_se_rechaza(monkeypatch, tmp_path):
    ruta = _caso(tmp_path)
    at = _pestana(_pantalla(monkeypatch, ruta), "Recuperación")
    at.button(key="control_r_calcular").click().run()
    at.button(key="control_r_elegir").click().run()
    assert any("obligatoria" in e.value for e in at.error)
    assert _contar(ruta, models.DecisionRecuperacion) == 0


def test_la_pantalla_no_escribe_en_la_base_real(monkeypatch, tmp_path):
    """Leer las pestañas de cálculo no escribe en el caso: el contenido del archivo (SHA-256) no
    cambia. `data/apu.db` la vigila además la salvaguarda de sesión de `tests/conftest.py`."""
    ruta = _caso(tmp_path)
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    at = _pantalla(monkeypatch, ruta)
    for pestana in PESTANAS[1:4]:  # Valuaciones, Valor ganado, Alertas y reproyección
        _pestana(at, pestana)
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes
