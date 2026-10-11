"""Variables de entorno de Sílice con sus alias anteriores (plan 0.6.0, tarea A1).

Cuatro casos por variable: solo la nueva, solo la vieja, las dos (gana la nueva) y ninguna; más la nueva
en blanco, que cede al alias. El alias vive hasta la 0.6.0 inclusive: una prueba falla cuando
`pyproject.toml` pase de esa versión con el alias todavía declarado.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.version import Version

from ui.app import modo_entrega_activo
from ui.caso import resolver_ruta
from ui.entorno import (
    ALIAS_ANTERIORES,
    ULTIMA_VERSION_CON_ALIAS,
    VARIABLE_CASO,
    VARIABLE_MODO_ENTREGA,
    leer_variable,
)

RAIZ = Path(__file__).resolve().parents[2]
PARES = [(VARIABLE_CASO, "ARENIA_CASO"), (VARIABLE_MODO_ENTREGA, "ARENIA_MODO_ENTREGA")]


def test_los_alias_son_exactamente_los_de_arenia() -> None:
    assert VARIABLE_CASO == "SILICE_CASO"
    assert VARIABLE_MODO_ENTREGA == "SILICE_MODO_ENTREGA"
    assert ALIAS_ANTERIORES == dict(PARES)


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_solo_la_nueva(nueva: str, vieja: str) -> None:
    assert leer_variable({nueva: "a"}, nueva) == "a"


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_solo_la_vieja(nueva: str, vieja: str) -> None:
    assert leer_variable({vieja: "b"}, nueva) == "b"


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_las_dos_distintas_gana_la_nueva(nueva: str, vieja: str) -> None:
    assert leer_variable({nueva: "a", vieja: "b"}, nueva) == "a"


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_ninguna(nueva: str, vieja: str) -> None:
    assert leer_variable({}, nueva) is None


@pytest.mark.parametrize(("nueva", "vieja"), PARES)
def test_la_variable_nueva_en_blanco_cede_al_alias(nueva: str, vieja: str) -> None:
    assert leer_variable({nueva: "  ", vieja: "b"}, nueva) == "b"
    assert leer_variable({nueva: "  "}, nueva) is None


def test_el_caso_y_el_modo_entrega_leen_con_el_ayudante() -> None:
    assert resolver_ruta(None, {"ARENIA_CASO": "viejo.db"}, "d.db") == Path("viejo.db")
    entorno = {"SILICE_CASO": "nuevo.db", "ARENIA_CASO": "viejo.db"}
    assert resolver_ruta(None, entorno, "d.db") == Path("nuevo.db")
    assert modo_entrega_activo({"ARENIA_MODO_ENTREGA": "1"}) is True
    assert modo_entrega_activo({"SILICE_MODO_ENTREGA": "0", "ARENIA_MODO_ENTREGA": "1"}) is False
    assert modo_entrega_activo({"SILICE_MODO_ENTREGA": "1"}) is True


def _alias_permitidos(version: str) -> bool:
    return Version(version) <= Version(ULTIMA_VERSION_CON_ALIAS)


def test_el_alias_se_retira_despues_de_la_0_6_0() -> None:
    assert _alias_permitidos("0.6.0") and not _alias_permitidos("0.7.0")
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    version = tomllib.loads(texto)["project"]["version"]
    assert _alias_permitidos(version) or ALIAS_ANTERIORES == {}, (
        f"pyproject dice {version}: la 0.7.0 ya no acepta ARENIA_*; vacie ALIAS_ANTERIORES y "
        "retire la nota de alias de los dos manuales"
    )


def test_el_ayudante_solo_usa_la_biblioteca_estandar() -> None:
    arbol = ast.parse((RAIZ / "ui" / "entorno.py").read_text(encoding="utf-8"))
    importados = {
        alias.name.split(".")[0]
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Import)
        for alias in nodo.names
    } | {
        nodo.module.split(".")[0]
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) and nodo.module
    }
    assert importados <= set(sys.stdlib_module_names) | {"__future__"}
