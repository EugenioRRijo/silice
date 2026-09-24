"""Hace ejecutable la hipótesis central (CLAUDE.md §1 y §2).

- adapters/ y ml/ importan de `core` únicamente `core.contracts`;
- core/ no importa adapters, ml, ui, api, scripts ni tests (ningún paquete de primer nivel);
- core/contracts solo depende de la biblioteca estándar.

Complementa a `git diff --stat core/` (Sesión I5): vigila la dependencia, no solo el cambio.
"""

import ast
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PAQUETES_FUERA_DEL_NUCLEO = ("adapters", "ml", "ui", "api", "scripts", "tests")


def _archivos(paquete: str) -> list[Path]:
    return sorted((RAIZ / paquete).rglob("*.py"))


def _ruta(archivo: Path) -> str:
    return archivo.relative_to(RAIZ).as_posix()


def _imports(archivo: Path):
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield alias.name
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            yield nodo.module


def _es_core_fuera_de_contracts(modulo: str) -> bool:
    es_core = modulo == "core" or modulo.startswith("core.")
    return es_core and not modulo.startswith("core.contracts")


@pytest.mark.parametrize(
    "archivo", [a for p in ("adapters", "ml") for a in _archivos(p)], ids=_ruta
)
def test_fuera_del_nucleo_solo_se_importa_core_contracts(archivo):
    prohibidos = [m for m in _imports(archivo) if _es_core_fuera_de_contracts(m)]
    assert not prohibidos, (
        f"{_ruta(archivo)} importa {prohibidos}; solo se permite core.contracts "
        "(CLAUDE.md §2). Si parece imprescindible, es un hallazgo de la investigación: "
        "documentarlo en docs/bitacora/."
    )


@pytest.mark.parametrize("archivo", _archivos("core"), ids=_ruta)
def test_el_nucleo_no_conoce_a_los_demas_paquetes(archivo):
    prohibidos = [m for m in _imports(archivo) if m.split(".")[0] in PAQUETES_FUERA_DEL_NUCLEO]
    assert not prohibidos, f"{_ruta(archivo)} importa {prohibidos}; core/ es un núcleo cerrado."


@pytest.mark.parametrize("archivo", _archivos("core/contracts"), ids=_ruta)
def test_los_contratos_solo_usan_la_biblioteca_estandar(archivo):
    permitidos = set(sys.stdlib_module_names) | {"__future__"}
    externos = [
        m
        for m in _imports(archivo)
        if m.split(".")[0] not in permitidos and not m.startswith("core.contracts")
    ]
    assert not externos, (
        f"{_ruta(archivo)} depende de {externos}; los contratos no llevan terceros."
    )


def test_la_guardia_cubre_todo_paquete_de_primer_nivel_fuera_del_nucleo():
    """INV-010: la tupla vigilada no puede olvidar un paquete del repositorio.

    Todo directorio de primer nivel con `__init__.py`, salvo `core`, es un paquete que el nucleo no
    puede importar (CLAUDE.md §2; spec de cierre §4, criterio D: `core/` no importa de `adapters/`,
    `ml/`, `ui/`, `api/` ni `scripts/`). `tests` entra porque tambien es importable
    (`tests/__init__.py`). Un paquete nuevo (p. ej. `asistente`) hace fallar esta prueba hasta
    que se agrega a la tupla.
    """
    paquetes = {inicio.parent.name for inicio in RAIZ.glob("*/__init__.py")} - {"core"}
    assert paquetes == set(PAQUETES_FUERA_DEL_NUCLEO)
