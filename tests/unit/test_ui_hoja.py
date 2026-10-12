"""Pantalla «Hoja del proyecto»: arranque de cada pestana y de cada accion (SF3, tareas 1.8 y 3.8).

`AppTest` no puede editar un `st.data_editor`: aqui se prueba el arranque de cada pestana (sin
excepcion, con lo que pinta), los botones, los formularios y los campos de texto, y los efectos en
la base. Las ediciones de celdas se cubren sembrando el borrador en `st.session_state` (el mismo
camino que sigue la pantalla despues de leer el editor) y, en `ui.hoja`, con pruebas directas
(`tests/unit/test_hoja_borrador.py`, `tests/integration/test_hoja_versiones.py`); lo que solo se
puede ver en un navegador (escribir en una celda, descargar el archivo) queda para la prueba
manual de `scripts/medir_data_editor.md` y la de aceptacion de Med.

La base se desvia a una copia temporal por el objeto modulo `sys.modules["ui.caso"]`; la
salvaguarda de `tests/conftest.py` vigila `data/apu.db`.
"""

from __future__ import annotations

import importlib
import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_motor
from tests.fixtures.espacio_bano import espacio_bano
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.hoja_en_base import (
    NOMBRE_OF001,
    NOMBRE_TI001,
    plantilla_of001,
    plantilla_ti001,
)
from ui import hoja
from ui.paginas.hoja import (
    CLAVE_ABIERTA,
    CLAVE_BORRADOR,
    CLAVE_EXCEL,
    CLAVE_FUENTE,
    CLAVE_GENERACION,
    CLAVE_PARTIDA,
    CLAVE_PESTANA,
    CLAVE_PROYECTO,
    CLAVE_RESPONSABLE,
    PESTANAS,
    SIN_PROYECTO,
)

SCRIPT = "from ui.paginas.hoja import render\nrender()\n"
D = Decimal


def _desviar(monkeypatch, base: Path) -> None:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))


def _arrancar(monkeypatch, base: Path, borrador=None, **estado) -> AppTest:
    _desviar(monkeypatch, base)
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    if borrador is not None:
        at.session_state[CLAVE_BORRADOR] = borrador
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _borrador(espacio) -> hoja.Borrador:
    from datetime import date

    return hoja.Borrador(fecha=date(2026, 10, 5), espacio=espacio)


# ---------------------------------------------------------------------------------------------
# Sin version: el borrador nuevo (comportamiento de la tarea 1.8)
# ---------------------------------------------------------------------------------------------


def test_la_pantalla_arranca_con_el_borrador_vacio(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path / "no_existe.db")
    # los cinco editores: origenes, ambientes, fuentes, puntos y vertices de recorridos
    assert len(at.dataframe) == 5
    assert at.info  # sin espacio no hay cantidades derivadas: la pantalla lo dice


def test_la_pantalla_no_crea_la_base_si_no_existe(monkeypatch, tmp_path):
    base = tmp_path / "no_existe.db"
    _arrancar(monkeypatch, base)
    assert not base.exists()


def test_el_bano_sembrado_muestra_cantidades_derivadas_y_el_informe(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path / "no_existe.db", _borrador(espacio_bano()))
    texto = " ".join(m.value for m in at.markdown)
    assert "AF-TUB-PVC-3/4" in texto or any("AF-TUB-PVC-3/4" in str(d.value) for d in at.dataframe)
    assert "Informe de auditoria" in " ".join(s.value for s in at.subheader)
    assert "R8" in texto  # el informe declara las reglas del espacio


def test_el_estado_va_fuera_de_los_editores(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path / "no_existe.db", _borrador(espacio_bano()))
    estados = [d for d in at.dataframe if "Estado" in list(d.value.columns)]
    assert len(estados) == 3  # ambientes, fuentes y puntos


def test_las_pestanas_son_las_nueve_de_la_spec_y_la_primera_es_espacio_y_metrajes():
    assert PESTANAS == (
        "Espacio y metrajes",
        "APU",
        "Presupuesto",
        "Plan y curva",
        "Punto de equilibrio",
        "Precios",
        "Parámetros",
        "Auditoría",
        "Trazabilidad",
    )


def test_la_oficina_sembrada_muestra_las_tres_especialidades(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path / "no_existe.db", _borrador(espacio_of001()))
    cantidades = [d.value for d in at.dataframe if "Partida" in list(d.value.columns)]
    assert len(cantidades) == 1
    partidas = set(cantidades[0]["Partida"])
    assert {"AF-TUB-PVC-3/4", "DR-TUB-PVC-2", "DT-UTP-CAT-6", "EL-COND-12-AWG"} <= partidas
    estados = [d for d in at.dataframe if "Estado" in list(d.value.columns)]
    assert len(estados) == 3


@pytest.mark.parametrize("pestana", PESTANAS)
def test_cada_pestana_arranca_sin_version_y_sin_base(monkeypatch, tmp_path, pestana):
    at = _arrancar(
        monkeypatch,
        tmp_path / "no_existe.db",
        _borrador(espacio_bano()),
        **{CLAVE_PESTANA: pestana},
    )
    assert not at.exception and not at.error, [e.value for e in at.error]


def test_sin_version_guardar_esta_deshabilitado_y_dice_por_que(monkeypatch, tmp_path):
    at = _arrancar(monkeypatch, tmp_path / "no_existe.db", _borrador(espacio_bano()))
    guardar = next(b for b in at.button if b.label == "Guardar version")
    assert guardar.disabled


# ---------------------------------------------------------------------------------------------
# Con una version abierta de OF-001
# ---------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _plantilla_of(tmp_path_factory):
    return plantilla_of001(tmp_path_factory.mktemp("ui_of") / "of001.db")


@pytest.fixture(scope="module")
def _plantilla_ti(tmp_path_factory):
    return plantilla_ti001(tmp_path_factory.mktemp("ui_ti") / "ti001.db")


@pytest.fixture
def base_of(_plantilla_of, tmp_path):
    copia = tmp_path / "of001.db"
    shutil.copy(_plantilla_of, copia)
    return copia


@pytest.fixture
def base_ti(_plantilla_ti, tmp_path):
    copia = tmp_path / "ti001.db"
    shutil.copy(_plantilla_ti, copia)
    return copia


def _abrir_of(monkeypatch, base, **estado) -> AppTest:
    return _arrancar(monkeypatch, base, **{CLAVE_PROYECTO: NOMBRE_OF001, **estado})


def _version(at: AppTest):
    """El selector de version (su clave cambia al abrir otra: se busca por su rotulo)."""
    return next(s for s in at.selectbox if s.label == "Version")


def _contar(base: Path, entidad) -> int:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return sesion.scalar(select(func.count()).select_from(entidad))
    finally:
        motor.dispose()


def test_la_pantalla_abre_la_version_vigente_del_proyecto_elegido(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of)

    abierta = at.session_state[CLAVE_ABIERTA]
    assert (abierta.proyecto, abierta.codigo) == (NOMBRE_OF001, "001")
    assert at.session_state[CLAVE_BORRADOR].espacio == espacio_of001()
    assert not at.warning  # sin ediciones no hay aviso de cambios sin guardar


@pytest.mark.parametrize("pestana", PESTANAS)
def test_cada_pestana_arranca_con_la_version_de_of001_abierta(monkeypatch, base_of, pestana):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: pestana})

    assert not at.exception and not at.error, [e.value for e in at.error]


def test_la_pestana_punto_de_equilibrio_dice_donde_se_alcanza(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Punto de equilibrio"})

    assert any(i.value.startswith("Se alcanza en Dia") for i in at.info)
    etiquetas = {m.label for m in at.metric}
    assert {"Ventas (contrato)", "Costo variable", "Costo fijo", "Punto de equilibrio"} <= etiquetas


def test_la_pestana_apu_pinta_el_precio_unitario_de_la_partida(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "APU"})

    assert "Precio unitario" in {m.label for m in at.metric}
    assert len([d for d in at.dataframe]) >= 3  # materiales, mano de obra y equipos


def test_la_pestana_presupuesto_pinta_pu_total_y_estado_aparte_del_editor(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Presupuesto"})

    calculado = next(d.value for d in at.dataframe if "Precio unitario" in d.value.columns)
    assert list(calculado.columns) == ["Partida", "Cantidad", "Precio unitario", "Total", "Estado"]
    assert len(calculado) == 30
    total = next(m for m in at.metric if m.label == "Total del presupuesto")
    assert total.value.startswith("2703.8") or total.value.startswith("2703.9")


def test_una_cantidad_escrita_se_marca_en_el_estado_del_presupuesto(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Presupuesto"})
    borrador = at.session_state[CLAVE_BORRADOR]
    items = hoja.items_sin_escribir(borrador)
    llave = next(
        c
        for c, i in zip(hoja.claves_de_items(items), items, strict=True)
        if i.codigo_partida == "AF-LLAVE"
    )

    editado = replace(borrador, cantidades={llave: D("9")})
    at.session_state[CLAVE_BORRADOR] = editado
    at.session_state[CLAVE_PARTIDA] = editado  # el editor se siembra con el borrador vigente
    at.run()

    calculado = next(d.value for d in at.dataframe if "Precio unitario" in d.value.columns)
    fila = calculado[calculado["Partida"] == "AF-LLAVE"].iloc[0]
    assert fila["Cantidad"] == "9" and "fijada a mano" in fila["Estado"]
    assert at.warning and "cambios sin guardar" in at.warning[0].value


def test_la_pestana_plan_y_curva_pinta_la_curva_que_cierra_en_el_total(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Plan y curva"})

    curva = next(d.value for d in at.dataframe if "% acumulado" in d.value.columns)
    assert list(curva["% acumulado"])[-1] == "100.00"


def test_la_pestana_precios_muestra_el_origen_y_marca_los_que_no_tienen_fuente(
    monkeypatch, base_of
):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Precios"})

    tabla = next(d.value for d in at.dataframe if "Referencia" in d.value.columns)
    assert len(tabla) > 10
    assert {"Lista", "Moneda", "Fecha del precio", "Tasa", "Fecha de la tasa"} <= set(tabla.columns)
    assert all("Sin referencia" in e for e in tabla["Estado"])


def test_la_pestana_auditoria_lista_los_hallazgos_con_su_origen(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Auditoría"})

    detalle = next(d.value for d in at.dataframe if "Origen" in d.value.columns)
    assert set(detalle["Regla"]) - {"R11", "R12"} == {"R8"}
    assert (detalle["Regla"] == "R8").sum() == 33


def test_la_pestana_trazabilidad_lista_las_versiones(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Trazabilidad"})

    versiones = next(d.value for d in at.dataframe if "Vigente" in d.value.columns)
    assert list(versiones["Version"]) == ["001"] and list(versiones["Vigente"]) == ["si"]


# --- parametros: campos de texto -----


def _campo(at: AppTest, nombre: str):
    generacion = at.session_state[CLAVE_GENERACION]
    return at.text_input(key=f"hoja_editor_param_{nombre}_{generacion}")


def test_cambiar_el_fcas_recalcula_y_deja_cambios_sin_guardar(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    antes = next(m for m in at.metric if m.label == "Total del presupuesto").value

    _campo(at, "fcas").set_value("7").run()

    despues = next(m for m in at.metric if m.label == "Total del presupuesto").value
    assert despues != antes
    assert at.session_state[CLAVE_BORRADOR].parametros.fcas == D("7")
    assert any("1 cambios sin guardar" in w.value for w in at.warning)


def test_un_parametro_invalido_dice_cual_y_conserva_el_ultimo_valido(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    _campo(at, "fcas").set_value("7").run()

    _campo(at, "utilidad").set_value("mucho").run()

    assert not at.exception
    assert any("utilidad" in e.value and "ultimos parametros validos" in e.value for e in at.error)
    assert at.session_state[CLAVE_BORRADOR].parametros.fcas == D("7")  # el ultimo valido
    assert at.session_state[CLAVE_BORRADOR].parametros.utilidad == D("0.10")


# --- guardar -----


def _guardar(at: AppTest, fuente="memoria rev. D", responsable="Ing. Prueba") -> AppTest:
    at.text_input(key=CLAVE_FUENTE).set_value(fuente)
    at.text_input(key=CLAVE_RESPONSABLE).set_value(responsable)
    at.run()
    return at


def test_guardar_exige_fuente_y_responsable_y_luego_crea_la_version(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    _campo(at, "administracion").set_value("0.20").run()
    guardar = next(b for b in at.button if b.label == "Guardar version")
    assert guardar.disabled  # sin fuente ni responsable
    assert "fuente" in guardar.help.lower()

    _guardar(at, fuente="", responsable="Ing. Prueba")
    assert next(b for b in at.button if b.label == "Guardar version").disabled
    _guardar(at)
    guardar = next(b for b in at.button if b.label == "Guardar version")
    assert not guardar.disabled
    guardar.click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("Se guardo la version 002 con 1 cambios" in s.value for s in at.success)
    assert _contar(base_of, models.Presupuesto) == 2
    assert _contar(base_of, models.RegistroCambio) == 1
    # la pantalla reabre la version nueva y ya no hay cambios sin guardar
    assert at.session_state[CLAVE_ABIERTA].codigo == "002"
    assert not at.warning
    assert at.session_state[CLAVE_BORRADOR].parametros.administracion == D("0.20")


def test_cambiar_de_version_con_cambios_pide_confirmar_y_no_los_descarta_solo(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    _campo(at, "fcas").set_value("7").run()
    _guardar(at)
    next(b for b in at.button if b.label == "Guardar version").click().run()
    _campo(at, "fcas").set_value("8").run()  # cambios nuevos sobre la 002

    _version(at).select("001").run()

    assert any(
        "cambios sin guardar. Si abre otra version se pierden" in w.value for w in at.warning
    )
    assert at.session_state[CLAVE_ABIERTA].codigo == "002"  # sigue la 002 con sus cambios
    assert at.session_state[CLAVE_BORRADOR].parametros.fcas == D("8")
    next(b for b in at.button if b.label.startswith("Descartar los cambios")).click().run()
    assert at.session_state[CLAVE_ABIERTA].codigo == "001"
    assert at.session_state[CLAVE_BORRADOR].parametros.fcas == D("6.00")


def test_seguir_editando_devuelve_los_selectores_a_la_version_abierta(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    _campo(at, "fcas").set_value("7").run()
    _guardar(at)
    next(b for b in at.button if b.label == "Guardar version").click().run()
    _campo(at, "fcas").set_value("8").run()
    _version(at).select("001").run()

    next(b for b in at.button if b.label == "Seguir editando").click().run()

    assert _version(at).value == "002"
    assert at.session_state[CLAVE_BORRADOR].parametros.fcas == D("8")
    assert not [b for b in at.button if b.label == "Seguir editando"]


def test_un_guardado_que_falla_dice_que_paso_y_no_deja_nada(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    _campo(at, "fcas").set_value("7").run()
    _guardar(at)
    # un borrador cuyo plan no reparte lo que el presupuesto tiene: la version no se puede crear
    borrador = at.session_state[CLAVE_BORRADOR]
    abierta = at.session_state[CLAVE_ABIERTA]
    fantasma = replace(abierta, solo_lectura=True)
    at.session_state[CLAVE_ABIERTA] = fantasma
    at.session_state[CLAVE_BORRADOR] = borrador
    at.run()

    guardar = next(b for b in at.button if b.label == "Guardar version")
    assert guardar.disabled  # solo lectura: el boton ni se ofrece
    assert any("solo lectura" in w.value for w in at.warning)
    assert _contar(base_of, models.Presupuesto) == 1


# --- exportar -----


def test_el_excel_se_genera_solo_al_pulsar_preparar_y_se_ofrece_para_descargar(
    monkeypatch, base_of
):
    at = _abrir_of(monkeypatch, base_of)
    assert CLAVE_EXCEL not in at.session_state  # nada se genera mientras no se pide
    assert not at.get("download_button")

    next(b for b in at.button if b.label == "Preparar Excel").click().run()

    assert not at.exception, [e.value for e in at.exception]
    nombre, contenido = at.session_state[CLAVE_EXCEL]
    assert nombre == "hoja_001.xlsx" and contenido[:2] == b"PK"  # un .xlsx es un zip
    assert len(at.get("download_button")) == 1


def test_editar_despues_de_preparar_descarta_el_excel_que_ya_no_es_el_vigente(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    next(b for b in at.button if b.label == "Preparar Excel").click().run()

    _campo(at, "fcas").set_value("7").run()

    assert CLAVE_EXCEL not in at.session_state
    assert not at.get("download_button")


def test_la_accion_exportar_de_la_barra_prepara_el_excel(monkeypatch, base_of):
    from ui.caso import ACCION_EXPORTAR_EXCEL, CLAVE_ACCION

    at = _abrir_of(monkeypatch, base_of, **{CLAVE_ACCION: ACCION_EXPORTAR_EXCEL})

    assert at.session_state[CLAVE_EXCEL][0] == "hoja_001.xlsx"


def test_la_accion_precios_de_la_barra_lleva_a_la_pestana_precios(monkeypatch, base_of):
    from ui.caso import ACCION_PRECIOS, CLAVE_ACCION

    at = _abrir_of(monkeypatch, base_of, **{CLAVE_ACCION: ACCION_PRECIOS})

    assert at.session_state[CLAVE_PESTANA] == "Precios"
    assert any("Referencia" in d.value.columns for d in at.dataframe)


# --- precios: cotizar y retirar -----


def _llenar_cotizacion(at: AppTest, precio: str, proveedor="Ferreteria Los Andes") -> None:
    formulario = {t.label: t for t in at.text_input}
    formulario["Precio cotizado"].set_value(precio)
    formulario["Proveedor"].set_value(proveedor)
    formulario["Numero de la cotizacion"].set_value("COT-77")
    formulario["Responsable"].set_value("Ing. Prueba")


def test_cotizar_desde_la_pestana_precios_crea_la_version_y_conserva_el_plan(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Precios"})
    plan = at.session_state[CLAVE_BORRADOR].plan
    precio = next(d.value for d in at.dataframe if "Referencia" in d.value.columns)["Precio"].iloc[
        0
    ]

    _llenar_cotizacion(at, str(D(precio) * 2))
    next(b for b in at.button if b.label == "Cotizar").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("Se guardo la version 002" in s.value for s in at.success)
    assert _contar(base_of, models.Cotizacion) == 1
    assert at.session_state[CLAVE_ABIERTA].codigo == "002"
    assert at.session_state[CLAVE_BORRADOR].plan == plan
    tabla = next(d.value for d in at.dataframe if "Cotizacion" in d.value.columns)
    assert list(tabla["Cotizacion"]).count("") == len(tabla) - 1  # una sola cotizada
    assert any(f.startswith("Ferreteria Los Andes") for f in tabla["Cotizacion"])
    # y se puede retirar
    next(b for b in at.button if b.label == "Retirar cotizacion")
    formulario = {t.label: t for t in at.text_input}
    formulario["Por que se retira"].set_value("el proveedor retiro la oferta")
    formulario["Responsable "].set_value("Ing. Prueba")
    next(b for b in at.button if b.label == "Retirar cotizacion").click().run()
    assert any("Se guardo la version 003" in s.value for s in at.success)


def test_una_cotizacion_sin_proveedor_se_rechaza_con_mensaje_y_no_guarda(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Precios"})

    _llenar_cotizacion(at, "999", proveedor="")
    next(b for b in at.button if b.label == "Cotizar").click().run()

    assert any("proveedor" in e.value and "No se guardo nada" in e.value for e in at.error)
    assert _contar(base_of, models.Presupuesto) == 1


def test_con_cambios_pendientes_no_se_ofrece_cotizar(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Precios"})
    borrador = at.session_state[CLAVE_BORRADOR]
    at.session_state[CLAVE_BORRADOR] = replace(
        borrador, parametros=replace(borrador.parametros, fcas=D("7"))
    )
    at.run()

    assert not [b for b in at.button if b.label == "Cotizar"]
    assert any("guarde o descarte primero" in w.value for w in at.warning)


# --- trazabilidad: restaurar -----


def test_restaurar_desde_trazabilidad_crea_una_copia_y_la_deja_vigente(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    _campo(at, "fcas").set_value("7").run()
    _guardar(at)
    next(b for b in at.button if b.label == "Guardar version").click().run()
    at.session_state[CLAVE_PESTANA] = "Trazabilidad"
    at.run()
    registros = next(d.value for d in at.dataframe if "Antes" in d.value.columns)
    assert list(registros["Campo"]) == ["valor"] and list(registros["Despues"]) == ["7"]

    formulario = {t.label: t for t in at.text_input}
    formulario["Fuente (por que se restaura)"].set_value("el FCAS de 7 no fue aprobado")
    formulario["Responsable"].set_value("Ing. Prueba")
    at.selectbox[-1].select("001")
    next(b for b in at.button if b.label == "Restaurar").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("La version 001 se restauro como la version 003" in s.value for s in at.success)
    assert _contar(base_of, models.Presupuesto) == 3  # nada se borra
    assert at.session_state[CLAVE_ABIERTA].codigo == "003"
    assert at.session_state[CLAVE_BORRADOR].parametros.fcas == D("6.00")


def test_restaurar_sin_fuente_se_rechaza(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Parámetros"})
    _campo(at, "fcas").set_value("7").run()
    _guardar(at)
    next(b for b in at.button if b.label == "Guardar version").click().run()
    at.session_state[CLAVE_PESTANA] = "Trazabilidad"
    at.run()

    at.selectbox[-1].select("001")
    next(b for b in at.button if b.label == "Restaurar").click().run()

    assert any("fuente" in e.value for e in at.error)
    assert _contar(base_of, models.Presupuesto) == 2


# --- plan sin plan, clinica y TI-001 -------------------------------- ---


def test_una_version_sin_plan_ofrece_crear_el_plan_secuencial(monkeypatch, base_of):
    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Plan y curva"})
    borrador = at.session_state[CLAVE_BORRADOR]
    at.session_state[CLAVE_BORRADOR] = replace(borrador, plan=None)
    at.run()
    assert any("no tiene plan" in i.value for i in at.info)

    next(b for b in at.button if b.label.startswith("Crear plan secuencial")).click().run()

    assert at.session_state[CLAVE_BORRADOR].plan is not None
    assert any("% acumulado" in d.value.columns for d in at.dataframe)


def test_ti001_abre_con_su_plan_y_su_punto_de_equilibrio(monkeypatch, base_ti):
    at = _arrancar(
        monkeypatch, base_ti, **{CLAVE_PROYECTO: NOMBRE_TI001, CLAVE_PESTANA: "Punto de equilibrio"}
    )

    assert at.session_state[CLAVE_ABIERTA].codigo == "TI-001"
    assert any("Se alcanza en Dia 6" in i.value for i in at.info)
    pe = next(m for m in at.metric if m.label == "Punto de equilibrio")
    assert pe.value.startswith("28586.7")


def test_abrir_ti001_en_la_pantalla_no_crea_versiones_ni_filas_de_espacio(monkeypatch, base_ti):
    """Abrir el caso lo adopta por `preparar_base` (RV-5): las tablas `esp_*` nacen vacias, pero
    abrir la pantalla no guarda ninguna version ni escribe filas de espacio."""
    _arrancar(monkeypatch, base_ti, **{CLAVE_PROYECTO: NOMBRE_TI001})

    assert _contar(base_ti, models.Presupuesto) == 1
    motor = crear_motor(f"sqlite:///{base_ti.as_posix()}")
    try:
        from sqlalchemy import inspect

        tablas_esp = [t for t in inspect(motor).get_table_names() if t.startswith("esp_")]
        assert tablas_esp, "preparar_base adopta el caso con el esquema completo"
        with motor.connect() as conexion:
            filas = {
                t: conexion.exec_driver_sql(f'SELECT count(*) FROM "{t}"').scalar()
                for t in tablas_esp
            }
        assert set(filas.values()) == {0}, filas
    finally:
        motor.dispose()


def test_proyecto_nuevo_sin_version_muestra_el_borrador_vacio(monkeypatch, base_of):
    at = _arrancar(monkeypatch, base_of, **{CLAVE_PROYECTO: SIN_PROYECTO})

    assert CLAVE_ABIERTA not in at.session_state or at.session_state[CLAVE_ABIERTA] is None
    assert at.session_state[CLAVE_BORRADOR].espacio.ambientes == ()


# --- SF4: acciones que pide la barra superior --------------------------------------------------


def test_la_accion_precios_de_la_barra_elige_la_pestana_precios_si_existe(monkeypatch, tmp_path):
    from ui.caso import ACCION_PRECIOS, CLAVE_ACCION
    from ui.paginas import hoja as pantalla

    monkeypatch.setattr(pantalla, "PESTANAS", ("Espacio y metrajes", "Precios"))
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "no_existe.db"))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_ACCION] = ACCION_PRECIOS
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[pantalla.CLAVE_PESTANA] == "Precios"
    assert CLAVE_ACCION not in at.session_state  # la accion se consume


def test_la_accion_precios_sin_pestana_precios_no_cambia_la_pestana(monkeypatch, tmp_path):
    from ui.caso import ACCION_PRECIOS, CLAVE_ACCION
    from ui.paginas import hoja as pantalla

    monkeypatch.setattr(pantalla, "PESTANAS", ("Espacio y metrajes", "APU"))
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "no_existe.db"))
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_ACCION] = ACCION_PRECIOS
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state[pantalla.CLAVE_PESTANA] == pantalla.PESTANAS[0]
    assert CLAVE_ACCION not in at.session_state
