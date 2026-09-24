"""UC-01 3a en la pantalla de elaborar (INV-072, parte de `ui/`; D6 del plan de C3).

Un item del computo sin partida en el catalogo queda **pendiente**: el presupuesto se elabora con
los demas, el informe lo declara y la pantalla propone partidas similares, que el usuario puede
aceptar para volver a elaborar. La base vive en `tmp_path`, desviada por el objeto modulo
`sys.modules["ui.caso"]`; la salvaguarda de `tests/conftest.py` vigila `data/apu.db`.

Las propuestas se sustituyen por un doble parchado **donde la pagina las resuelve al llamarlas**
(`ui.elaboracion.propuestas_de_pendientes`): la similitud semantica real necesita el extra `ml`.
"""

from __future__ import annotations

import dataclasses
import importlib
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import ElementList

from core.budget import elaborar, plan_secuencial
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from scripts.seed import sembrar
from tests.fixtures.apu_linea_base import (
    MONEDA,
    PARAMETROS_LINEA_BASE,
    PRECIO_UNITARIO_EXACTO,
    TOTAL_EXACTO_LINEA_BASE,
)
from tests.fixtures.computo_auditado import composiciones_linea_base, items_auditados
from ui.elaboracion import aceptar_propuesta, propuestas_de_pendientes

SCRIPT = "from ui.paginas.elaborar import render\nrender()\n"

CLAVE_ITEMS = "elaborar_items"
CLAVE_RESULTADO = "elaborar_resultado"
ROTULO_ELABORAR = "Elaborar presupuesto"
ROTULO_APLICAR = "Aplicar y volver a elaborar"
CODIGO_PRESUPUESTO = "P-001"  # valor por defecto de la pantalla

#: Dos redondeos de presentacion (el total mostrado antes y despues) separan a lo sumo esto.
TOLERANCIA = Decimal(1).scaleb(-DECIMALES_PRESENTACION)

PENDIENTE_T99 = ItemComputo(
    codigo_partida="XX-99-NUE",
    descripcion="Tuberia de PVC de 4 pulgadas",
    # En `pieza`, la unidad de LB-02-TUB: aceptar la propuesta no agrega un hallazgo R3 ajeno.
    unidad="pieza",
    cantidad=Decimal("2"),
    origen_id="T-99",
    origen_tipo=OrigenTipo.MANUAL,
    dominio=Dominio.CIVIL,
)


def _items() -> list[ItemComputo]:
    return [*items_auditados(), PENDIENTE_T99]


def _propuestas_fijas(partidas, pendientes):
    """Doble de `ui.elaboracion.propuestas_de_pendientes`: dos propuestas fijas por pendiente."""
    from ml.normalization import PartidaSimilar
    from ui.elaboracion import PendienteConPropuestas

    return tuple(
        PendienteConPropuestas(
            item=pendiente,
            similares=(
                PartidaSimilar("LB-02-TUB", "Tuberia PVC 4 pulgadas", 0.91),
                PartidaSimilar("LB-01-EXC", "Excavacion", 0.55),
            ),
        )
        for pendiente in pendientes
    )


def _total_por_el_nucleo(items: list[ItemComputo]) -> str:
    """Oraculo por el nucleo directo, sin la pagina: el total formateado como lo presenta."""
    resultado = elaborar(
        items,
        composiciones_linea_base(),
        PARAMETROS_LINEA_BASE,
        codigo=CODIGO_PRESUPUESTO,
        fecha=date.today(),
        moneda=MONEDA,
        plan=plan_secuencial,
    )
    return formatear_decimal(resultado.presupuesto.total, DECIMALES_PRESENTACION)


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


def _elaborado(monkeypatch, base: Path) -> AppTest:
    """La pantalla con los items de la linea base mas T-99, tras pulsar «Elaborar presupuesto»."""
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    # `raising=False`: el rojo es el `st.error` de la pagina, no un AttributeError al preparar.
    monkeypatch.setattr("ui.elaboracion.propuestas_de_pendientes", _propuestas_fijas, raising=False)
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_ITEMS] = _items()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _total_mostrado(at: AppTest) -> str:
    return _por_rotulo(at.metric, "Total del presupuesto").value


def test_el_item_sin_partida_queda_pendiente_con_sus_propuestas(monkeypatch, base_sembrada):
    at = _elaborado(monkeypatch, base_sembrada)
    assert not at.error, [e.value for e in at.error]

    total = formatear_decimal(TOTAL_EXACTO_LINEA_BASE, DECIMALES_PRESENTACION)
    assert _total_mostrado(at) == f"{total} {MONEDA}"
    assert _total_mostrado(at) == f"{_total_por_el_nucleo(list(items_auditados()))} {MONEDA}"

    assert "Pendientes" in [s.value for s in at.subheader]
    textos = [m.value for m in at.markdown]
    assert any(t.startswith("**T-99**") and "XX-99-NUE" in t for t in textos), textos
    assert list(at.selectbox(key="elaborar_propuesta_0").options) == ["LB-02-TUB", "LB-01-EXC"]
    assert any("0.91" in t for t in textos) and any("0.55" in t for t in textos)
    assert any("PENDIENTE" in t for t in textos)  # el informe en markdown lo declara


# --- D6: aceptar una propuesta y volver a elaborar ------------------------------------------


def test_aceptar_una_propuesta_vuelve_a_elaborar_sin_pendientes(monkeypatch, base_sembrada):
    at = _elaborado(monkeypatch, base_sembrada)
    antes = Decimal(_total_mostrado(at).split()[0])

    at.selectbox(key="elaborar_propuesta_0").set_value("LB-02-TUB")
    at.button(key="elaborar_aplicar_0").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]

    assert at.session_state[CLAVE_RESULTADO].pendientes == ()
    assert "Pendientes" not in [s.value for s in at.subheader]
    aceptados = aceptar_propuesta(_items(), PENDIENTE_T99, "LB-02-TUB")
    assert _total_mostrado(at) == f"{_total_por_el_nucleo(aceptados)} {MONEDA}"
    # Aritmetica de la fixture: el total crece en 2 piezas x 10,1933700 USD de LB-02-TUB.
    despues = Decimal(_total_mostrado(at).split()[0])
    crecimiento = PENDIENTE_T99.cantidad * PRECIO_UNITARIO_EXACTO["LB-02-TUB"]
    assert abs((despues - antes) - crecimiento) <= TOLERANCIA


# --- aceptar_propuesta (pura) ---------------------------------------------------------------


def test_aceptar_cambia_solo_el_item_pendiente() -> None:
    items = _items()
    aceptados = aceptar_propuesta(items, PENDIENTE_T99, "LB-02-TUB")
    assert aceptados[:-1] == items[:-1]  # los demas, identicos
    assert aceptados[-1] == dataclasses.replace(PENDIENTE_T99, codigo_partida="LB-02-TUB")


def test_aceptar_un_item_que_no_esta_es_un_error() -> None:
    with pytest.raises(ValueError, match="T-99"):
        aceptar_propuesta(list(items_auditados()), PENDIENTE_T99, "LB-02-TUB")


# --- propuestas_de_pendientes (cuerpo provisional; 10c reescribe esta prueba) ----------------


def test_una_entrada_por_pendiente_en_su_orden(monkeypatch) -> None:
    from ml.normalization import PartidaSimilar

    llamadas: list[tuple[object, str]] = []

    def _doble(partidas, descripcion):
        llamadas.append((partidas, descripcion))
        return [PartidaSimilar(f"P-{descripcion}", descripcion, 0.5)]

    monkeypatch.setattr("ui.composicion.sugerir_partidas_similares", _doble)
    partidas = {"LB-02-TUB": "Tuberia PVC 4 pulgadas"}
    otro = dataclasses.replace(PENDIENTE_T99, origen_id="T-98", descripcion="Codo de PVC")
    entradas = propuestas_de_pendientes(partidas, [PENDIENTE_T99, otro])

    assert [entrada.item for entrada in entradas] == [PENDIENTE_T99, otro]
    assert [entrada.similares[0].codigo for entrada in entradas] == [
        f"P-{PENDIENTE_T99.descripcion}",
        "P-Codo de PVC",
    ]
    assert llamadas == [(partidas, PENDIENTE_T99.descripcion), (partidas, "Codo de PVC")]


def test_sin_pendientes_no_hay_propuestas_ni_se_carga_nada(monkeypatch) -> None:
    llamadas: list[object] = []
    monkeypatch.setattr(
        "ui.composicion.sugerir_partidas_similares", lambda *args: llamadas.append(args) or []
    )
    assert propuestas_de_pendientes({"LB-02-TUB": "Tuberia"}, []) == ()
    assert llamadas == []


# --- el fragmento sin propuestas: la regresion de componer (A-3) ----------------------------


def _fragmento(con_similares: bool) -> None:
    from datetime import date
    from decimal import Decimal

    from core.budget import elaborar
    from core.contracts import Dominio, ItemComputo, OrigenTipo
    from ml.normalization import PartidaSimilar
    from tests.fixtures.apu_linea_base import PARAMETROS_LINEA_BASE
    from tests.fixtures.computo_auditado import composiciones_linea_base, items_auditados
    from ui.elaboracion import PendienteConPropuestas
    from ui.resultado import mostrar_elaboracion

    pendiente = ItemComputo(
        codigo_partida="XX-99-NUE",
        descripcion="Tuberia de PVC de 4 pulgadas",
        unidad="pieza",
        cantidad=Decimal("2"),
        origen_id="T-99",
        origen_tipo=OrigenTipo.MANUAL,
        dominio=Dominio.CIVIL,
    )
    resultado = elaborar(
        [*items_auditados(), pendiente],
        composiciones_linea_base(),
        PARAMETROS_LINEA_BASE,
        codigo="P-001",
        fecha=date(2026, 4, 28),
    )
    similares = (PartidaSimilar("LB-02-TUB", "Tuberia PVC 4 pulgadas", 0.91),)
    propuestas = (
        (PendienteConPropuestas(item=pendiente, similares=similares),) if con_similares else ()
    )
    mostrar_elaboracion(
        resultado, b"", "presupuesto_P-001.xlsx", prefijo="prueba", propuestas=propuestas
    )


def test_sin_propuestas_el_fragmento_no_ofrece_selector() -> None:
    at = AppTest.from_function(_fragmento, kwargs={"con_similares": False}, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any(m.value.startswith("**T-99**") for m in at.markdown)
    assert len(at.selectbox) == 0
    assert ROTULO_APLICAR not in [boton.label for boton in at.button]

    at = AppTest.from_function(_fragmento, kwargs={"con_similares": True}, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.selectbox) == 1
