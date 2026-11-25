"""Guardia contra `monkeypatch.undo()` en la suite de pruebas.

`tests/conftest.py` aísla cada prueba con la fixture `monkeypatch` (`SILICE_DATOS`,
`SILICE_USUARIO` y `SILICE_ACCESO=0`). Llamar a `monkeypatch.undo()` deshace también esos
parches de la sesión y deja el resto de la prueba corriendo contra el entorno real. Para
revertir un parche temporal dentro de una prueba debe usarse `with monkeypatch.context() as
parche:`.
"""

from __future__ import annotations

import ast
from pathlib import Path

ESTE_ARCHIVO = Path(__file__).resolve()
CARPETA_PRUEBAS = ESTE_ARCHIVO.parents[1]
RAIZ = ESTE_ARCHIVO.parents[2]


def _es_monkeypatch(nodo: ast.expr) -> bool:
    if isinstance(nodo, ast.Name):
        return nodo.id == "monkeypatch"
    if isinstance(nodo, ast.Attribute):
        return nodo.attr == "monkeypatch"
    return False


def _lineas_monkeypatch_undo(ruta: Path) -> list[int]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    lineas = [
        nodo.lineno
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and nodo.func.attr == "undo"
        and _es_monkeypatch(nodo.func.value)
    ]
    return sorted(lineas)


def test_ninguna_prueba_llama_monkeypatch_undo() -> None:
    hallazgos = [
        f"{ruta.relative_to(RAIZ).as_posix()}:{linea}"
        for ruta in sorted(CARPETA_PRUEBAS.rglob("*.py"))
        if ruta.resolve() != ESTE_ARCHIVO
        for linea in _lineas_monkeypatch_undo(ruta)
    ]
    assert not hallazgos, (
        "No uses `monkeypatch.undo()` (deshace las fixtures de `tests/conftest.py`); "
        "usa `with monkeypatch.context() as parche:`: " + ", ".join(hallazgos)
    )
