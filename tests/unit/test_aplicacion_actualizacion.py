"""Actualizacion de precios (`aplicacion/actualizacion.py`): el detector de atipicos (UC-07).

Movida desde `tests/unit/test_ui_actualizacion_alta.py` (retiro de Streamlit, F3). Alli se probaba
a traves de `ui.paginas.actualizacion._detector_de_atipicos`, que solo delegaba en
`aplicacion.actualizacion.detector_de_atipicos`; aqui se llama al objeto real. La pagina se
importaba "igual" sin el extra: ahora lo comprobado es que `aplicacion.actualizacion` se importa
igual y expone `revalorar`.
"""

from __future__ import annotations

import importlib

from tests.fixtures.sin_extra import SinExtra

_MODULOS_RELACIONADOS_CON_ML = (
    "ml",
    "ml.anomaly",
    "ml.anomaly.detector",
    "aplicacion.actualizacion",
)


def test_el_detector_es_el_de_ml_y_sin_el_extra_no_hay(monkeypatch):
    """El import perezoso: con el extra `ml`, `ml.anomaly.precios_atipicos`; sin el, `None` y el
    modulo se importa igual."""
    import ml.anomaly

    actualizacion = importlib.import_module("aplicacion.actualizacion")
    assert actualizacion.detector_de_atipicos() is ml.anomaly.precios_atipicos

    with SinExtra(monkeypatch, ("ml",), _MODULOS_RELACIONADOS_CON_ML):
        sin_ml = importlib.import_module("aplicacion.actualizacion")
        assert callable(sin_ml.revalorar)
        assert sin_ml.detector_de_atipicos() is None
