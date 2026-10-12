"""Ayudantes compartidos de las reglas de arquitectura de cada spec de Sílice (maestro §3.1, RV-2).

Cada spec escribe sus reglas en su propio archivo (`tests/unit/test_arquitectura_s5.py`, …) y lee
las importaciones con estas funciones. `tests/unit/test_arquitectura.py` conserva las suyas (archivo
caliente: no se reescribe).
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
_TIPADO = {"TYPE_CHECKING", "typing.TYPE_CHECKING"}


def archivos(paquete: str) -> list[Path]:
    carpeta = RAIZ / paquete
    return sorted(carpeta.rglob("*.py")) if carpeta.is_dir() else []


def ruta(archivo: Path) -> str:
    return archivo.relative_to(RAIZ).as_posix()


def importaciones(archivo: Path) -> set[str]:
    """Módulos que `archivo` importa en tiempo de ejecución (fuera de `if TYPE_CHECKING:`), también
    los perezosos; `from a import b` cuenta `a` y `a.b` (b puede ser un submódulo)."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    solo_tipado = {
        id(nodo)
        for bloque in ast.walk(arbol)
        if isinstance(bloque, ast.If) and ast.unparse(bloque.test) in _TIPADO
        for sentencia in bloque.body
        for nodo in ast.walk(sentencia)
    }
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if id(nodo) in solo_tipado:
            continue
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
            nombres.update(f"{nodo.module}.{alias.name}" for alias in nodo.names)
    return nombres


def llamadas(archivo: Path, nombre: str) -> list[int]:
    """Líneas donde `archivo` llama a `nombre(...)` o a `<algo>.nombre(...)`."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    lineas = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            funcion = nodo.func
            if (isinstance(funcion, ast.Name) and funcion.id == nombre) or (
                isinstance(funcion, ast.Attribute) and funcion.attr == nombre
            ):
                lineas.append(nodo.lineno)
    return sorted(lineas)
