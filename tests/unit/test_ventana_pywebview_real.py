"""Las pruebas con el `webview.util` real de pywebview 6.2.1 (RF-184, MENOR del árbitro).

pywebview solo se instala en Windows (`pywebview==6.2.1; sys_platform == 'win32'`): la importación
es dura y este archivo no se recolecta en otras plataformas (`tests/unit/conftest.py`), de modo que
la CI de Linux no tiene pruebas omitidas ni lista blanca.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest
from webview import util

from operacion import ventana


class _VentanaDePywebview(SimpleNamespace):
    """Lo que `webview.util` lee de una ventana de pywebview 6.2.1 (leído en su código)."""

    def __init__(self, js_api: object) -> None:
        super().__init__(
            _functions={},
            _js_api=js_api,
            _expose_lock=threading.Lock(),
            uid="master",
            js_api_endpoint=None,
            text_select=True,
            zoomable=True,
            draggable=False,
            easy_drag=False,
            frameless=False,
            state={},
            events=SimpleNamespace(
                before_load=threading.Event(),
                _pywebviewready=threading.Event(),
                loaded=threading.Event(),
            ),
            evaluadas=[],
            corridas=[],
        )
        self.evaluate_js = self.evaluadas.append
        self.run_js = self.corridas.append


@pytest.mark.parametrize("nombre", ["__class__", "__class__.__base__.__subclasses__", "abrir"])
def test_pywebview_no_llama_nada_que_la_pagina_pida_por_el_puente(nombre: str) -> None:
    """Con el `js_bridge_call` real de pywebview: el nombre no resuelve, no se lanza ningún hilo y
    no vuelve ninguna respuesta a la página (con `None`, «__class__» sí respondía)."""
    falsa = _VentanaDePywebview(ventana.PuenteCerrado())
    util.js_bridge_call(falsa, nombre, [], "1")
    assert falsa.evaluadas == []


def test_pywebview_inyecta_su_objeto_sin_ninguna_funcion_de_silice() -> None:
    """Con el `inject_pywebview` real: el puente cerrado no rompe la carga (`loaded` llega) y la
    lista de funciones expuestas a la página queda vacía."""
    falsa = _VentanaDePywebview(ventana.PuenteCerrado())
    util.inject_pywebview("edgechromium", falsa)
    assert falsa.events.loaded.wait(10)
    assert falsa.events._pywebviewready.is_set()
    (final,) = falsa.corridas[1:]
    assert "_createApi(JSON.parse('[]'))" in final  # `webview/js/finish.js` con la lista vacía
