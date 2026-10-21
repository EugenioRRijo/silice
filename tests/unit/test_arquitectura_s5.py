"""Reglas de arquitectura de S5 (spec S5 §5.2; maestro §3.1 y §4.3; RV-5, RV-22).

Archivo propio de S5 (RV-2: cada spec escribe sus reglas en su archivo, con los ayudantes
compartidos de `tests/fixtures/arquitectura.py`).
"""

from __future__ import annotations

import ast

import pytest

from tests.fixtures.arquitectura import archivos, importaciones, llamadas, ruta

#: Lo único de `operacion` que `aplicacion` y `api` NO pueden importar: arrancar y la CLI (S5 §5.2).
PRIVADOS_DE_OPERACION = ("operacion.lanzador", "operacion.ordenes_100", "operacion.__main__")


def _raiz(modulo: str) -> str:
    return modulo.split(".")[0]


def _infractores(paquetes: tuple[str, ...], prohibidos: set[str]) -> list[str]:
    return sorted(
        f"{ruta(archivo)}: {modulo}"
        for paquete in paquetes
        for archivo in archivos(paquete)
        for modulo in importaciones(archivo)
        if _raiz(modulo) in prohibidos
    )


@pytest.mark.parametrize("archivo", archivos("core"), ids=ruta)
def test_el_nucleo_no_importa_operacion_ni_migraciones(archivo) -> None:
    prohibidos = sorted(
        m for m in importaciones(archivo) if _raiz(m) in {"operacion", "migraciones"}
    )
    assert prohibidos == []


def test_operacion_no_importa_streamlit_ui_ni_api() -> None:
    assert archivos("operacion"), "la guardia no ve operacion/"
    assert _infractores(("operacion",), {"streamlit", "ui", "api"}) == []


def test_migraciones_no_importa_streamlit_ui_api_ni_operacion() -> None:
    assert archivos("migraciones"), "la guardia no ve migraciones/"
    assert _infractores(("migraciones",), {"streamlit", "ui", "api", "operacion"}) == []


def test_aplicacion_y_api_no_importan_migraciones() -> None:
    assert _infractores(("aplicacion", "api"), {"migraciones"}) == []


def test_aplicacion_y_api_no_importan_el_lanzador_ni_la_cli() -> None:
    infractores = sorted(
        f"{ruta(archivo)}: {modulo}"
        for paquete in ("aplicacion", "api")
        for archivo in archivos(paquete)
        for modulo in importaciones(archivo)
        if any(modulo == p or modulo.startswith(p + ".") for p in PRIVADOS_DE_OPERACION)
    )
    assert infractores == []


def test_ni_la_aplicacion_ni_la_api_crean_el_esquema() -> None:
    """RV-5: `crear_esquema` queda para las pruebas en memoria y los scripts de siembra."""
    infractores = sorted(
        f"{ruta(archivo)}:{linea}"
        for paquete in ("aplicacion", "api")
        for archivo in archivos(paquete)
        for linea in llamadas(archivo, "crear_esquema")
    )
    assert infractores == []


# --- Tarea 11 (RV-25): `scripts/` y `tests/fixtures` viajan solo por el manifiesto ------------


def _importaciones_al_cargar(archivo, raices: set[str]) -> list[str]:
    """Importaciones del nivel superior del módulo (también dentro de `try`, `if` que no es de
    tipado y `with`), no las de `if TYPE_CHECKING` ni las de dentro de una función o clase."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    pendientes = list(arbol.body)
    halladas = []
    while pendientes:
        nodo = pendientes.pop()
        if isinstance(nodo, ast.Try):
            pendientes.extend(nodo.body + nodo.orelse + nodo.finalbody)
            for manejador in nodo.handlers:
                pendientes.extend(manejador.body)
        elif isinstance(nodo, ast.If) and ast.unparse(nodo.test) not in {
            "TYPE_CHECKING",
            "typing.TYPE_CHECKING",
        }:
            pendientes.extend(nodo.body + nodo.orelse)
        elif isinstance(nodo, ast.With):
            pendientes.extend(nodo.body)
        elif isinstance(nodo, ast.Import):
            halladas += [a.name for a in nodo.names if a.name.split(".")[0] in raices]
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            if nodo.level == 0 and nodo.module.split(".")[0] in raices:
                halladas.append(nodo.module)
    return sorted(halladas)


@pytest.mark.parametrize("archivo", archivos("aplicacion"), ids=ruta)
def test_ningun_modulo_de_aplicacion_importa_scripts_ni_fixtures_al_cargar(archivo) -> None:
    assert _importaciones_al_cargar(archivo, {"scripts", "tests"}) == []


def test_el_detector_de_importaciones_al_cargar_ve_lo_que_debe(tmp_path) -> None:
    """Guardia del propio detector: ve el nivel superior, `try` e `if`; ignora `TYPE_CHECKING` y
    las funciones (las importaciones diferidas de RV-25)."""
    modulo = tmp_path / "m.py"
    modulo.write_text(
        "from typing import TYPE_CHECKING\n"
        "import scripts.seed\n"
        "try:\n    from tests.fixtures import x\nexcept ImportError:\n    import scripts.otro\n"
        "if True:\n    from scripts.simular_lista import simular\n"
        "if TYPE_CHECKING:\n    from scripts.tipos import T\n"
        "def f():\n    from scripts.seed_demo import main\n",
        encoding="utf-8",
    )
    assert _importaciones_al_cargar(modulo, {"scripts", "tests"}) == [
        "scripts.otro",
        "scripts.seed",
        "scripts.simular_lista",
        "tests.fixtures",
    ]
