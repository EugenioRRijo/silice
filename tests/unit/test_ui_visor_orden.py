"""El visor valida el IFC con el adaptador antes de teselarlo (O-1 de la revision P de C5).

`ui.visor3d.mallas` abre el modelo con `ifcopenshell.open`, que ante un archivo que no es STEP deja
una excepcion no atrapable al liberarse (ifcopenshell 0.8.5). El adaptador civil IFC es la unica
puerta que rechaza esos archivos con un `ValueError` sin pasar por `ifcopenshell.open` (su
`_abrir_modelo`, pista P). Por eso la pagina extrae el computo **antes** de teselar: si el adaptador
rechaza el archivo, `mallas` nunca lo abre.

Esta prueba fija el orden con dobles (no necesita el extra `civil`): un adaptador que rechaza el
archivo y un `mallas` que cuenta sus llamadas. El recorrido real con un IFC ilegible y
`-W error` necesita el `_abrir_modelo` de la pista P y se comprueba al integrar.
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

SCRIPT = "from ui.paginas.visor import render\nrender()\n"
MOTIVO = "el archivo 'tanquilla.ifc' es ilegible: no es un modelo IFC"


class _IfcopenshellDoble(SimpleNamespace):
    class Error(Exception):
        pass


class _AdaptadorQueRechaza:
    def extraer(self, _ruta):
        raise ValueError(MOTIVO)


def test_si_el_adaptador_rechaza_el_ifc_el_visor_no_lo_abre(monkeypatch):
    llamadas: list[object] = []
    pagina = importlib.import_module("ui.paginas.visor")
    monkeypatch.setattr(
        pagina,
        "_cargar_dependencias_civiles",
        lambda: (_IfcopenshellDoble(), _AdaptadorQueRechaza),
    )
    monkeypatch.setattr(pagina, "mallas", lambda ruta: llamadas.append(ruta) or [])

    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()

    assert not at.exception, [e.value for e in at.exception]
    assert [e.value for e in at.error] == [MOTIVO]
    assert llamadas == []  # `ifcopenshell.open` (dentro de `mallas`) nunca se llamo
