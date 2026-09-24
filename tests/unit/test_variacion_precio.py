"""Una sola fórmula de variación (INV‑004): docs/modelo_datos.md §6,
(nuevo − anterior) / anterior.
"""

from __future__ import annotations

from decimal import Decimal

from core.budget import actualizacion
from core.catalog.precios import CambioDetectado, variacion_relativa
from core.models import Insumo


def test_la_variacion_es_la_de_modelo_datos():
    assert variacion_relativa(Decimal("15"), Decimal("18")) == Decimal("0.2")


def test_con_base_nula_la_variacion_es_cero_por_politica_declarada():
    assert variacion_relativa(Decimal("0"), Decimal("18")) == Decimal("0")


def test_el_cambio_detectado_usa_la_misma_funcion():
    cambio = CambioDetectado(
        insumo=Insumo(), precio_anterior=Decimal("0"), precio_nuevo=Decimal("18")
    )
    assert cambio.variacion == Decimal("0")


def test_actualizacion_no_define_su_propia_formula():
    assert not hasattr(actualizacion, "_variacion")
    assert actualizacion.variacion_relativa is variacion_relativa
