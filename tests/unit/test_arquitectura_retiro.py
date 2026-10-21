"""Guardia del retiro de Streamlit (PLAN_RETIRO_STREAMLIT F1).

Nada fuera de `ui/` y `tests/` importa `ui`; la unica excepcion son los archivos de `PENDIENTES`,
que bajan a vacio en F7. La lectura es por `ast` (no por texto): cuenta tambien los imports dentro
de funciones, bajo `if TYPE_CHECKING:` y las llamadas `importlib.import_module("ui...")` con
cadena literal.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

from instalador import manifiesto
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


def _modulos_del_producto() -> list[str]:
    """Las raices que el instalador empaqueta: el cierre del manifiesto, la API y `operacion`."""
    raices = list(manifiesto.cargar().cierre_desde) + ["api.main"]
    raices += [
        ".".join(a.relative_to(RAIZ).with_suffix("").parts)
        for a in (RAIZ / "operacion").rglob("*.py")
    ]
    return raices


def cierre_que_toca_ui(raices: list[str], permitidos: set[str]) -> list[str]:
    """Archivos del cierre transitivo de `raices` que son de `ui/` o que importan `ui`.

    Atrapa lo que la lectura archivo por archivo no ve: un modulo empaquetado que importa un
    `tests/fixtures/*.py` que a su vez importa `ui` (el instalador no lleva `ui/`). Los
    `permitidos` (PENDIENTES de `asistente/`) bajan a vacio en F7."""
    cierre = manifiesto.cierre_de_importaciones(RAIZ, raices)
    return sorted(
        ruta_relativa.as_posix()
        for ruta_relativa in cierre
        if ruta_relativa.as_posix() not in permitidos
        if ruta_relativa.parts[0] == "ui"
        or modulos_ui_importados((RAIZ / ruta_relativa).read_text(encoding="utf-8"))
    )


def test_el_cierre_de_importaciones_del_instalador_no_toca_ui() -> None:
    assert cierre_que_toca_ui(_modulos_del_producto(), PENDIENTES) == []


# --- F4: la capa Streamlit ya no existe ----------------------------------------------------------

#: Paquetes de la interfaz retirada: ningun `.py` del repo (tampoco `tests/`) los importa.
PAQUETES_RETIRADOS = {"streamlit", "altair"}


def _es_retirado(modulo: str) -> bool:
    return modulo.split(".")[0] in PAQUETES_RETIRADOS


def importa_paquetes_retirados(fuente: str) -> list[str]:
    """Los modulos `streamlit*` o `altair*` que importa `fuente` (tambien dentro de funciones y
    con `importlib.import_module("...")` de cadena literal)."""
    encontrados: list[str] = []
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Import):
            encontrados += [a.name for a in nodo.names if _es_retirado(a.name)]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            if _es_retirado(nodo.module):
                encontrados.append(nodo.module)
        elif isinstance(nodo, ast.Call):
            f = nodo.func
            nombre = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nombre == "import_module" and nodo.args:
                a = nodo.args[0]
                if (
                    isinstance(a, ast.Constant)
                    and isinstance(a.value, str)
                    and _es_retirado(a.value)
                ):
                    encontrados.append(a.value)
    return encontrados


def todos_los_py_del_repo() -> list[Path]:
    """Todo `.py` versionable del repo, `tests/` y `ui/` incluidos (sin venv, `.worktrees`,
    `node_modules` ni carpetas ocultas)."""
    salida = []
    for carpeta, subcarpetas, nombres in os.walk(RAIZ):
        subcarpetas[:] = [
            d
            for d in subcarpetas
            if not d.startswith(".") and d not in {"node_modules", "__pycache__"}
        ]
        salida += [Path(carpeta) / n for n in nombres if n.endswith(".py")]
    return sorted(salida)


def test_ui_paginas_no_existe() -> None:
    assert not (RAIZ / "ui" / "paginas").exists()


def test_ningun_py_del_repo_importa_streamlit_ni_altair() -> None:
    infractores_ = sorted(
        f"{ruta(a)}: {', '.join(sorted(set(mods)))}"
        for a in todos_los_py_del_repo()
        if (mods := importa_paquetes_retirados(a.read_text(encoding="utf-8")))
    )
    assert infractores_ == []


def test_la_guardia_de_streamlit_ve_cada_forma_de_importar() -> None:
    assert importa_paquetes_retirados("import streamlit as st\n") == ["streamlit"]
    assert importa_paquetes_retirados(
        "def f():\n    from streamlit.testing.v1 import AppTest\n"
    ) == ["streamlit.testing.v1"]
    assert importa_paquetes_retirados("import altair\n") == ["altair"]
    assert importa_paquetes_retirados("import importlib\nimportlib.import_module('altair')\n") == [
        "altair"
    ]
    assert (
        importa_paquetes_retirados("import streamlit_extras\nfrom aplicacion import altairx\n")
        == []
    )
