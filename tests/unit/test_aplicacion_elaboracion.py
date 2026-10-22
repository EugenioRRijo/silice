"""Elaboracion (`aplicacion/elaboracion.py`): propuestas por pendiente y plan por periodos.

Movidas sin cambio de logica desde `tests/unit/test_ui_elaborar.py` y
`tests/unit/test_ui_elaborar_plan_y_rendimiento.py` (retiro de Streamlit, F3); solo cambia el
import (`ui.elaboracion` y `ui.composicion` eran puentes de `aplicacion`). Datos ficticios
(NORMAS.md §1).
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from aplicacion.elaboracion import aceptar_propuesta, propuestas_de_pendientes
from core.contracts import Dominio, ItemComputo, OrigenTipo
from tests.fixtures.computo_auditado import items_auditados

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


def test_aceptar_cambia_solo_el_item_pendiente() -> None:
    items = _items()
    aceptados = aceptar_propuesta(items, PENDIENTE_T99, "LB-02-TUB")
    assert aceptados[:-1] == items[:-1]  # los demas, identicos
    assert aceptados[-1] == dataclasses.replace(PENDIENTE_T99, codigo_partida="LB-02-TUB")


def test_aceptar_un_item_que_no_esta_es_un_error() -> None:
    with pytest.raises(ValueError, match="T-99"):
        aceptar_propuesta(list(items_auditados()), PENDIENTE_T99, "LB-02-TUB")


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


PLAN_DOS_SEMANAS = [
    {"periodo": "Semana 1", "codigo_partida": "LB-01-EXC", "fraccion": "1"},
    {"periodo": "Semana 1", "codigo_partida": "LB-02-TUB", "fraccion": "0.5"},
    {"periodo": "Semana 2", "codigo_partida": "LB-02-TUB", "fraccion": "0.5"},
    {"periodo": "Semana 2", "codigo_partida": "LB-03-ENC", "fraccion": "1"},
    {"periodo": "Semana 2", "codigo_partida": "LB-04-CON", "fraccion": "1"},
    {"periodo": "Semana 2", "codigo_partida": "LB-05-REL", "fraccion": "1"},
]


def test_las_filas_del_plan_se_agrupan_por_periodo_y_una_a_medias_se_rechaza() -> None:
    from aplicacion.composicion import ComposicionInvalida
    from aplicacion.elaboracion import plan_desde_filas

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
