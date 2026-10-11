"""Dependencias de Sílice, una sola vez (maestro §3, RV-2, RV-24; plan 0.6.0, tarea A2).

Tres cosas: `pyproject.toml` declara lo que necesitan la 0.6.0 a la 1.0.0; todo esta instalado
(la CI corre con `--all-extras`: cero omitidas); y cada tercero nuevo solo lo importa su paquete
dueño, con importacion diferida (dentro de una funcion) si viene de un extra, para que importar el
modulo no falle sin el extra (INV-024, como `ml/normalization` con sentence-transformers).
Complementa a `TERCEROS_POR_ADAPTADOR` de `test_arquitectura.py`, que solo mira `adapters/`; las
reglas de cada spec van en su propio archivo (maestro §3.1).
"""

from __future__ import annotations

import ast
import importlib.util
import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

BASE_SILICE = ("alembic>=1.20", "argon2-cffi>=25.1", "cryptography>=44")
EXTRAS_SILICE: dict[str, tuple[str, ...]] = {
    "bcv": ("xlrd>=2.0",),
    "ifc": ("ifctester>=0.8.5,<0.9",),
    "planos": ("ezdxf>=1.3", "shapely>=2.1"),
    "anomalias": ("scikit-learn>=1.4",),
    "similitud": ("sentence-transformers>=3.0",),
    "ia": ("anthropic>=1.0", "ollama>=0.6", "keyring>=25"),
}

#: Tercero (nombre de importacion) -> carpetas que pueden importarlo. Fuera de ellas, ningun modulo.
DUENOS_DE_TERCEROS: dict[str, tuple[str, ...]] = {
    "xlrd": ("adapters/bcv/",),
    "ifctester": ("adapters/espacio/planos/",),
    "shapely": ("adapters/espacio/planos/",),
    "anthropic": ("asistente/",),
    "ollama": ("asistente/",),
    "keyring": ("asistente/",),
    "argon2": ("seguridad/",),
    "cryptography": ("seguridad/",),
    "alembic": ("migraciones/", "operacion/"),
}
#: Terceros de un extra: se importan dentro de una funcion, nunca al cargar el modulo.
DIFERIDOS = frozenset({"xlrd", "ifctester", "anthropic", "ollama", "keyring"})
#: Carpetas que no son codigo del producto (las pruebas pueden importar cualquier tercero).
_EXCLUIDAS = frozenset({"tests", "data", "docs"})


def _proyecto() -> dict:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def importaciones(texto: str) -> list[tuple[str, bool]]:
    """(paquete de primer nivel, diferida) de cada importacion absoluta del modulo."""
    arbol = ast.parse(texto)
    en_funcion: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            en_funcion.update(id(hijo) for hijo in ast.walk(nodo) if hijo is not nodo)
    resultado: list[tuple[str, bool]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            nombres = [nodo.module]
        else:
            continue
        resultado.extend((nombre.split(".")[0], id(nodo) in en_funcion) for nombre in nombres)
    return resultado


def violaciones(ruta_relativa: str, texto: str) -> list[str]:
    """Las importaciones de terceros de Sílice que `ruta_relativa` no puede hacer."""
    encontradas: list[str] = []
    for tercero, diferida in importaciones(texto):
        duenos = DUENOS_DE_TERCEROS.get(tercero)
        if duenos is None:
            continue
        if not ruta_relativa.startswith(duenos):
            encontradas.append(f"{ruta_relativa}: {tercero} fuera de {', '.join(duenos)}")
        elif tercero in DIFERIDOS and not diferida:
            encontradas.append(
                f"{ruta_relativa}: {tercero} se importa al cargar el modulo "
                "(debe ir dentro de una funcion)"
            )
    return encontradas


def _modulos_del_producto() -> list[Path]:
    return sorted(
        archivo
        for carpeta in RAIZ.iterdir()
        if carpeta.is_dir() and not carpeta.name.startswith(".") and carpeta.name not in _EXCLUIDAS
        for archivo in carpeta.rglob("*.py")
    )


def test_el_pyproject_declara_las_dependencias_de_silice() -> None:
    proyecto = _proyecto()
    assert set(BASE_SILICE) <= set(proyecto["dependencies"])
    extras = proyecto["optional-dependencies"]
    for extra, requisitos in EXTRAS_SILICE.items():
        assert set(requisitos) <= set(extras[extra]), extra


def test_ml_reune_anomalias_similitud_y_xgboost() -> None:
    extras = _proyecto()["optional-dependencies"]
    esperado = set(extras["anomalias"]) | set(extras["similitud"]) | {"xgboost>=2.0"}
    assert set(extras["ml"]) == esperado


def test_ifctester_no_entra_en_civil() -> None:
    """`bcf-client` (de ifctester) declara GPLv3: `civil` va al instalador basico, sin ella."""
    assert not any(r.startswith("ifctester") for r in _proyecto()["optional-dependencies"]["civil"])


@pytest.mark.parametrize("modulo", sorted(DUENOS_DE_TERCEROS))
def test_cada_dependencia_nueva_esta_instalada(modulo: str) -> None:
    assert importlib.util.find_spec(modulo) is not None, (
        f"falta {modulo}: unset VIRTUAL_ENV; uv sync --all-extras"
    )


def test_ifctester_es_de_la_misma_serie_que_ifcopenshell() -> None:
    def serie(distribucion: str) -> list[str]:
        return version(distribucion).split(".")[:2]

    assert serie("ifctester") == serie("ifcopenshell")


def test_ningun_modulo_importa_un_tercero_de_silice_fuera_de_su_dueno() -> None:
    encontradas = [
        violacion
        for archivo in _modulos_del_producto()
        for violacion in violaciones(
            archivo.relative_to(RAIZ).as_posix(), archivo.read_text(encoding="utf-8")
        )
    ]
    assert encontradas == []


def test_la_guardia_de_terceros_ve_cada_caso() -> None:
    assert violaciones("ui/x.py", "import xlrd\n") == ["ui/x.py: xlrd fuera de adapters/bcv/"]
    assert violaciones("adapters/bcv/libro.py", "import xlrd\n") == [
        "adapters/bcv/libro.py: xlrd se importa al cargar el modulo (debe ir dentro de una funcion)"
    ]
    assert violaciones("adapters/bcv/libro.py", "def leer():\n    import xlrd\n") == []
    assert (
        violaciones(
            "seguridad/firma.py", "from cryptography.hazmat.primitives.asymmetric import ed25519\n"
        )
        == []
    )
    assert violaciones("api/main.py", "from cryptography.fernet import Fernet\n") == [
        "api/main.py: cryptography fuera de seguridad/"
    ]
    assert violaciones("ui/x.py", "import pandas\n") == []
