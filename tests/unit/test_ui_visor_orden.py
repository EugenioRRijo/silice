"""El visor valida el IFC con el adaptador antes de teselarlo (O-1 de la revision P de C5).

`ui.visor3d.mallas` abre el modelo con `ifcopenshell.open`, que ante un archivo que no es STEP deja
una excepcion no atrapable al liberarse (ifcopenshell 0.8.5). El adaptador civil IFC es la unica
puerta que rechaza esos archivos con un `ValueError` sin pasar por `ifcopenshell.open` (su
`_abrir_modelo`, pista P). Por eso la pagina extrae el computo **antes** de teselar: si el adaptador
rechaza el archivo, `mallas` nunca lo abre.

La primera prueba fija el orden con dobles (no necesita el extra `civil`): un adaptador que
rechaza el archivo y un `mallas` que cuenta sus llamadas. La segunda recorre la pagina de punta a
punta, ya integrado el `_abrir_modelo` de la pista P: un IFC ilegible real escrito en `tmp_path`,
el adaptador y `mallas` reales, sin dobles. La pagina debe mostrar el rechazo del adaptador con
`st.error` y no dejar ninguna excepcion no atrapable (el `KeyError` del `__del__` de
`ifcopenshell.file`): se capturan con `sys.unraisablehook` tras un `gc.collect()`, sin depender de
que `-W error` las convierta en falla en esta prueba y no en la siguiente.
"""

from __future__ import annotations

import gc
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
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


#: IFC ilegibles reales: uno que no es STEP y dos STEP con la cabecera danada, que ifcopenshell no
#: abre (los mismos tipos de caso que `tests/unit/test_fuentes_ilegibles.py`).
IFC_ILEGIBLES = {
    "binario": b"\x00\xff\xfe basura binaria que no es STEP \x00",
    "cabecera-danada": b"ISO-10303-21;\nHEADER;\n@@@ basura $$$ \x00\xff\nENDSEC;\n",
    "solo-la-palabra-inicial": b"ISO-10303-21;",
}


@pytest.mark.parametrize("caso", sorted(IFC_ILEGIBLES))
def test_un_ifc_ilegible_real_se_muestra_como_error_sin_excepciones_no_atrapables(
    monkeypatch, tmp_path: Path, caso: str
):
    pytest.importorskip("ifcopenshell")
    ruta = tmp_path / f"{caso}.ifc"
    ruta.write_bytes(IFC_ILEGIBLES[caso])
    pagina = importlib.import_module("ui.paginas.visor")
    monkeypatch.setattr(pagina, "RUTA_POR_DEFECTO", str(ruta))  # sin archivo subido: esta ruta
    no_atrapables: list[str] = []
    monkeypatch.setattr(
        sys, "unraisablehook", lambda info: no_atrapables.append(repr(info.exc_value))
    )

    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.run()
    gc.collect()

    assert not at.exception, [e.value for e in at.exception]
    errores = [e.value for e in at.error]
    assert len(errores) == 1, errores
    assert ruta.name in errores[0] and "ilegible" in errores[0], errores
    assert no_atrapables == []
