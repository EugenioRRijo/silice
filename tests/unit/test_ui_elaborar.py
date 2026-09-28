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
    FECHA_LINEA_BASE,
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
        fecha=FECHA_LINEA_BASE,  # metadato del presupuesto: no entra en el total
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
    # Sin `raising=False` (Q-4 de la revision de A4): si la funcion cambiara de nombre, el parche
    # fallaria aqui en vez de fijar en silencio un atributo que la pagina no llama.
    monkeypatch.setattr("ui.elaboracion.propuestas_de_pendientes", _propuestas_fijas)
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


# --- propuestas_de_pendientes: `ml.normalization.propuestas_para` (INV-081, 10c) -------------


def _normalizador_contado(construcciones: list[dict[str, str]], falla: Exception | None = None):
    """Doble de `NormalizadorPartidas` en su submodulo (donde lo resuelve `proponedor`): cuenta
    construcciones y propone `P-<descripcion>`; con `falla`, la lanza al consultar."""
    from ml.normalization import PartidaSimilar

    class _Doble:
        def __init__(self, partidas):
            construcciones.append(dict(partidas))

        def similares(self, descripcion):
            if falla is not None:
                raise falla
            return [PartidaSimilar(f"P-{descripcion}", descripcion, 0.5)]

    return _Doble


def test_una_entrada_por_pendiente_en_su_orden_con_un_solo_normalizador(monkeypatch) -> None:
    construcciones: list[dict[str, str]] = []
    monkeypatch.setattr(
        "ml.normalization.normalizador.NormalizadorPartidas", _normalizador_contado(construcciones)
    )
    partidas = {"LB-02-TUB": "Tuberia PVC 4 pulgadas"}
    otro = dataclasses.replace(PENDIENTE_T99, origen_id="T-98", descripcion="Codo de PVC")
    entradas = propuestas_de_pendientes(partidas, [PENDIENTE_T99, otro])

    assert [entrada.item for entrada in entradas] == [PENDIENTE_T99, otro]
    assert [entrada.similares[0].codigo for entrada in entradas] == [
        f"P-{PENDIENTE_T99.descripcion}",
        "P-Codo de PVC",
    ]
    assert [entrada.falla for entrada in entradas] == [None, None]
    assert construcciones == [partidas]  # un solo normalizador por elaboracion


def test_sin_pendientes_no_hay_propuestas_ni_se_carga_nada(monkeypatch) -> None:
    construcciones: list[dict[str, str]] = []
    monkeypatch.setattr(
        "ml.normalization.normalizador.NormalizadorPartidas", _normalizador_contado(construcciones)
    )
    assert propuestas_de_pendientes({"LB-02-TUB": "Tuberia"}, []) == ()
    assert construcciones == []


def test_una_falla_declarada_queda_en_la_entrada_del_pendiente(monkeypatch) -> None:
    """El extra ausente llega como `ModuleNotFoundError`; la entrada lo declara `ImportError`."""

    def _sin_extra(*_args, **_kwargs):
        raise ModuleNotFoundError("No module named 'sentence_transformers'")

    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _sin_extra)
    (entrada,) = propuestas_de_pendientes({"LB-02-TUB": "Tuberia"}, [PENDIENTE_T99])

    assert entrada.item == PENDIENTE_T99
    assert entrada.similares == ()
    assert entrada.falla.startswith("ImportError: No module named")


# --- el fragmento sin propuestas: la regresion de componer (A-3) ----------------------------


def _fragmento(variante: str) -> None:
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
    propuestas = {
        # la pagina de componer: no propone
        "ninguna": (),
        # produccion sin el extra `ml`: una entrada sin similares (Q-1 de la revision de A4)
        "sin_similares": (
            PendienteConPropuestas(item=pendiente, falla="ImportError: falta el extra ml"),
        ),
        "con_similares": (PendienteConPropuestas(item=pendiente, similares=similares),),
    }[variante]
    mostrar_elaboracion(
        resultado, b"", "presupuesto_P-001.xlsx", prefijo="prueba", propuestas=propuestas
    )


def test_sin_propuestas_el_fragmento_no_ofrece_selector() -> None:
    for variante in ("ninguna", "sin_similares"):
        at = AppTest.from_function(_fragmento, kwargs={"variante": variante}, default_timeout=60)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        assert any(m.value.startswith("**T-99**") for m in at.markdown), variante
        assert len(at.selectbox) == 0, variante
        assert ROTULO_APLICAR not in [boton.label for boton in at.button], variante
    # sin similares, la falla se declara
    assert "ImportError: falta el extra ml" in [c.value for c in at.caption]

    at = AppTest.from_function(_fragmento, kwargs={"variante": "con_similares"}, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.selectbox) == 1
    assert ROTULO_APLICAR in [boton.label for boton in at.button]


# --- las propuestas se calculan una vez por elaboracion (Q-3 de la revision de A4) -----------


def test_las_propuestas_se_calculan_una_vez_por_elaboracion(monkeypatch, base_sembrada):
    llamadas: list[int] = []

    def _contadas(partidas, pendientes):
        llamadas.append(len(pendientes))
        return _propuestas_fijas(partidas, pendientes)

    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base_sembrada))
    monkeypatch.setattr("ui.elaboracion.propuestas_de_pendientes", _contadas)
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_ITEMS] = _items()
    at.run()
    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()
    assert llamadas == [1]
    at.run()  # otro render sin volver a elaborar
    at.run()
    assert llamadas == [1]


# --- errores tras «Aplicar» (R-2 y Q-2 de la revision de A4) ---------------------------------


def test_si_la_reelaboracion_falla_el_error_queda_visible(monkeypatch, base_sembrada):
    at = _elaborado(monkeypatch, base_sembrada)

    def _falla(*_args):
        raise LookupError("no hay lista de precios vigente a esa fecha")

    monkeypatch.setattr("ui.elaboracion.elaborar_desde_catalogo", _falla)
    at.selectbox(key="elaborar_propuesta_0").set_value("LB-02-TUB")
    at.button(key="elaborar_aplicar_0").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("no hay lista de precios vigente" in e.value for e in at.error), at.error


def test_aplicar_sin_items_no_rompe(monkeypatch, base_sembrada):
    at = _elaborado(monkeypatch, base_sembrada)
    at.session_state[CLAVE_ITEMS] = None  # lo que deja una extraccion fallida (`_extraer`)
    at.button(key="elaborar_aplicar_0").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("vuelva a elaborar" in e.value for e in at.error), at.error


def test_aplicar_con_otros_items_no_rompe(monkeypatch, base_sembrada):
    """O-1 de la revision de A4: la otra mitad de la guarda. Tras extraer otro computo (una lista
    no vacia sin T-99) sigue a la vista el resultado anterior; aceptar su propuesta es un error
    visible, no el `ValueError` de `aceptar_propuesta`."""
    at = _elaborado(monkeypatch, base_sembrada)
    at.session_state[CLAVE_ITEMS] = list(items_auditados())
    at.button(key="elaborar_aplicar_0").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("vuelva a elaborar" in e.value for e in at.error), at.error
    assert at.session_state[CLAVE_ITEMS] == list(items_auditados())  # nada se acepto


# --- una falla real del modelo llega a la pantalla (Q-4 de la revision de A4) ----------------


def test_sin_el_extra_el_pendiente_se_declara_sin_propuestas(monkeypatch, base_sembrada):
    """Sin doble de `propuestas_de_pendientes`: el modelo falla donde falla de verdad
    (`_cargar_modelo`, con `ModuleNotFoundError`), y la pantalla declara la falla del pendiente
    sin selector ni excepcion."""

    def _sin_extra(*_args, **_kwargs):
        raise ModuleNotFoundError("No module named 'sentence_transformers'")

    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base_sembrada))
    monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _sin_extra)
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_ITEMS] = _items()
    at.run()
    _por_rotulo(at.button, ROTULO_ELABORAR).click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert any(m.value.startswith("**T-99**") for m in at.markdown)
    assert "elaborar_propuesta_0" not in [s.key for s in at.selectbox]
    assert ROTULO_APLICAR not in [boton.label for boton in at.button]
    assert any(c.value.startswith("ImportError: No module named") for c in at.caption), [
        c.value for c in at.caption
    ]
