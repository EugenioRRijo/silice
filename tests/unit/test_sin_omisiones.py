"""Ninguna prueba se omite por su cuenta (maestro §6.2 y §6.3; plan 0.6.0, tarea A3).

`pytest.skip`, `pytest.mark.skip` y `pytest.mark.skipif` quedan prohibidos en `tests/`: lo que falte
debe fallar con la orden que lo arregla. `pytest.importorskip` de un extra sigue permitido porque la
CI instala todos los extras y `scripts/verificar_omitidas.py` falla ante cualquier omitida.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
_FORMAS = frozenset({"pytest.skip", "pytest.mark.skip", "pytest.mark.skipif"})


def omisiones(archivo: Path) -> list[int]:
    """Lineas de `archivo` con una forma de omitir de `_FORMAS`."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    return sorted(
        {
            nodo.lineno
            for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.Attribute) and ast.unparse(nodo) in _FORMAS
        }
    )


def test_el_detector_ve_cada_forma_de_omitir(tmp_path: Path) -> None:
    archivo = tmp_path / "test_x.py"
    archivo.write_text(
        "import pytest\n"
        "@pytest.mark.skipif(True, reason='x')\n"
        "def test_a():\n"
        "    pytest.skip('y')\n"
        "@pytest.mark.skip\n"
        "def test_b():\n"
        "    pytest.importorskip('z')\n",
        encoding="utf-8",
    )
    assert omisiones(archivo) == [2, 4, 5]


def test_ninguna_prueba_se_omite_por_su_cuenta() -> None:
    encontradas = {
        archivo.relative_to(RAIZ).as_posix(): lineas
        for archivo in sorted((RAIZ / "tests").rglob("*.py"))
        if (lineas := omisiones(archivo))
    }
    assert encontradas == {}
