"""Los mensajes del servidor no dicen «este caso» (F8, C5; resto del árbitro de la tanda).

«Caso» es la palabra interna del archivo de una carpeta (`casos/*.db`); la persona ve «carpeta».
Los textos que devuelven la capa de aplicación y la API (detalles de un 404, errores de
validación) dicen «en esta carpeta». Se leen las cadenas del código con `ast` (no los
comentarios): un texto nuevo con «este caso» hace fallar la prueba.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
CARPETAS = ("aplicacion", "api")


def _cadenas(ruta: Path) -> list[tuple[int, str]]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    return [
        (nodo.lineno, nodo.value)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)
    ]


def test_ninguna_cadena_del_servidor_dice_este_caso() -> None:
    encontradas = [
        f"{ruta.relative_to(RAIZ).as_posix()}:{linea}: {texto.strip()[:80]}"
        for carpeta in CARPETAS
        for ruta in sorted((RAIZ / carpeta).rglob("*.py"))
        for linea, texto in _cadenas(ruta)
        if "este caso" in texto.lower()
    ]
    assert encontradas == []


@pytest.mark.parametrize(
    ("archivo", "esperado"),
    [
        ("aplicacion/hoja_versiones.py", "no existe en esta carpeta."),
        ("aplicacion/vial.py", "no existe en esta carpeta."),
        ("aplicacion/precios_empresa.py", "no existe en esta carpeta"),
        ("api/rutas/control.py", "La obra no existe en esta carpeta."),
        ("api/rutas/entregas.py", "no existe en esta carpeta."),
        ("api/rutas/hoja.py", "no existe en esta carpeta."),
        ("api/rutas/reajuste.py", "La obra no existe en esta carpeta."),
        ("api/rutas/revision.py", "La lista {id} no existe en esta carpeta."),
        ("api/rutas/tablero.py", "no existe en esta carpeta."),
        ("api/rutas/precios_empresa.py", "no es una lista de empresa de esta carpeta"),
    ],
)
def test_cada_archivo_dice_carpeta(archivo: str, esperado: str) -> None:
    textos = [t for _, t in _cadenas(RAIZ / archivo)]
    assert any(esperado in t for t in textos), archivo


def _docstrings(ruta: Path) -> set[int]:
    """Líneas donde empieza un docstring (de módulo, clase o función): no son mensajes."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    lineas = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            cuerpo = nodo.body
            if cuerpo and isinstance(cuerpo[0], ast.Expr) and isinstance(cuerpo[0].value, ast.Constant):
                lineas.add(cuerpo[0].value.lineno)
    return lineas


def test_ninguna_cadena_del_servidor_dice_caso_abierto() -> None:
    """Revisión final del árbitro (MENOR 3): «el caso abierto» es la carpeta abierta."""
    encontradas = [
        f"{ruta.relative_to(RAIZ).as_posix()}:{linea}: {texto.strip()[:80]}"
        for carpeta in CARPETAS
        for ruta in sorted((RAIZ / carpeta).rglob("*.py"))
        for linea, texto in _cadenas(ruta)
        if "caso abierto" in texto.lower() and linea not in _docstrings(ruta)
    ]
    assert encontradas == []
