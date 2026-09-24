"""Hace ejecutable la hipótesis central (CLAUDE.md §1 y §2).

- adapters/ importa solo la biblioteca estándar, core.contracts, su propio paquete y los terceros
  declarados, con importación absoluta; ml/ importa de core solo core.contracts;
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

#: Terceros que cada adaptador puede importar, ademas de la biblioteca estandar, `core.contracts` y
#: su propio paquete (INV-018: una sola guardia con la regla que antes solo regia para telecom).
#: Un adaptador nuevo necesita su fila: lo exige `test_toda_carpeta_de_adapters_tiene_su_regla`.
TERCEROS_POR_ADAPTADOR: dict[str, frozenset[str]] = {
    "civil": frozenset({"ifcopenshell"}),
    "industrial": frozenset(),
    "sistemas": frozenset(),
    "telecom": frozenset(),
}
_BIBLIOTECA_ESTANDAR = frozenset(sys.stdlib_module_names) | {"__future__"}


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


@pytest.mark.parametrize("archivo", _archivos("ml"), ids=_ruta)
def test_ml_solo_importa_core_contracts_del_nucleo(archivo):
    """ml/ importa de core solo core.contracts; adapters/ lo vigila su propia guardia (INV-018)."""
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


def _imports_relativos(archivo: Path) -> list[str]:
    """Las importaciones relativas (`from . import x`, `from ..core import y`), que `_imports` no
    devuelve (`level > 0`). Sin resolverlas no se sabe que paquete importan: en `adapters/` se
    prohiben, y cada adaptador importa con la ruta absoluta que la regla si puede juzgar."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    return [
        "." * nodo.level + (nodo.module or "")
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) and nodo.level > 0
    ]


def _import_permitido(adaptador: str, modulo: str) -> bool:
    """True si un archivo de `adapters/<adaptador>/` puede importar `modulo`.

    Compara el paquete completo y no solo la raiz: `adapters.civil.evaluador` tiene la misma raiz
    `adapters` que el propio paquete de telecom y no por eso le esta permitido (hallazgo Important 1
    de la ronda 1 de revision de I5, que antes solo vigilaba la copia de telecom).
    """
    raiz = modulo.split(".")[0]
    if raiz == "core":
        return modulo == "core.contracts" or modulo.startswith("core.contracts.")
    if raiz == "adapters":
        propio = f"adapters.{adaptador}"
        return modulo == propio or modulo.startswith(propio + ".")
    return raiz in _BIBLIOTECA_ESTANDAR or raiz in TERCEROS_POR_ADAPTADOR[adaptador]


@pytest.mark.parametrize("adaptador", sorted(TERCEROS_POR_ADAPTADOR))
def test_un_adaptador_solo_importa_contratos_su_paquete_y_sus_terceros(adaptador):
    """INV-018: CLAUDE.md §2 y §5 para cada adaptador, con importaciones anidadas incluidas.

    Las relativas se rechazan todas: `from ..core import costing` escaparia a `_imports`."""
    archivos = _archivos(f"adapters/{adaptador}")
    prohibidos = [
        f"{_ruta(archivo)}: {modulo}"
        for archivo in archivos
        for modulo in _imports(archivo)
        if not _import_permitido(adaptador, modulo)
    ] + [
        f"{_ruta(archivo)}: {relativo} (relativa)"
        for archivo in archivos
        for relativo in _imports_relativos(archivo)
    ]
    assert not prohibidos, (
        f"adapters/{adaptador} importa {prohibidos}; solo se permite la biblioteca estandar, "
        "core.contracts, su propio paquete y los terceros de TERCEROS_POR_ADAPTADOR, siempre con "
        "importacion absoluta"
    )


def test_la_regla_de_un_adaptador_rechaza_otro_adaptador_y_el_resto_del_nucleo():
    assert not _import_permitido("telecom", "adapters.civil.evaluador")
    assert not _import_permitido("telecom", "adapters.civil")
    assert not _import_permitido("telecom", "adapters.telecomunicaciones")  # prefijo, no paquete
    assert not _import_permitido("telecom", "core.costing")
    assert not _import_permitido("telecom", "core")
    assert not _import_permitido("telecom", "ifcopenshell")  # el tercero de civil no es de telecom
    assert _import_permitido("telecom", "core.contracts.item_computo")
    assert _import_permitido("telecom", "adapters.telecom.adaptador")
    assert _import_permitido("telecom", "decimal")
    assert _import_permitido("telecom", "__future__")


def test_la_guardia_ve_las_importaciones_relativas(tmp_path):
    """`_imports` descarta las relativas (`level > 0`); `_imports_relativos` las devuelve todas,
    con sus puntos, para que la regla por adaptador las rechace."""
    archivo = tmp_path / "modulo.py"
    archivo.write_text(
        "from . import hermano\nfrom ..core.costing import calcular_apu\nimport decimal\n",
        encoding="utf-8",
    )
    assert list(_imports(archivo)) == ["decimal"]
    assert _imports_relativos(archivo) == [".", "..core.costing"]


def test_toda_carpeta_de_adapters_tiene_su_regla():
    """Un adaptador nuevo no puede quedar fuera de la guardia; el `__init__` raiz no importa nada.

    Ademas, todo `.py` de `adapters/` es el `__init__` raiz o vive bajo un paquete con regla: un
    modulo suelto (`adapters/utilidades.py`) o una carpeta sin `__init__.py` escaparian a la regla
    por adaptador, y la generica ya solo recorre `ml/`.
    """
    paquetes = {inicio.parent.name for inicio in (RAIZ / "adapters").glob("*/__init__.py")}
    assert paquetes == set(TERCEROS_POR_ADAPTADOR)
    raiz = RAIZ / "adapters" / "__init__.py"
    assert not list(_imports(raiz)) and not _imports_relativos(raiz)
    sueltos = [
        _ruta(archivo)
        for archivo in _archivos("adapters")
        if archivo != raiz
        and archivo.relative_to(RAIZ / "adapters").parts[0] not in TERCEROS_POR_ADAPTADOR
    ]
    assert not sueltos, f"{sueltos} no estan bajo ningun paquete de TERCEROS_POR_ADAPTADOR"


#: Lo que cada modulo de ui/ no importa en tiempo de ejecucion (fuera de `if TYPE_CHECKING:`).
#: Reglas de interfaz del plan de C3 (Global Constraints) e INV-043 para la pagina de componer.
PROHIBIDOS_EN_UI: dict[str, tuple[str, ...]] = {
    "ui/paginas/componer.py": ("core.budget", "core.costing", "sqlalchemy.orm", "tempfile"),
    # RA-2: "no escribe en la base" vigilado tambien por core.catalog, core.budget y sqlalchemy.
    "ui/composicion.py": (
        "streamlit", "pandas", "ui.caso", "sqlalchemy", "core.catalog", "core.budget",
    ),
    "ui/elaboracion.py": ("streamlit", "pandas", "ui.caso"),
    # ARQ-A2: el fragmento pinta; no abre la base ni lee el catalogo.
    "ui/resultado.py": ("sqlalchemy.orm", "core.costing", "core.catalog"),
}


def _imports_de_ejecucion(ruta: Path) -> set[str]:
    """Modulos importados fuera de `if TYPE_CHECKING:` (AST), tambien los perezosos."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    solo_tipado = {
        id(nodo)
        for bloque in ast.walk(arbol)
        if isinstance(bloque, ast.If)
        and ast.unparse(bloque.test) in {"TYPE_CHECKING", "typing.TYPE_CHECKING"}
        for sentencia in bloque.body
        for nodo in ast.walk(sentencia)
    }
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if id(nodo) in solo_tipado:
            continue
        if isinstance(nodo, ast.Import):
            importados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            importados.add(nodo.module)
            # `from core import costing` importa el submodulo `core.costing` (QA-A2).
            importados.update(f"{nodo.module}.{alias.name}" for alias in nodo.names)
    return importados


@pytest.mark.parametrize("modulo", sorted(PROHIBIDOS_EN_UI))
def test_ui_respeta_sus_importaciones_prohibidas(modulo):
    """INV-043 (criterio S, spec de cierre §4) y reglas de interfaz de C3: cada modulo de ui/
    importa solo lo que su responsabilidad pide."""
    importados = _imports_de_ejecucion(RAIZ / modulo)
    prohibidos = {
        nombre
        for nombre in importados
        for prefijo in PROHIBIDOS_EN_UI[modulo]
        if nombre == prefijo or nombre.startswith(prefijo + ".")
    }
    assert not prohibidos, f"{modulo} importa {sorted(prohibidos)}"


def test_una_sola_lectura_de_celdas_de_tabla_en_ui():
    """INV-046: las celdas de las tablas de `st.data_editor` se leen solo con
    `ui.composicion.texto_de_celda`; ningun modulo de ui/ define su propia copia."""
    copias = sorted(
        archivo.relative_to(RAIZ).as_posix()
        for archivo in (RAIZ / "ui").rglob("*.py")
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8")))
        if isinstance(nodo, ast.FunctionDef) and nodo.name in {"_celda_de_cantidad", "_texto"}
    )
    assert copias == []


def test_ningun_modulo_de_prueba_importa_de_otro_modulo_de_prueba():
    """INV-052 (A-6): lo compartido entre pruebas vive en `tests/fixtures/`. Un modulo `test_*.py`
    solo importa de `tests.fixtures` o de `tests.conftest`, nunca de otro modulo de prueba."""
    permitidos = ("tests.fixtures", "tests.conftest")
    infractores = sorted(
        f"{archivo.relative_to(RAIZ).as_posix()}:{nodo.lineno}"
        for archivo in (RAIZ / "tests").rglob("test_*.py")
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8")))
        if isinstance(nodo, ast.ImportFrom)
        and nodo.module
        and nodo.module.startswith("tests.")
        and not nodo.module.startswith(permitidos)
    )
    assert infractores == []
