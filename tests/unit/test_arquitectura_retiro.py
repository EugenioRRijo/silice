"""Guardia del retiro de Streamlit (PLAN_RETIRO_STREAMLIT F1).

Nada fuera de `ui/` y `tests/` importa `ui`; la unica excepcion son los archivos de `PENDIENTES`,
que bajan a vacio en F7. La lectura es por `ast` (no por texto): cuenta tambien los imports dentro
de funciones, bajo `if TYPE_CHECKING:` y las llamadas `importlib.import_module("ui...")` con
cadena literal.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.fixtures.arquitectura import RAIZ, ruta

#: Carpetas que no se vigilan: `ui/` y `tests/` pueden importar `ui`; las otras no son codigo.
EXCLUIDAS = {"ui", "tests", "frontend-desktop", "data", "node_modules", "__pycache__"}

#: Archivos que todavia importan `ui` (F7 los pasa a `aplicacion` y vacia esta lista).
#: `asistente/` recibe y devuelve el `Borrador` de `ui.hoja` (otra clase que
#: `aplicacion.hoja.Borrador`): moverlos de a uno rompe el contrato entre ellos.
#: `scripts/prueba_real_asistente.py` pasa a `hoja.elaborar_borrador` el `Borrador` de `ui.hoja` que
#: le entrega `asistente.experimento.banco.borrador_de_partida`: se mueve con `asistente/` (F7).
PENDIENTES = {
    "asistente/experimento/banco.py",
    "asistente/experimento/ejecucion.py",
    "asistente/orquestador.py",
    "asistente/privacidad.py",
    "asistente/propuestas.py",
    "asistente/servicio.py",
    "asistente/validacion.py",
    "scripts/prueba_real_asistente.py",
}


def _es_ui(modulo: str) -> bool:
    return modulo == "ui" or modulo.startswith("ui.")


def modulos_ui_importados(fuente: str) -> list[str]:
    """Los modulos `ui*` que importa `fuente`, en cualquier parte (tambien dentro de funciones)."""
    encontrados: list[str] = []
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Import):
            encontrados += [a.name for a in nodo.names if _es_ui(a.name)]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            if _es_ui(nodo.module):
                encontrados.append(nodo.module)
        elif isinstance(nodo, ast.Call):
            f = nodo.func
            nombre = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nombre == "import_module" and nodo.args:
                a = nodo.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and _es_ui(a.value):
                    encontrados.append(a.value)
    return encontrados


def archivos_del_producto() -> list[Path]:
    salida = []
    for archivo in RAIZ.rglob("*.py"):
        partes = archivo.relative_to(RAIZ).parts
        if partes[0] in EXCLUIDAS or any(p.startswith(".") or p == "node_modules" for p in partes):
            continue
        salida.append(archivo)
    return sorted(salida)


def infractores(archivos: list[Path], permitidos: set[str]) -> list[str]:
    return sorted(
        f"{ruta(a)}: {', '.join(sorted(set(mods)))}"
        for a in archivos
        if ruta(a) not in permitidos
        if (mods := modulos_ui_importados(a.read_text(encoding="utf-8")))
    )


def test_nada_fuera_de_ui_y_tests_importa_ui_salvo_los_pendientes() -> None:
    assert infractores(archivos_del_producto(), PENDIENTES) == []


def test_los_pendientes_existen_y_siguen_importando_ui() -> None:
    """Un pendiente que ya no importa `ui` debe salir de la lista (la lista solo baja)."""
    for relativa in sorted(PENDIENTES):
        archivo = RAIZ / relativa
        assert archivo.is_file(), relativa
        assert modulos_ui_importados(archivo.read_text(encoding="utf-8")), relativa


def test_la_guardia_ve_los_imports_dentro_de_funciones_y_los_dinamicos() -> None:
    assert modulos_ui_importados("def f():\n    from ui import hoja\n") == ["ui"]
    assert modulos_ui_importados("def f():\n    import ui.hoja\n") == ["ui.hoja"]
    assert modulos_ui_importados("import importlib\nimportlib.import_module('ui.hoja')\n") == [
        "ui.hoja"
    ]
    assert modulos_ui_importados("from interfaz import ui\nimport uix\n") == []
