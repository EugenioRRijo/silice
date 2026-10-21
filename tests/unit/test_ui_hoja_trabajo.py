"""Interfaz de trabajo de la hoja y la barra (PLAN_SILICE_UI, tareas 5 y 6; RU-1: sin prueba
hasta la auditoría final, 2026-10-13).

* `ui.hoja.filtrar_partidas`: sin acentos ni mayúsculas, por código o descripción, el orden de
  entrada se conserva y un texto vacío deja todas;
* `ui.hoja.filas_de_cierre`: la cascada de `core.costing.motor.calcular_apu` paso a paso, con el
  oráculo a mano de OB-B (memoria `control_ob_s2.md` §1: materiales 3,00, equipos 30 × 0,10 / 20 =
  0,15, mano de obra (2 × 2,50 × 7 + 2) / 20 = 1,85; costo directo 5,00; con administración 5,75;
  precio unitario 6,325);
* `ui.caso.publicar_resumen` / `ui.barra.pintar_estado`: la línea de estado muestra el resumen de
  la hoja solo si es del proyecto abierto, y el marco la pinta en el mismo ciclo en que la
  pantalla lo publica;
* la pestaña APU en tres paneles (OF-001): el filtro que deja una partida, el filtro vacío, la
  partida elegida que desaparece del filtro (foco 4), un factor inválido, el cierre que cuadra con
  las métricas y el selector de insumo con su tope de 300.
Datos ficticios (NORMAS.md §1).
"""

from __future__ import annotations

import importlib
import shutil
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import preparar_base
from tests.fixtures import control_ob_s2 as ob
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from ui.caso import CLAVE_PROYECTO, CLAVE_RESUMEN, ResumenDeTrabajo
from ui.paginas.hoja import (
    CLAVE_BORRADOR,
    CLAVE_FILTRO_APU,
    CLAVE_GENERACION,
    CLAVE_PARTIDA_APU,
    CLAVE_PESTANA,
)
from ui.texto_seguro import texto_seguro

D = Decimal
SCRIPT_HOJA = "from ui.paginas.hoja import render\nrender()\n"


# --- filtrar_partidas ----------------------------------------------------------------------------

CODIGOS = ["AF-TUB-PVC-3/4", "EL-CAB-12", "DT-UTP-CAT-6", "SIN-DESC"]
DESCRIPCIONES = {
    "AF-TUB-PVC-3/4": "Tubería PVC 3/4 pulg de agua fría",
    "EL-CAB-12": "Cable ELÉCTRICO 12 AWG",
    "DT-UTP-CAT-6": "Cable UTP categoría 6",
}


# --- filas_de_cierre -----------------------------------------------------------------------------


# --- línea de estado de la barra -----------------------------------------------------------------

SCRIPT_ESTADO = """
import streamlit as st
from ui import barra, caso

resumen = st.session_state.get("resumen_de_prueba")
if resumen == "retirar":
    caso.publicar_resumen(None)
elif resumen is not None:
    caso.publicar_resumen(resumen)
st.session_state["publicado"] = caso.resumen_publicado()
barra.pintar_estado()
"""


@pytest.fixture
def caso_ob(tmp_path) -> Path:
    ruta = tmp_path / "obra.db"
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            ob.sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


def _estado(monkeypatch, ruta: Path, **sesion) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(ruta))
    at = AppTest.from_string(SCRIPT_ESTADO, default_timeout=60)
    for clave, valor in sesion.items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _resumen(proyecto=ob.NOMBRE, version: str | None = "OB-001") -> ResumenDeTrabajo:
    return ResumenDeTrabajo(
        proyecto, version, "borrador con 2 cambio(s) sin guardar", "5060.00 USD"
    )


def test_sin_proyecto_abierto_no_hay_linea_de_estado(monkeypatch, caso_ob):
    at = _estado(monkeypatch, caso_ob, resumen_de_prueba=_resumen())
    assert [c.value for c in at.caption] == []


def test_el_resumen_del_proyecto_abierto_muestra_version_estado_y_total(monkeypatch, caso_ob):
    at = _estado(monkeypatch, caso_ob, resumen_de_prueba=_resumen(), **{CLAVE_PROYECTO: ob.NOMBRE})
    assert [c.value for c in at.caption] == [
        "Version OB\\-001 · Estado: borrador con 2 cambio(s) sin guardar · Total: 5060\\.00 USD"
    ]


def test_un_resumen_sin_version_no_nombra_version(monkeypatch, caso_ob):
    at = _estado(
        monkeypatch,
        caso_ob,
        resumen_de_prueba=_resumen(version=None),
        **{CLAVE_PROYECTO: ob.NOMBRE},
    )
    assert [c.value for c in at.caption] == [
        "Estado: borrador con 2 cambio(s) sin guardar · Total: 5060\\.00 USD"
    ]


def test_el_resumen_de_otro_proyecto_no_se_atribuye_al_abierto(monkeypatch, caso_ob):
    at = _estado(
        monkeypatch, caso_ob, resumen_de_prueba=_resumen(proyecto="Otro"),
        **{CLAVE_PROYECTO: ob.NOMBRE},
    )  # fmt: skip
    assert [c.value for c in at.caption] == ["Version vigente OB\\-001 del 2026-11-02"]


def test_sin_resumen_ni_version_guardada_lo_dice(monkeypatch, caso_ob):
    motor = crear_motor(f"sqlite:///{caso_ob.as_posix()}")
    with abrir_sesion(motor) as sesion:
        from core.budget import crear_proyecto

        crear_proyecto(sesion, "Vacio")
        sesion.commit()
    motor.dispose()
    at = _estado(monkeypatch, caso_ob, **{CLAVE_PROYECTO: "Vacio"})
    assert [c.value for c in at.caption] == ["sin version guardada"]


def test_publicar_none_retira_el_resumen_y_un_valor_ajeno_no_cuenta(monkeypatch, caso_ob):
    at = _estado(monkeypatch, caso_ob, resumen_de_prueba=_resumen())
    assert at.session_state["publicado"] == _resumen()
    at.session_state["resumen_de_prueba"] = "retirar"
    at.run()
    assert at.session_state["publicado"] is None
    assert CLAVE_RESUMEN not in at.session_state
    otro = _estado(monkeypatch, caso_ob, **{CLAVE_RESUMEN: {"proyecto": ob.NOMBRE}})
    assert otro.session_state["publicado"] is None  # solo un `ResumenDeTrabajo` es un resumen


def test_un_nombre_de_version_con_markdown_va_escapado(monkeypatch, caso_ob):
    raro = ResumenDeTrabajo(ob.NOMBRE, "*v1* [x](y)", "guardada", "<b>1</b>")
    at = _estado(monkeypatch, caso_ob, resumen_de_prueba=raro, **{CLAVE_PROYECTO: ob.NOMBRE})
    (linea,) = [c.value for c in at.caption]
    assert texto_seguro("*v1* [x](y)") in linea and texto_seguro("<b>1</b>") in linea
    assert "*v1*" not in linea


SCRIPT_MARCO = """
import streamlit as st
from ui import caso
from ui.app import marco, pagina_por_ruta


def pintar():
    caso.publicar_resumen(
        caso.ResumenDeTrabajo(
            st.session_state[caso.CLAVE_PROYECTO], "OB-001", "guardada", "5060.00 USD"
        )
    )


marco(pagina_por_ruta("tablero"), pintar, lambda destino: None)
"""


def test_el_marco_pinta_el_resumen_que_la_pantalla_publica_en_el_mismo_ciclo(monkeypatch, caso_ob):
    """El hueco de la línea de estado se llena al final del marco: en la PRIMERA ejecución ya
    muestra lo que la pantalla publicó, no lo de la ejecución anterior."""
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(caso_ob))
    at = AppTest.from_string(SCRIPT_MARCO, default_timeout=120)
    at.session_state[CLAVE_PROYECTO] = ob.NOMBRE
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    linea = "Version OB\\-001 · Estado: guardada · Total: 5060\\.00 USD"
    assert linea in [c.value for c in at.main.caption]


# --- la hoja publica su resumen y la pestaña APU -------------------------------------------------


@pytest.fixture(scope="module")
def _plantilla_of(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("trabajo_of") / "of001.db")


@pytest.fixture
def base_of(_plantilla_of, tmp_path):
    copia = tmp_path / "of001.db"
    shutil.copy(_plantilla_of, copia)
    return copia


def _hoja(monkeypatch, base: Path, **estado) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT_HOJA, default_timeout=120)
    at.session_state[CLAVE_PROYECTO] = NOMBRE_OF001
    at.session_state[CLAVE_PESTANA] = "APU"
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _factor(at: AppTest, nombre: str):
    return at.text_input(key=f"hoja_editor_factor_{nombre}_{at.session_state[CLAVE_GENERACION]}")


def _cierre(at: AppTest) -> dict[str, str]:
    tabla = next(
        d.value for d in at.dataframe if list(d.value.columns) == ["Concepto", "Monto", "Nota"]
    )
    return dict(zip(tabla["Concepto"], tabla["Monto"], strict=True))


def _monto(texto: str) -> Decimal:
    return D(texto.split()[0])


def test_la_hoja_publica_su_resumen_guardada_y_luego_con_cambios(monkeypatch, base_of):
    at = _hoja(monkeypatch, base_of)
    resumen = at.session_state[CLAVE_RESUMEN]
    assert (resumen.proyecto, resumen.version, resumen.estado) == (NOMBRE_OF001, "001", "guardada")
    _factor(at, "fcas").set_value("7").run()
    resumen = at.session_state[CLAVE_RESUMEN]
    assert resumen.estado == "borrador con 1 cambio(s) sin guardar"


def test_un_borrador_nuevo_no_publica_resumen(monkeypatch, tmp_path):
    at = _hoja(monkeypatch, tmp_path / "no_existe.db", **{CLAVE_PROYECTO: None})
    assert CLAVE_RESUMEN not in at.session_state


def test_la_pestana_apu_tiene_tres_paneles_y_el_cierre_cuadra_con_las_metricas(
    monkeypatch, base_of
):
    at = _hoja(monkeypatch, base_of)
    radio = at.radio(key=CLAVE_PARTIDA_APU)
    assert len(radio.options) == 30 and radio.value == "AF-CODO-1/2"
    metricas = {m.label: _monto(m.value) for m in at.metric}
    cierre = {concepto: _monto(monto) for concepto, monto in _cierre(at).items()}
    assert cierre["= Precio unitario"] == metricas["Precio unitario"]
    for rubro in ("Materiales", "Equipos", "Mano de obra"):
        assert cierre[rubro] == metricas[rubro]
    # Cada «=» es la suma de lo anterior; los montos están redondeados, así que ± 0,01 por término.
    directo = cierre["Materiales"] + cierre["Equipos"] + cierre["Mano de obra"]
    assert abs(cierre["= Costo directo"] - directo) <= D("0.02")
    con_adm = cierre["= Costo directo"] + cierre["+ Administracion"]
    assert abs(cierre["= Con administracion"] - con_adm) <= D("0.01")
    precio = cierre["= Con administracion"] + cierre["+ Utilidad"]
    assert abs(cierre["= Precio unitario"] - precio) <= D("0.01")


def test_el_filtro_deja_una_partida_y_el_radio_toma_la_visible(monkeypatch, base_of):
    """Foco 4: la partida elegida (AF-CODO-1/2) desaparece del filtro; el radio no queda con un
    valor fuera de la lista y pasa a la única visible."""
    at = _hoja(monkeypatch, base_of)
    at.text_input(key=CLAVE_FILTRO_APU).input("breaker").run()
    assert not at.exception, [e.value for e in at.exception]
    radio = at.radio(key=CLAVE_PARTIDA_APU)
    assert radio.value == "EL-PROT"
    assert len(radio.options) == 1
    assert radio.options[0] == texto_seguro(
        "EL-PROT · Breaker de 1 polo x 20 A instalado en el tablero"
    )


def test_el_filtro_sin_coincidencias_muestra_todas_y_lo_dice(monkeypatch, base_of):
    at = _hoja(monkeypatch, base_of)
    at.text_input(key=CLAVE_FILTRO_APU).input("no existe ninguna").run()
    assert "Ninguna partida coincide; se muestran todas." in [c.value for c in at.caption]
    assert len(at.radio(key=CLAVE_PARTIDA_APU).options) == 30


def test_un_factor_invalido_se_dice_y_la_hoja_sigue_con_el_ultimo_valido(monkeypatch, base_of):
    at = _hoja(monkeypatch, base_of)
    antes = at.session_state[CLAVE_BORRADOR].parametros
    _factor(at, "utilidad").set_value("mucho").run()
    assert not at.exception
    assert any("utilidad" in e.value and "ultimos parametros validos" in e.value for e in at.error)
    assert at.session_state[CLAVE_BORRADOR].parametros == antes


def test_un_factor_valido_cambia_el_cierre_de_la_partida(monkeypatch, base_of):
    """Utilidad 0 → el precio unitario es el costo con administración."""
    at = _hoja(monkeypatch, base_of)
    _factor(at, "utilidad").set_value("0").run()
    assert at.session_state[CLAVE_BORRADOR].parametros.utilidad == D(0)
    cierre = _cierre(at)
    assert cierre["+ Utilidad"] == "0.00 USD"
    assert cierre["= Precio unitario"] == cierre["= Con administracion"]


def test_el_selector_de_insumo_ofrece_candidatos_y_usar_empieza_deshabilitado(monkeypatch, base_of):
    at = _hoja(monkeypatch, base_of)
    clave = f"hoja_editor_insumo_AF-CODO-1/2_{at.session_state[CLAVE_GENERACION]}"
    selector = at.selectbox(key=clave)
    assert selector.value is None and len(selector.options) >= 1
    usar = next(b for b in at.button if b.label == "Usar este insumo")
    assert usar.disabled is True
    assert not any(t.label.startswith("Hay mas de") for t in at.text_input)


def test_con_mas_candidatos_que_el_tope_pide_acotar(monkeypatch, base_of):
    """Corrección 6 de la revisión final: el aviso solo aparece si hay MÁS que el tope (se consulta
    tope + 1). Con tope 1 y al menos 2 materiales en la lista, aparece y pide acotar."""
    pantalla = importlib.import_module("ui.paginas.hoja")
    monkeypatch.setattr(pantalla, "LIMITE_INSUMOS", 1)
    at = _hoja(monkeypatch, base_of)
    avisos = [t for t in at.text_input if t.label.startswith("Hay mas de 1 insumos")]
    assert len(avisos) == 1
    clave = f"hoja_editor_insumo_AF-CODO-1/2_{at.session_state[CLAVE_GENERACION]}"
    assert len(at.selectbox(key=clave).options) == 1  # recortado al tope
