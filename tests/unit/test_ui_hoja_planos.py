"""Pantalla de la hoja: el flujo «Importar plano» de la pestana Espacio y metrajes (RF-50/51).

`AppTest` no sube archivos: la logica se prueba en `tests/unit/test_hoja_planos.py` con el
archivo en disco, y aqui el pintado, con la importacion ya leida y precargada en `st.session_state`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import ezdxf
import pytest
from streamlit.testing.v1 import AppTest

from ui import hoja
from ui.caso import ACCION_IMPORTAR_PLANO, CLAVE_ACCION
from ui.paginas.hoja import (
    CLAVE_ACCION_PENDIENTE,
    CLAVE_BORRADOR,
    CLAVE_IMPORTACION,
    CLAVE_PESTANA,
    CLAVE_PLANO,
)

SCRIPT = "from ui.paginas.hoja import render\nrender()\n"
RAIZ = Path(__file__).resolve().parents[2]
DXF = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"
IMPORTAR = "Importar plano (DXF o IFC)"
FUSIONAR = "Fusionar con el espacio del borrador"
CARGAR_ALTURAS = "Cargar alturas"
DECLARAR = "Declarar circuitos"
CONTINUAR = "Continuar con esta unidad"
DESCARTAR = "Descartar la importación"


def _arrancar(monkeypatch, tmp_path, **estado) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "no_existe.db"))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _boton(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def _hay_boton(at: AppTest, rotulo: str) -> bool:
    return any(b.label == rotulo for b in at.button)


def _metricas(at: AppTest) -> dict[str, str]:
    return {m.label: m.value for m in at.metric}


def _textos(at: AppTest) -> str:
    return " ".join(
        [m.value for m in at.markdown]
        + [c.value for c in at.caption]
        + [e.value for e in at.error]
        + [w.value for w in at.warning]
        + [s.value for s in at.success]
        + [i.value for i in at.info]
    )


def _cargado():
    return hoja.leer_plano(DXF)


# --- la accion de la barra lleva al flujo ------------------------------------------------------


def test_importar_plano_de_la_barra_lleva_a_espacio_y_metrajes_y_abre_el_flujo(
    monkeypatch, tmp_path
):
    at = _arrancar(
        monkeypatch,
        tmp_path,
        **{CLAVE_ACCION: ACCION_IMPORTAR_PLANO, CLAVE_PESTANA: "Auditoría"},
    )
    assert at.session_state[CLAVE_PESTANA] == "Espacio y metrajes"
    assert CLAVE_ACCION not in at.session_state
    assert CLAVE_ACCION_PENDIENTE not in at.session_state
    abierto = next(e for e in at.expander if e.label == IMPORTAR)
    assert abierto.proto.expanded is True


def test_sin_pedirlo_el_flujo_esta_plegado_y_dice_que_formatos_acepta(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path)
    plegado = next(e for e in at.expander if e.label == IMPORTAR)
    assert plegado.proto.expanded is False
    assert "DXF" in _textos(at) and "IFC" in _textos(at)


# --- el informe --------------------------------------------------------------------------------


def test_con_una_importacion_se_muestran_los_cuatro_conteos_y_el_informe(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: _cargado()})
    metricas = _metricas(at)
    assert metricas["Importado"] == "33" and metricas["No reconocido"] == "0"
    assert metricas["Aproximado"] == "9" and metricas["Pendiente"] == "6"
    informe = [d.value for d in at.dataframe if "Qué pasó" in list(d.value.columns)]
    assert len(informe) == 1 and len(informe[0]) == 48
    for interno in ("SF5", "esp_", "DA-SF"):
        assert interno not in _textos(at)


def test_la_importacion_rechazada_dice_el_motivo_y_no_ofrece_fusionar(monkeypatch, tmp_path):
    ruta = tmp_path / "roto.dxf"
    ruta.write_bytes(b"esto no es un dibujo")
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: hoja.leer_plano(ruta)})
    assert any("roto.dxf" in e.value for e in at.error)
    assert not _hay_boton(at, FUSIONAR)
    assert _hay_boton(at, DESCARTAR)


def test_la_importacion_detenida_pide_la_unidad_y_se_reanuda_con_ella(monkeypatch, tmp_path):
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 0
    ruta = tmp_path / "sin_unidad.dxf"
    doc.saveas(ruta)
    at = _arrancar(
        monkeypatch,
        tmp_path,
        **{CLAVE_IMPORTACION: hoja.leer_plano(ruta), CLAVE_PLANO: str(ruta)},
    )
    assert not _hay_boton(at, FUSIONAR)
    selector = next(s for s in at.selectbox if s.label == "Unidad del dibujo")
    assert list(selector.options) == list(hoja.UNIDADES_DE_PLANO)
    selector.select("cm")
    _boton(at, CONTINUAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[CLAVE_IMPORTACION].estado.value == "importada"
    assert _hay_boton(at, FUSIONAR)


# --- alturas y circuitos -----------------------------------------------------------------------


def test_se_piden_las_seis_alturas_pendientes_y_cargarlas_las_quita(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: _cargado()})
    alturas = [t for t in at.text_input if t.label.startswith("Altura de ")]
    assert len(alturas) == 6
    for campo in alturas:
        campo.set_value("2,50")
    _boton(at, CARGAR_ALTURAS).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not [t for t in at.text_input if t.label.startswith("Altura de ")]
    assert _metricas(at)["Pendiente"] == "0"
    assert {a.alto for a in at.session_state[CLAVE_IMPORTACION].ambientes} == {hoja.Decimal("2.5")}


def test_una_altura_invalida_se_dice_en_claro_y_no_se_carga_ninguna(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: _cargado()})
    campos = [t for t in at.text_input if t.label.startswith("Altura de ")]
    campos[0].set_value("2,50")
    campos[1].set_value("abc")
    _boton(at, CARGAR_ALTURAS).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("no es una altura valida" in e.value for e in at.error)
    assert len([t for t in at.text_input if t.label.startswith("Altura de ")]) == 6
    assert _metricas(at)["Pendiente"] == "6"


def test_los_circuitos_supuestos_se_declaran_y_dejan_de_ser_supuestos(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: _cargado()})
    puntos = [t for t in at.text_input if t.label.startswith("Puntos máximos del circuito ")]
    assert len(puntos) == 2
    puntos[0].set_value("8")
    _boton(at, DECLARAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not [t for t in at.text_input if t.label.startswith("Puntos máximos del circuito ")]
    declarado = {c.id: c.puntos_maximos for c in at.session_state[CLAVE_IMPORTACION].circuitos}
    assert declarado == {"C1": 8, "C2": 6}  # se confirman los dos: con lo escrito y lo propuesto
    assert hoja.circuitos_supuestos(at.session_state[CLAVE_IMPORTACION]) == []


def test_un_circuito_invalido_se_dice_en_claro(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: _cargado()})
    next(t for t in at.text_input if t.label == "Puntos máximos del circuito C2").set_value("0")
    _boton(at, DECLARAR).click().run()
    assert any("C2" in e.value for e in at.error)
    assert len(hoja.circuitos_supuestos(at.session_state[CLAVE_IMPORTACION])) == 2


# --- fusionar ----------------------------------------------------------------------------------


def test_fusionar_pasa_las_filas_al_borrador_sin_saltar_la_hoja(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: _cargado()})
    assert "provisionales" in _textos(at)  # lo pendiente se advierte antes de fusionar
    _boton(at, FUSIONAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    espacio = at.session_state[CLAVE_BORRADOR].espacio
    assert len(espacio.ambientes) == 6 and len(espacio.puntos) == 21
    assert CLAVE_IMPORTACION not in at.session_state
    assert any("borrador" in s.value for s in at.success)
    # la hoja y la auditoria las ven: los editores muestran las filas y el informe esta pintado
    assert len([d for d in at.dataframe if "Estado" in list(d.value.columns)]) == 3
    assert "Informe de auditoria" in " ".join(s.value for s in at.subheader)


def test_descartar_la_importacion_no_toca_el_borrador(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: _cargado()})
    antes = at.session_state[CLAVE_BORRADOR]
    _boton(at, DESCARTAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert CLAVE_IMPORTACION not in at.session_state
    assert at.session_state[CLAVE_BORRADOR] == antes


@pytest.mark.parametrize("rotulo", [FUSIONAR, DESCARTAR])
def test_los_botones_del_flujo_tienen_rotulos_que_el_usuario_reconoce(
    monkeypatch, tmp_path, rotulo
):
    at = _arrancar(monkeypatch, tmp_path, **{CLAVE_IMPORTACION: _cargado()})
    assert _hay_boton(at, rotulo)
