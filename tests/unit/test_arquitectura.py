"""Hace ejecutable la hipótesis central (NORMAS.md §1 y §2).

- adapters/ importa solo la biblioteca estándar, core.contracts, su propio paquete y los terceros
  declarados, con importación absoluta; ml/ importa de core solo core.contracts;
- core/ no importa adapters, ml, ui, api, scripts ni tests (ningún paquete de primer nivel);
- core/contracts solo depende de la biblioteca estándar.

Complementa a `git diff --stat core/` (Sesión I5): vigila la dependencia, no solo el cambio.
"""

import ast
import functools
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PAQUETES_FUERA_DEL_NUCLEO = (
    "adapters",
    "ml",
    "api",
    "scripts",
    "tests",
    "operacion",
    "migraciones",
    "seguridad",
    "paquete",
    "auditoria",
    "asistente",
    "instalador",
    "fusion",
    "aplicacion",  # RM-1 (sesion 2b): la capa de aplicacion
    "produccion",
)

#: Terceros que cada adaptador puede importar, ademas de la biblioteca estandar, `core.contracts` y
#: su propio paquete (INV-018: una sola guardia con la regla que antes solo regia para telecom).
#: Un adaptador nuevo necesita su fila: lo exige `test_toda_carpeta_de_adapters_tiene_su_regla`.
TERCEROS_POR_ADAPTADOR: dict[str, frozenset[str]] = {
    "bcv": frozenset({"xlrd", "openpyxl"}),
    "civil": frozenset({"ifcopenshell"}),
    "espacio": frozenset(
        {"sqlalchemy", "ezdxf", "ifcopenshell", "shapely", "ifctester", "xmlschema"}
    ),
    "hoja_empresa": frozenset({"openpyxl", "defusedxml", "xlsxwriter", "pdfplumber", "pdfminer"}),
    "industrial": frozenset(),
    "sistemas": frozenset(),
    "telecom": frozenset(),
    "vial": frozenset(),  # plan vial, Tarea 7: solo biblioteca estandar y core.contracts
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
        "(NORMAS.md §2). Si parece imprescindible, es un hallazgo de la investigación: "
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
    puede importar (NORMAS.md §2; spec de cierre §4, criterio D: `core/` no importa de `adapters/`,
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
    """INV-018: NORMAS.md §2 y §5 para cada adaptador, con importaciones anidadas incluidas.

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


#: Terceros de `produccion/` (Tarea 4.2 de la sesion 4): dominio puro de la arenera.
TERCEROS_DE_PRODUCCION = frozenset({"sqlalchemy", "openpyxl"})


def _prohibidos_en_produccion(archivo: Path) -> list[str]:
    """Importaciones de `archivo` que `produccion/` no admite: solo biblioteca estandar, los
    terceros declarados, `core.contracts` y su propio paquete, siempre con ruta absoluta."""
    prohibidos = []
    for modulo in _imports(archivo):
        raiz = modulo.split(".")[0]
        if raiz == "core":
            if not (modulo == "core.contracts" or modulo.startswith("core.contracts.")):
                prohibidos.append(modulo)
        elif raiz == "produccion":
            continue
        elif raiz not in _BIBLIOTECA_ESTANDAR and raiz not in TERCEROS_DE_PRODUCCION:
            prohibidos.append(modulo)
    return prohibidos + [f"{r} (relativa)" for r in _imports_relativos(archivo)]


def test_produccion_respeta_su_regla(tmp_path):
    """RT-7: `produccion/` no importa `core` salvo `core.contracts`, ni `adapters`, `api`, `ui`,
    `operacion` ni `seguridad`. Se prueba con archivos construidos y con el paquete real."""
    malo = tmp_path / "malo.py"
    malo.write_text("from core.models import Item\nimport decimal\n", encoding="utf-8")
    assert _prohibidos_en_produccion(malo) == ["core.models"]
    ajenos = ("adapters.bcv", "api.main", "ui.app", "operacion.respaldo", "seguridad.permisos")
    for modulo in ajenos:
        otro = tmp_path / "otro.py"
        otro.write_text(f"import {modulo}\n", encoding="utf-8")
        assert _prohibidos_en_produccion(otro) == [modulo]
    bueno = tmp_path / "bueno.py"
    bueno.write_text(
        "import decimal\nimport sqlalchemy\nimport openpyxl\nfrom core.contracts import x\n"
        "from produccion.modelo import Material\n",
        encoding="utf-8",
    )
    assert _prohibidos_en_produccion(bueno) == []
    archivos = _archivos("produccion")
    assert archivos, "produccion/ debe existir y tener modulos"
    hallados = {_ruta(a): _prohibidos_en_produccion(a) for a in archivos}
    assert not {k: v for k, v in hallados.items() if v}


#: Lo que cada modulo de la hoja y su composicion no importa en tiempo de ejecucion (fuera de
#: `if TYPE_CHECKING:`). Eran las reglas de `ui/composicion.py` y `ui/hoja.py`; con el retiro de
#: Streamlit (F8) pasan a sus destinos definitivos en `aplicacion/`.
PROHIBIDOS_EN_LA_HOJA: dict[str, tuple[str, ...]] = {
    # RA-2: no escribe presupuestos (`core.budget`) ni toca SQL a mano. `core.catalog` ya no se
    # vigila: `aplicacion/composicion.py` guarda la composicion (`guardar_composicion`) con el.
    "aplicacion/composicion.py": ("streamlit", "pandas", "sqlalchemy", "core.budget"),
    # SF 1.8: la hoja orquesta el borrador y la elaboracion sin pintar (FR-5: sin Streamlit).
    "aplicacion/hoja.py": ("streamlit", "pandas"),
}


def test_la_carpeta_ui_no_existe():
    """Retiro de Streamlit (F8): ya no hay interfaz clasica; nada vuelve a crear `ui/`."""
    assert not (RAIZ / "ui").exists()


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


@pytest.mark.parametrize("modulo", sorted(PROHIBIDOS_EN_LA_HOJA))
def test_la_hoja_respeta_sus_importaciones_prohibidas(modulo):
    """INV-043 (criterio S, spec de cierre §4) y reglas de C3: cada modulo importa solo lo que su
    responsabilidad pide."""
    importados = _imports_de_ejecucion(RAIZ / modulo)
    prohibidos = {
        nombre
        for nombre in importados
        for prefijo in PROHIBIDOS_EN_LA_HOJA[modulo]
        if nombre == prefijo or nombre.startswith(prefijo + ".")
    }
    assert not prohibidos, f"{modulo} importa {sorted(prohibidos)}"


def test_una_sola_lectura_de_celdas_de_tabla():
    """INV-046: las celdas de las tablas se leen solo con `aplicacion.composicion.texto_de_celda`;
    ningun otro modulo de `aplicacion/` define su propia copia."""
    copias = sorted(
        archivo.relative_to(RAIZ).as_posix()
        for archivo in (RAIZ / "aplicacion").rglob("*.py")
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8")))
        if isinstance(nodo, ast.FunctionDef) and nodo.name in {"_celda_de_cantidad", "_texto"}
    )
    assert copias == []


def _nombres_importados(archivo: Path) -> list[tuple[int, str]]:
    """`(linea, modulo)` de cada import del archivo, con los relativos resueltos a nombre absoluto.

    Cubre `import a.b`, `from a.b import c` (registra `a.b` y `a.b.c`, porque `c` puede ser un
    submodulo) y `from ..b import c` (`level > 0`), resuelto desde el paquete del archivo.
    """
    paquete = archivo.relative_to(RAIZ).with_suffix("").parts[:-1]
    nombres: list[tuple[int, str]] = []
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            nombres.extend((nodo.lineno, alias.name) for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:
                base = paquete[: len(paquete) - (nodo.level - 1)]
                modulo = ".".join((*base, *([nodo.module] if nodo.module else [])))
            else:
                modulo = nodo.module or ""
            nombres.append((nodo.lineno, modulo))
            nombres.extend((nodo.lineno, f"{modulo}.{alias.name}") for alias in nodo.names)
    return nombres


def test_ningun_modulo_de_prueba_importa_de_otro_modulo_de_prueba():
    """INV-052 (A-6): lo compartido entre pruebas vive en `tests/fixtures/`. Los modulos de prueba,
    las fixtures y **todo** `conftest.py` (el raiz y los de cada subcarpeta, como
    `tests/integration/conftest.py`: O-7 de la revision de A5) solo importan de `tests.fixtures` o
    de `tests.conftest`, nunca de un modulo de prueba, sea con `from`, con `import` o con un import
    relativo (M-1 de la revision de A5)."""
    permitidos = ("tests.fixtures", "tests.conftest")
    conftests = sorted((RAIZ / "tests").rglob("conftest.py"))
    assert RAIZ / "tests" / "integration" / "conftest.py" in conftests
    archivos = sorted(
        {
            *(RAIZ / "tests").rglob("test_*.py"),
            *(RAIZ / "tests" / "fixtures").rglob("*.py"),
            *conftests,
        }
    )
    infractores = sorted(
        {
            f"{archivo.relative_to(RAIZ).as_posix()}:{linea}"
            for archivo in archivos
            for linea, nombre in _nombres_importados(archivo)
            if nombre.startswith("tests.") and not nombre.startswith(permitidos)
        }
    )
    assert infractores == []


#: Paquetes que la API no importa en tiempo de ejecucion (ARQ-5 de la revision de arquitectura de
#: GC4): docs/arquitectura.md §4 declara que `api` no depende de `scripts` ni de `tests`, y la API
#: no es un cliente de la interfaz. Una ruta que importara `scripts.seed` arrastraria `tests/`.
PROHIBIDOS_EN_API = ("scripts", "tests", "ui")


def _prohibido_en_api(modulo: str) -> bool:
    """True si `modulo` pertenece a un paquete de `PROHIBIDOS_EN_API` (paquete, no prefijo)."""
    return modulo.split(".")[0] in PROHIBIDOS_EN_API


def test_la_regla_de_la_api_distingue_paquetes_de_prefijos():
    """Las mordidas de `_prohibido_en_api`, fijadas en los dos sentidos."""
    assert _prohibido_en_api("scripts.seed")
    assert _prohibido_en_api("tests")
    assert _prohibido_en_api("tests.fixtures.apu_linea_base")
    assert _prohibido_en_api("ui.caso")
    assert not _prohibido_en_api("uimodulo")
    assert not _prohibido_en_api("scriptsx")
    assert not _prohibido_en_api("core.budget")
    assert not _prohibido_en_api("ml.normalization")


def test_la_api_no_importa_scripts_tests_ni_ui():
    """ARQ-5 (GC4), por archivo: ningun modulo de `api/` importa `scripts`, `tests` ni `ui` en
    tiempo de ejecucion, tampoco de forma perezosa (`_imports_de_ejecucion`)."""
    archivos = _archivos("api")
    assert RAIZ / "api" / "rutas" / "presupuestos.py" in archivos
    prohibidos = sorted(
        f"{_ruta(archivo)}: {modulo}"
        for archivo in archivos
        for modulo in _imports_de_ejecucion(archivo)
        if _prohibido_en_api(modulo)
    )
    assert prohibidos == []


def test_importar_la_api_no_carga_scripts_tests_ni_ui():
    """ARQ-5 (GC4), transitivo: importar `api.main` en un proceso limpio no deja en `sys.modules`
    ningun modulo de `scripts`, `tests` ni `ui`, aunque llegara a ellos a traves de otro paquete.
    `subprocess` se importa aqui para no desplazar las anclas de este archivo que citan los
    documentos (`:23`, `:110-123`, `:196-207`)."""
    import subprocess

    codigo = (
        "import sys\n"
        "import api.main\n"
        f"print(sorted({{n for n in sys.modules if n.split('.')[0] in {PROHIBIDOS_EN_API!r}}}))\n"
    )
    salida = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )
    assert salida.stdout.strip() == "[]", salida.stdout


def _importado_de_tests(archivo: Path) -> list[str]:
    """Lo que `archivo` importa del paquete `tests`, con el nombre completo: `from tests import
    fixtures` cuenta como `tests.fixtures`, no como `tests`. Incluye las importaciones perezosas."""
    nombres: list[str] = []
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            nombres.extend(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            if nodo.module == "tests":
                nombres.extend(f"tests.{alias.name}" for alias in nodo.names)
            else:
                nombres.append(nodo.module)
    return [nombre for nombre in nombres if nombre == "tests" or nombre.startswith("tests.")]


def _prohibidos_en_scripts(archivo: Path) -> list[str]:
    """Lo que `archivo` importa de `tests` fuera del paquete `tests.fixtures`."""
    return [
        nombre
        for nombre in _importado_de_tests(archivo)
        if nombre != "tests.fixtures" and not nombre.startswith("tests.fixtures.")
    ]


def test_scripts_solo_importa_de_tests_sus_fixtures():
    """ARQ-5 (GC4): `scripts/` depende de `tests` solo por `tests.fixtures`, la fuente unica de la
    linea base y de los casos (docs/arquitectura.md §4); nunca de un modulo de prueba ni de un
    `conftest.py`. La guardia no es ciega: `scripts/seed.py` importa `tests.fixtures`."""
    assert _importado_de_tests(RAIZ / "scripts" / "seed.py")
    prohibidos = sorted(
        f"{_ruta(archivo)}: {nombre}"
        for archivo in _archivos("scripts")
        for nombre in _prohibidos_en_scripts(archivo)
    )
    assert prohibidos == []


def test_la_guardia_de_scripts_ve_cada_forma_de_importar_tests(tmp_path):
    """Las mordidas de `_prohibidos_en_scripts` en los dos sentidos, como
    `test_la_guardia_del_marco_ve_cada_forma_de_importarlo`: cada forma de llegar a `tests` fuera
    de `tests.fixtures` se detecta; las formas permitidas y un nombre que solo empieza igual, no."""
    fuentes = {
        "from tests.fixtures import apu_linea_base\n": False,
        "from tests.fixtures.apu_linea_base import PARAMETROS\n": False,
        "from tests import fixtures\n": False,
        "import tests.fixtures.apu_linea_base\n": False,
        "import testsuite\n": False,
        "from tests.conftest import huella\n": True,
        "from tests import conftest\n": True,
        "import tests\n": True,
        "import tests.unit.test_costing\n": True,
        "def perezosa():\n    from tests.integration import conftest\n": True,
    }
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"script_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = bool(_prohibidos_en_scripts(archivo))
    assert detectadas == fuentes


# --- SF1: el grafo de dependencias de adapters/espacio y de aplicacion.hoja no tiene ciclos ----


def _modulo_de(archivo: Path) -> str:
    """Nombre punteado de un archivo (`adapters/espacio/__init__.py` -> `adapters.espacio`)."""
    partes = archivo.relative_to(RAIZ).with_suffix("").parts
    return ".".join(partes[:-1] if partes[-1] == "__init__" else partes)


def _hay_ciclo(grafo: dict[str, set[str]]) -> list[str] | None:
    """Un ciclo del grafo (lista de nodos) o `None`; busqueda en profundidad con colores."""
    estado: dict[str, int] = {}  # 1 = en la pila, 2 = terminado

    def visitar(nodo: str, pila: list[str]) -> list[str] | None:
        estado[nodo] = 1
        for vecino in sorted(grafo.get(nodo, ())):
            if estado.get(vecino) == 1:
                return (
                    [*pila[pila.index(vecino) :], nodo, vecino]
                    if vecino in pila
                    else [nodo, vecino]
                )
            if vecino not in estado and (ciclo := visitar(vecino, [*pila, nodo])):
                return ciclo
        estado[nodo] = 2
        return None

    for nodo in sorted(grafo):
        if nodo not in estado and (ciclo := visitar(nodo, [])):
            return ciclo
    return None


def _grafo_de_espacio() -> dict[str, set[str]]:
    modulos = {_modulo_de(a) for a in _archivos("adapters/espacio")}
    grafo: dict[str, set[str]] = {m: set() for m in modulos}
    for archivo in _archivos("adapters/espacio"):
        origen = _modulo_de(archivo)
        for importado in _imports(archivo):
            if importado.startswith("adapters.espacio") and importado in modulos:
                grafo[origen].add(importado)
    return grafo


def test_el_detector_de_ciclos_ve_un_ciclo_y_no_ve_uno_donde_no_lo_hay():
    assert _hay_ciclo({"a": {"b"}, "b": {"c"}, "c": {"a"}}) is not None
    assert _hay_ciclo({"a": {"b", "c"}, "b": {"c"}, "c": set()}) is None


def test_el_grafo_interno_de_adapters_espacio_es_aciclico():
    """Ningun modulo de `adapters/espacio` depende, directa o indirectamente, de si mismo."""
    grafo = _grafo_de_espacio()
    assert {"adapters.espacio.modelo", "adapters.espacio.reglas"} <= set(grafo)  # lo recorre
    assert _hay_ciclo(grafo) is None, _hay_ciclo(grafo)


def test_ningun_submodulo_de_espacio_importa_el_paquete_raiz():
    """`from adapters.espacio import X` desde un submodulo cierra un ciclo con `__init__`, que los
    importa a todos: los submodulos se importan entre si por su ruta completa."""
    raiz = "adapters.espacio"
    culpables = [
        _ruta(a)
        for a in _archivos("adapters/espacio")
        if a.name != "__init__.py" and raiz in set(_imports(a))
    ]
    assert not culpables, culpables


def test_la_hoja_depende_de_adapters_espacio_y_este_no_depende_de_aplicacion():
    """La arista es aplicacion.hoja -> adapters.espacio y no existe la inversa: sin ciclo."""
    de_hoja = {m for m in _imports(RAIZ / "aplicacion" / "hoja.py") if m.startswith("adapters")}
    assert de_hoja and all(
        m == "adapters.espacio" or m.startswith("adapters.espacio.") for m in de_hoja
    ), de_hoja
    inversa = [
        f"{_ruta(a)}: {m}"
        for a in _archivos("adapters/espacio")
        for m in _imports(a)
        if m == "ui" or m.startswith(("ui.", "aplicacion"))
    ]
    assert not inversa, inversa


#: RM-1 (sesion 2b): la capa de aplicacion (`aplicacion/`) es lo que la interfaz clasica y la API
#: comparten sin Streamlit; no conoce a ninguna de las dos, ni a los guiones ni a las pruebas.
PROHIBIDOS_EN_APLICACION = ("streamlit", "ui", "api", "scripts", "tests")


def test_la_capa_de_aplicacion_no_importa_interfaz_api_guiones_ni_pruebas():
    """RM-1, por archivo: tambien las importaciones perezosas (`_imports_de_ejecucion`)."""
    archivos = _archivos("aplicacion")
    assert RAIZ / "aplicacion" / "proyectos.py" in archivos  # la guardia no recorre una lista vacia
    assert RAIZ / "aplicacion" / "hoja.py" in archivos  # la copia del Plan C (T10) tambien
    prohibidos = sorted(
        f"{_ruta(archivo)}: {modulo}"
        for archivo in archivos
        for modulo in _imports_de_ejecucion(archivo)
        if modulo.split(".")[0] in PROHIBIDOS_EN_APLICACION
    )
    assert prohibidos == []


def test_importar_la_capa_de_aplicacion_no_carga_interfaz_api_guiones_ni_pruebas():
    """RM-1, transitivo: importar cada modulo de `aplicacion/` en un proceso limpio no deja en
    `sys.modules` nada de `streamlit`, `ui`, `api`, `scripts` ni `tests`."""
    import subprocess

    modulos = sorted(
        ".".join(archivo.relative_to(RAIZ).with_suffix("").parts)
        for archivo in _archivos("aplicacion")
        if archivo.name != "__init__.py"
    )
    assert "aplicacion.proyectos" in modulos
    assert "aplicacion.hoja" in modulos  # T10, Plan C: la copia de la hoja no carga `ui`
    codigo = (
        "import importlib, sys\n"
        f"for m in {modulos!r}: importlib.import_module(m)\n"
        "print(sorted({n for n in sys.modules "
        f"if n.split('.')[0] in {PROHIBIDOS_EN_APLICACION!r}}}))\n"
    )
    salida = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )
    assert salida.stdout.strip() == "[]", salida.stdout


def test_la_elaboracion_toma_el_guardado_de_la_composicion():
    """RB-3 (ola 3, S2-B): `guardar_composicion` y `Guardado` viven en `aplicacion/composicion.py`
    (la ruta de guardado de la API no puede importar `ui/`); `aplicacion/elaboracion.py` no los
    define. (F5: se retiro el puente `ui/elaboracion.py` que los reexportaba.)"""
    arbol = ast.parse((RAIZ / "aplicacion" / "elaboracion.py").read_text(encoding="utf-8"))
    definidos = {
        nodo.name
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef)
    }
    assert definidos.isdisjoint({"Guardado", "guardar_composicion"})


def test_solo_cadena_usa_formato_legado():
    """VB-1: `formato_legado` es un contexto de solo transicion (reconocer huellas selladas antes);
    solo `core/budget/cadena.py` lo usa, `canonico.py` lo define;
    `aplicacion/entrega.py` pregunta con `cadena.formato_de_sellado`.
    Nadie mas (adapters, ui, api, otro modulo del nucleo) puede escribir con el."""
    permitidos = {
        "core/budget/canonico.py",
        "core/budget/cadena.py",
    }
    usan: set[str] = set()
    for paquete in ("core", "aplicacion", *PAQUETES_FUERA_DEL_NUCLEO):
        if paquete == "tests":
            continue
        for archivo in _archivos(paquete):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
            for nodo in ast.walk(arbol):
                nombre = (
                    nodo.id
                    if isinstance(nodo, ast.Name)
                    else nodo.attr
                    if isinstance(nodo, ast.Attribute)
                    else nodo.name
                    if isinstance(nodo, ast.alias)
                    else None
                )
                if nombre == "formato_legado":
                    usan.add(_ruta(archivo))
    assert usan <= permitidos, f"usan formato_legado sin permiso: {sorted(usan - permitidos)}"
    assert "core/budget/cadena.py" in usan  # la guardia no queda vacia


# --- N5 (arbitraje F5/F7/F8, revision de correcciones): fusion y aplicacion sin ciclo -----------
#
# `fusion/apu_por_hoja.py` importaba `aplicacion.cifras` y `operacion.config`, y
# `aplicacion/desperdicio.py` importaba `fusion.desperdicio`: un ciclo entre paquetes que ninguna
# guardia vigilaba. `aplicacion.cifras` no se puede mudar (la importan `aplicacion/hoja.py` y
# `aplicacion/composicion.py`, archivos congelados del experimento), asi que el ciclo se corta del
# otro lado: `aplicacion` no importa `fusion`, la formula del desperdicio vive en una regla pura de
# `aplicacion`, y de `aplicacion` fusion solo toma reglas puras (que solo usan la biblioteca
# estandar: no arrastran la capa). La carpeta de perfiles se la pasa a fusion quien llama.

#: Lo unico de `aplicacion/` que `fusion/` puede importar.
REGLAS_PURAS_DE_APLICACION = frozenset({"aplicacion.cifras", "aplicacion.regla_desperdicio"})


def test_aplicacion_no_importa_fusion():
    culpables = sorted(
        f"{_ruta(archivo)}: {modulo}"
        for archivo in _archivos("aplicacion")
        for modulo in _imports_de_ejecucion(archivo)
        if modulo.split(".")[0] == "fusion"
    )
    assert culpables == []


def test_de_aplicacion_fusion_solo_importa_reglas_puras():
    """Con el modulo completo (`from aplicacion.cifras import X`): `from aplicacion import cifras`
    tambien se rechaza, para que la regla se lea en una sola forma."""
    usadas = {
        (_ruta(archivo), modulo)
        for archivo in _archivos("fusion")
        for modulo in _imports(archivo)
        if modulo.split(".")[0] == "aplicacion"
    }
    ajenas = sorted(f"{r}: {m}" for r, m in usadas if m not in REGLAS_PURAS_DE_APLICACION)
    assert ajenas == []
    assert {m for _, m in usadas} == REGLAS_PURAS_DE_APLICACION  # la guardia no queda vacia


@pytest.mark.parametrize("modulo", sorted(REGLAS_PURAS_DE_APLICACION))
def test_una_regla_pura_de_aplicacion_solo_usa_la_biblioteca_estandar(modulo):
    archivo = RAIZ / f"{modulo.replace('.', '/')}.py"
    assert archivo.is_file(), f"{modulo} no existe"
    ajenos = [m for m in _imports(archivo) if m.split(".")[0] not in _BIBLIOTECA_ESTANDAR]
    assert ajenos == [], f"{modulo} importa {ajenos}: una regla pura no arrastra otra capa"


def test_fusion_no_importa_la_configuracion_de_la_instalacion():
    """Donde viven los datos (`operacion.config`) lo decide la instalacion y lo pasa quien llama:
    fusion no lo lee por su cuenta."""
    culpables = sorted(
        f"{_ruta(archivo)}: {modulo}"
        for archivo in _archivos("fusion")
        for modulo in _imports_de_ejecucion(archivo)
        if modulo == "operacion.config" or modulo.startswith("operacion.config.")
    )
    assert culpables == []


# --- Plan de desenredo, ola 1 (2026-11-17): guardias con lista congelada ------------------------
#
# Cada guardia fotografia la deuda de capas medida sobre `feature/depuracion-unida` (a802d728) y
# falla si empeora; su prueba `_sin_sobrantes` falla si mejora y nadie borra la fila: la lista solo
# se achica (docs/planes/2026-11-17-plan-desenredo.md, ola 1). Las ayudas viven aqui porque ningun
# modulo de prueba importa de otro
# (`test_ningun_modulo_de_prueba_importa_de_otro_modulo_de_prueba`).

#: Los paquetes de primer nivel del repositorio, nucleo incluido.
PAQUETES_INTERNOS = frozenset(PAQUETES_FUERA_DEL_NUCLEO) | {"core"}
_SOLO_TIPADO = frozenset({"TYPE_CHECKING", "typing.TYPE_CHECKING"})


def _arbol(archivo: Path) -> ast.Module:
    return ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))


def _nodos_de_tipado(arbol: ast.AST) -> set[int]:
    """`id` de cada nodo bajo un `if TYPE_CHECKING:` (solo el cuerpo; el `else` se ejecuta)."""
    return {
        id(nodo)
        for bloque in ast.walk(arbol)
        if isinstance(bloque, ast.If) and ast.unparse(bloque.test) in _SOLO_TIPADO
        for sentencia in bloque.body
        for nodo in ast.walk(sentencia)
    }


@functools.cache
def _imports_con_linea(archivo: Path, raiz: Path = RAIZ) -> tuple[tuple[int, str], ...]:
    """`(linea, modulo)` de cada import de ejecucion de `archivo`: fuera de `if TYPE_CHECKING:`,
    con los perezosos (dentro de funciones) y los relativos resueltos a nombre absoluto.
    `from a import b` registra `a` y `a.b`, porque `b` puede ser un submodulo. Se guarda en cache:
    las guardias de la ola 1 leen cada archivo una sola vez."""
    arbol = _arbol(archivo)
    tipado = _nodos_de_tipado(arbol)
    paquete = archivo.relative_to(raiz).with_suffix("").parts[:-1]
    nombres: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if id(nodo) in tipado:
            continue
        if isinstance(nodo, ast.Import):
            nombres.extend((nodo.lineno, alias.name) for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:
                base = paquete[: len(paquete) - (nodo.level - 1)]
                modulo = ".".join((*base, *([nodo.module] if nodo.module else [])))
            else:
                modulo = nodo.module or ""
            nombres.append((nodo.lineno, modulo))
            nombres.extend((nodo.lineno, f"{modulo}.{alias.name}") for alias in nodo.names)
    return tuple(sorted(nombres))


# --- Tarea 1.1: matriz de dependencias entre paquetes -------------------------------------------


def _imports_de_ejecucion_de_paquete(paquete: str, raiz: Path = RAIZ) -> dict[str, set[str]]:
    """Paquete interno de primer nivel importado por `paquete` -> `archivo:linea` que lo importan.

    Incluye los imports locales dentro de funciones y excluye los de `if TYPE_CHECKING:`; el propio
    paquete no cuenta (no es una dependencia entre paquetes)."""
    aristas: dict[str, set[str]] = {}
    for archivo in sorted((raiz / paquete).rglob("*.py")):
        for linea, modulo in _imports_con_linea(archivo, raiz):
            destino = modulo.split(".")[0]
            if destino in PAQUETES_INTERNOS and destino != paquete:
                sitio = f"{archivo.relative_to(raiz).as_posix()}:{linea}"
                aristas.setdefault(destino, set()).add(sitio)
    return aristas


#: Lista blanca de cada paquete (2026-11-17, medida sobre a802d728). Es la fuente de las
#: dependencias entre paquetes mientras `docs/arquitectura.md` §4 espera su enmienda (aval del
#: tutor). Una arista nueva hace fallar la guardia; una que desaparece obliga a borrarla.
DEPENDENCIAS_PERMITIDAS: dict[str, frozenset[str]] = {
    "adapters": frozenset({"core"}),  # solo core.contracts: lo afina la guardia por adaptador
    "api": frozenset(
        {
            "adapters",
            "aplicacion",
            "asistente",
            "auditoria",
            "core",
            "fusion",
            "ml",
            "operacion",
            "paquete",
            "produccion",
            "seguridad",
        }
    ),
    "aplicacion": frozenset(
        {
            "adapters",
            "asistente",
            "auditoria",
            "core",
            "ml",
            "operacion",
            "paquete",
            "produccion",
            "seguridad",
        }
    ),
    "asistente": frozenset(
        {
            "adapters",
            "aplicacion",  # ciclo, ola 5
            "core",
            "operacion",
            "seguridad",
        }
    ),
    "auditoria": frozenset({"adapters", "core", "paquete", "seguridad"}),
    "core": frozenset(),
    "fusion": frozenset(
        {
            "adapters",
            "aplicacion",  # ciclo, ola 5
            "auditoria",
            "core",
            "operacion",
        }
    ),
    "instalador": frozenset(
        {
            "ml",
            "operacion",
            "tests",  # cierra un ciclo con tests -> instalador; 1.3 no mira tests ni scripts
        }
    ),
    "migraciones": frozenset(
        {
            "adapters",
            "aplicacion",  # ciclo, ola 5
            "asistente",  # ciclo, ola 5
            "core",
            "fusion",  # ciclo, ola 5
            "paquete",
            "produccion",
            "seguridad",
        }
    ),
    "ml": frozenset({"core"}),  # solo core.contracts (test_ml_solo_importa_core_contracts...)
    "operacion": frozenset(
        {
            "migraciones",
            "ml",
            "scripts",  # cierra un ciclo con scripts -> operacion; 1.3 no mira tests ni scripts
            "seguridad",
        }
    ),
    "paquete": frozenset({"core", "seguridad"}),
    "produccion": frozenset(),
    "scripts": frozenset(
        {
            "adapters",
            "api",
            "aplicacion",
            "asistente",
            "core",
            "fusion",
            "instalador",
            "ml",
            "operacion",
            "seguridad",
            "tests",
        }
    ),
    "seguridad": frozenset(
        {
            "operacion",  # ciclo, ola 5
        }
    ),
    "tests": PAQUETES_INTERNOS - {"tests"},  # las pruebas recorren todos los paquetes
}


def test_cada_paquete_solo_importa_su_lista_blanca_de_la_matriz():
    nuevas = sorted(
        f"{paquete} -> {destino} ({min(sitios)}; {len(sitios)} sitios)"
        for paquete in sorted(PAQUETES_INTERNOS)
        for destino, sitios in _imports_de_ejecucion_de_paquete(paquete).items()
        if destino not in DEPENDENCIAS_PERMITIDAS.get(paquete, frozenset())
    )
    assert nuevas == [], "aristas fuera de DEPENDENCIAS_PERMITIDAS:\n" + "\n".join(nuevas)


def test_la_matriz_sin_sobrantes():
    """Una arista permitida que ya nadie usa se borra de la matriz: la lista solo se achica."""
    sobrantes = sorted(
        f"{paquete} -> {destino}"
        for paquete, destinos in DEPENDENCIAS_PERMITIDAS.items()
        for destino in destinos - set(_imports_de_ejecucion_de_paquete(paquete))
    )
    assert sobrantes == [], "aristas que ya no existen; borrarlas de la matriz: " + ", ".join(
        sobrantes
    )


def test_la_matriz_cubre_todo_paquete():
    assert set(DEPENDENCIAS_PERMITIDAS) == set(PAQUETES_INTERNOS)


def test_la_matriz_ve_un_import_local(tmp_path):
    carpeta = tmp_path / "falso"
    carpeta.mkdir()
    (carpeta / "modulo.py").write_text(
        "import decimal\n\n\ndef f():\n    from api import x\n    return x\n", encoding="utf-8"
    )
    assert _imports_de_ejecucion_de_paquete("falso", raiz=tmp_path) == {
        "api": {"falso/modulo.py:5"}
    }


def test_la_matriz_ignora_type_checking(tmp_path):
    carpeta = tmp_path / "falso"
    carpeta.mkdir()
    (carpeta / "modulo.py").write_text(
        "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from api import x\n"
        "else:\n    from seguridad import y\n",
        encoding="utf-8",
    )
    assert _imports_de_ejecucion_de_paquete("falso", raiz=tmp_path) == {
        "seguridad": {"falso/modulo.py:6"}
    }


# --- Tarea 1.2: las rutas no consultan la base ni entran al nucleo por dentro -------------------


@functools.cache
def _es_modulo(nombre: str, raiz: Path = RAIZ) -> bool:
    ruta = raiz.joinpath(*nombre.split("."))
    return ruta.with_suffix(".py").is_file() or (ruta / "__init__.py").is_file()


@functools.cache
def _modulos_usados(archivo: Path, raiz: Path = RAIZ) -> tuple[tuple[int, str], ...]:
    """`(linea, modulo)` que `archivo` carga en ejecucion: `from a import b` cuenta `a.b` si `b` es
    un submodulo y `a` si no lo es (una funcion o una clase de `a`). Sin `if TYPE_CHECKING:`."""
    arbol = _arbol(archivo)
    tipado = _nodos_de_tipado(arbol)
    paquete = archivo.relative_to(raiz).with_suffix("").parts[:-1]
    usados: set[tuple[int, str]] = set()
    for nodo in ast.walk(arbol):
        if id(nodo) in tipado:
            continue
        if isinstance(nodo, ast.Import):
            usados.update((nodo.lineno, alias.name) for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:
                base = paquete[: len(paquete) - (nodo.level - 1)]
                modulo = ".".join((*base, *([nodo.module] if nodo.module else [])))
            else:
                modulo = nodo.module or ""
            for alias in nodo.names:
                hijo = f"{modulo}.{alias.name}"
                usados.add((nodo.lineno, hijo if _es_modulo(hijo, raiz) else modulo))
    return tuple(sorted(usados))


def _archivos_de_rutas(raiz: Path = RAIZ) -> list[Path]:
    return sorted((raiz / "api" / "rutas").rglob("*.py"))


def _llamadas_select(archivo: Path) -> list[int]:
    """Lineas de cada llamada `select(...)` o `x.select(...)`, por AST: un comentario no cuenta."""
    return sorted(
        nodo.lineno
        for nodo in ast.walk(_arbol(archivo))
        if isinstance(nodo, ast.Call)
        and (
            (isinstance(nodo.func, ast.Name) and nodo.func.id == "select")
            or (isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "select")
        )
    )


def _importa_modelos_del_nucleo(archivo: Path, raiz: Path = RAIZ) -> list[int]:
    """Lineas donde `archivo` importa `core.models` (`from core import models` incluido)."""
    return sorted(
        {
            linea
            for linea, modulo in _modulos_usados(archivo, raiz)
            if modulo == "core.models" or modulo.startswith("core.models.")
        }
    )


def _es_nucleo_de_superficie(modulo: str) -> bool:
    """Lo unico del nucleo que una ruta puede importar: los contratos y la presentacion de texto."""
    return (
        modulo == "core.contracts"
        or modulo.startswith("core.contracts.")
        or modulo == "core.verification.texto"
    )


def _nucleo_profundo(archivo: Path, raiz: Path = RAIZ) -> dict[str, int]:
    """Modulo del nucleo que no es de superficie -> primera linea que lo importa. `core.models`
    queda fuera: lo vigila su propia lista (`MODELOS_EN_RUTAS`)."""
    hallados: dict[str, int] = {}
    for linea, modulo in _modulos_usados(archivo, raiz):
        es_modelo = modulo == "core.models" or modulo.startswith("core.models.")
        if modulo.startswith("core.") and not es_modelo and not _es_nucleo_de_superficie(modulo):
            hallados.setdefault(modulo, linea)
    return hallados


#: Llamadas `select(` por archivo de `api/rutas` (2026-11-17, a802d728): la ola 3 las muda a
#: `aplicacion`, `seguridad` y `produccion`.
SELECT_EN_RUTAS: dict[str, int] = {
    "api/rutas/admin_claves_api.py": 1,
    "api/rutas/admin_empresas_registradas.py": 1,
    "api/rutas/cuentas.py": 1,
    "api/rutas/entregas.py": 1,
    "api/rutas/listas.py": 1,
    "api/rutas/presupuestos.py": 4,
    "api/rutas/produccion.py": 2,
    "api/rutas/reajuste.py": 1,
    "api/rutas/rendimientos.py": 1,
}

#: Archivos de `api/rutas` que importan `core.models` (2026-11-17, a802d728).
MODELOS_EN_RUTAS: frozenset[str] = frozenset(
    {
        "api/rutas/entregas.py",
        "api/rutas/listas.py",
        "api/rutas/presupuestos.py",
        "api/rutas/reajuste.py",
        "api/rutas/rendimientos.py",
        "api/rutas/revision.py",
    }
)

#: Archivo de `api/rutas` -> modulos del nucleo que no son `core.contracts.*` ni
#: `core.verification.texto` (2026-11-17, a802d728).
NUCLEO_PROFUNDO_EN_RUTAS: dict[str, frozenset[str]] = {
    "api/rutas/aprobaciones.py": frozenset({"core.catalog"}),
    "api/rutas/auditorias.py": frozenset({"core.budget.canonico"}),
    "api/rutas/busqueda.py": frozenset({"core.catalog"}),
    "api/rutas/catalogo.py": frozenset({"core.catalog"}),
    "api/rutas/control.py": frozenset({"core.budget.control", "core.catalog"}),
    "api/rutas/entregas.py": frozenset({"core.budget.canonico"}),
    "api/rutas/hoja.py": frozenset({"core.budget.moneda", "core.catalog"}),
    "api/rutas/listas.py": frozenset({"core.catalog", "core.catalog.precios"}),
    "api/rutas/mercado.py": frozenset(
        {"core.catalog", "core.catalog.errores", "core.catalog.moneda"}
    ),
    "api/rutas/obras.py": frozenset({"core.catalog", "core.catalog.indices"}),
    "api/rutas/presupuestos.py": frozenset(
        {"core.budget", "core.budget.instantanea", "core.catalog", "core.verification.informe"}
    ),
    "api/rutas/proyectos.py": frozenset({"core.catalog"}),
    "api/rutas/reajuste.py": frozenset({"core.budget.reajuste"}),
    "api/rutas/rendimientos.py": frozenset({"core.catalog"}),
    "api/rutas/revision.py": frozenset({"core.budget.comparacion"}),
    "api/rutas/sesion.py": frozenset({"core.catalog"}),
    "api/rutas/tablero.py": frozenset({"core.catalog"}),
}


def test_las_rutas_no_consultan_la_base():
    peores = []
    for archivo in _archivos_de_rutas():
        lineas = _llamadas_select(archivo)
        congelado = SELECT_EN_RUTAS.get(_ruta(archivo), 0)
        if len(lineas) > congelado:
            sitios = ", ".join(f"{_ruta(archivo)}:{linea}" for linea in lineas)
            peores.append(f"{len(lineas)} select() (congelado {congelado}): {sitios}")
    assert peores == [], "la consulta va en aplicacion/, no en la ruta:\n" + "\n".join(peores)


def test_las_rutas_no_consultan_la_base_sin_sobrantes():
    sobrantes = []
    for ruta, congelado in sorted(SELECT_EN_RUTAS.items()):
        hoy = len(_llamadas_select(RAIZ / ruta)) if (RAIZ / ruta).is_file() else 0
        if hoy < congelado:
            sobrantes.append(f"{ruta}: {congelado} -> {hoy}" + ("" if hoy else " (borrar la fila)"))
    assert sobrantes == [], "bajar SELECT_EN_RUTAS: " + "; ".join(sobrantes)


def test_las_rutas_no_consultan_la_base_ve_la_falta(tmp_path):
    archivo = tmp_path / "ruta.py"
    archivo.write_text(
        "import sqlalchemy as sa\nfrom sqlalchemy import select\n\n"
        "# select(Partida) en un comentario no cuenta\n"
        'consulta = select(1).where(True)\notra = sa.select(2)\ntexto = "select(3)"\n',
        encoding="utf-8",
    )
    assert _llamadas_select(archivo) == [5, 6]


def test_las_rutas_no_importan_los_modelos_del_nucleo():
    nuevos = sorted(
        f"{_ruta(archivo)}:{lineas[0]}"
        for archivo in _archivos_de_rutas()
        if (lineas := _importa_modelos_del_nucleo(archivo))
        and _ruta(archivo) not in MODELOS_EN_RUTAS
    )
    assert nuevos == [], f"importan core.models fuera de MODELOS_EN_RUTAS: {nuevos}"


def test_las_rutas_no_importan_los_modelos_del_nucleo_sin_sobrantes():
    sobrantes = sorted(
        ruta
        for ruta in MODELOS_EN_RUTAS
        if not (RAIZ / ruta).is_file() or not _importa_modelos_del_nucleo(RAIZ / ruta)
    )
    assert sobrantes == [], (
        f"ya no importan core.models; borrarlas de MODELOS_EN_RUTAS: {sobrantes}"
    )


def test_las_rutas_no_importan_los_modelos_del_nucleo_ve_la_falta(tmp_path):
    fuentes = {
        "from core.models import Partida\n": [1],
        "from core import models\n": [1],
        "import core.models\n": [1],
        "def f():\n    from core.models import Insumo\n": [2],
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from core.models import X\n": [],
        "from core.contracts import Dominio\n": [],
    }
    for paquete in ("core", "core/models"):
        (tmp_path / paquete).mkdir()
        (tmp_path / paquete / "__init__.py").write_text("", encoding="utf-8")
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"ruta_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = _importa_modelos_del_nucleo(archivo, raiz=tmp_path)
    assert detectadas == fuentes


def test_las_rutas_no_entran_al_nucleo_por_dentro():
    nuevos = sorted(
        f"{_ruta(archivo)}:{linea} {modulo}"
        for archivo in _archivos_de_rutas()
        for modulo, linea in _nucleo_profundo(archivo).items()
        if modulo not in NUCLEO_PROFUNDO_EN_RUTAS.get(_ruta(archivo), frozenset())
    )
    assert nuevos == [], (
        "del nucleo, una ruta solo importa los contratos y el texto:\n" + "\n".join(nuevos)
    )


def test_las_rutas_no_entran_al_nucleo_por_dentro_sin_sobrantes():
    sobrantes = sorted(
        f"{ruta}: {modulo}"
        for ruta, modulos in NUCLEO_PROFUNDO_EN_RUTAS.items()
        for modulo in modulos
        - (set(_nucleo_profundo(RAIZ / ruta)) if (RAIZ / ruta).is_file() else set())
    )
    assert sobrantes == [], f"borrar de NUCLEO_PROFUNDO_EN_RUTAS: {sobrantes}"


def test_las_rutas_no_entran_al_nucleo_por_dentro_ve_la_falta(tmp_path):
    for paquete in ("core", "core/budget", "core/verification", "core/contracts"):
        (tmp_path / paquete).mkdir(parents=True)
        (tmp_path / paquete / "__init__.py").write_text("", encoding="utf-8")
    for modulo in ("core/budget/cadena.py", "core/verification/texto.py"):
        (tmp_path / modulo).write_text("", encoding="utf-8")
    ruta = tmp_path / "api" / "rutas" / "obra.py"
    ruta.parent.mkdir(parents=True)
    ruta.write_text(
        "from core.contracts import Dominio\nfrom core.verification import texto\n"
        "from core.budget import cadena\n\n\ndef f():\n    from core.budget import elaborar\n",
        encoding="utf-8",
    )
    assert _nucleo_profundo(ruta, raiz=tmp_path) == {"core.budget.cadena": 3, "core.budget": 7}


# --- Tarea 1.3: cero ciclos nuevos --------------------------------------------------------------
#
# Los grafos de 1.3 miran el programa: `tests` y `scripts` quedan fuera porque importan todo por
# oficio (con ellos, todo el programa seria un solo ciclo). Sus aristas hacia el programa las
# congela la matriz de 1.1, que tambien ve `operacion -> scripts` e `instalador -> tests`.

PAQUETES_DEL_PROGRAMA = PAQUETES_INTERNOS - {"tests", "scripts"}


def _componentes_fuertes(grafo: dict[str, set[str]]) -> list[frozenset[str]]:
    """Componentes fuertemente conexos de dos o mas nodos (Tarjan, iterativo: sin recursion)."""
    indice: dict[str, int] = {}
    enlace: dict[str, int] = {}
    pila: list[str] = []
    en_pila: set[str] = set()
    componentes: list[frozenset[str]] = []
    nodos = sorted(set(grafo) | {v for vecinos in grafo.values() for v in vecinos})
    for raiz in nodos:
        if raiz in indice:
            continue
        trabajo = [(raiz, iter(sorted(grafo.get(raiz, ()))))]
        indice[raiz] = enlace[raiz] = len(indice)
        pila.append(raiz)
        en_pila.add(raiz)
        while trabajo:
            nodo, vecinos = trabajo[-1]
            vecino = next(vecinos, None)
            if vecino is None:
                trabajo.pop()
                if trabajo:
                    padre = trabajo[-1][0]
                    enlace[padre] = min(enlace[padre], enlace[nodo])
                if enlace[nodo] == indice[nodo]:
                    componente = set()
                    while True:
                        miembro = pila.pop()
                        en_pila.discard(miembro)
                        componente.add(miembro)
                        if miembro == nodo:
                            break
                    if len(componente) > 1:
                        componentes.append(frozenset(componente))
            elif vecino not in indice:
                indice[vecino] = enlace[vecino] = len(indice)
                pila.append(vecino)
                en_pila.add(vecino)
                trabajo.append((vecino, iter(sorted(grafo.get(vecino, ())))))
            elif vecino in en_pila:
                enlace[nodo] = min(enlace[nodo], indice[vecino])
    return sorted(componentes, key=sorted)


def _aristas_de_modulos(paquetes: frozenset[str], raiz: Path = RAIZ) -> dict[tuple[str, str], str]:
    """`(modulo, modulo importado)` -> primer `archivo:linea`, entre modulos de `paquetes`.

    Imports de ejecucion (locales incluidos, sin `if TYPE_CHECKING:`); `from a import b` apunta a
    `a.b` si es un submodulo y a `a` (su `__init__`) si no lo es."""
    archivos = [a for paquete in sorted(paquetes) for a in sorted((raiz / paquete).rglob("*.py"))]
    modulos = {}
    for archivo in archivos:
        partes = archivo.relative_to(raiz).with_suffix("").parts
        modulos[archivo] = ".".join(partes[:-1] if partes[-1] == "__init__" else partes)
    conocidos = set(modulos.values())
    aristas: dict[tuple[str, str], str] = {}
    for archivo, origen in modulos.items():
        for linea, destino in _modulos_usados(archivo, raiz):
            if destino in conocidos and destino != origen:
                sitio = f"{archivo.relative_to(raiz).as_posix()}:{linea}"
                aristas.setdefault((origen, destino), sitio)
    return aristas


def _grafo(aristas) -> dict[str, set[str]]:
    grafo: dict[str, set[str]] = {}
    for origen, destino in aristas:
        grafo.setdefault(origen, set()).add(destino)
    return grafo


def _describir_componente(componente: frozenset[str], aristas: dict) -> str:
    internas = sorted(
        f"{origen} -> {destino} ({sitio})"
        for (origen, destino), sitio in aristas.items()
        if origen in componente and destino in componente
    )
    return f"{sorted(componente)}:\n    " + "\n    ".join(internas)


#: Ciclos de importacion entre modulos del programa (2026-11-17, a802d728): componente -> motivo.
#: Salir de ellos es la ola 5 (aval del tutor). Sin los imports locales no hay ninguno: todos
#: estan esquivados dentro de funciones.
CICLOS_CONOCIDOS: dict[frozenset[str], str] = {
    frozenset(
        {
            "aplicacion.aprobaciones",
            "aplicacion.control",
            "aplicacion.entrega",
            "aplicacion.frentes",
            "aplicacion.hoja",
            "aplicacion.hoja_partidas",
            "aplicacion.mercado",
            "aplicacion.mesa",
            "aplicacion.precios_declarados",
            "aplicacion.procura",
            "aplicacion.vial",
        }
    ): "2026-11-17, la mesa reune los pendientes de todos y ellos le piden sus tipos (tarea 5.1)",
    frozenset({"seguridad.cuentas", "seguridad.sesiones"}): (
        "2026-11-17, sesiones toma texto_responsable de cuentas dentro de una funcion (tarea 5.2)"
    ),
}

#: El unico ciclo entre paquetes del programa (2026-11-17, a802d728); lo rompen las seis aristas
#: marcadas `# ciclo, ola 5` en `DEPENDENCIAS_PERMITIDAS`.
CICLO_DE_PAQUETES_CONOCIDO: frozenset[str] = frozenset(
    {
        "aplicacion",
        "asistente",
        "auditoria",
        "fusion",
        "migraciones",
        "operacion",
        "paquete",
        "seguridad",
    }
)


def _ciclos_de_modulos():
    aristas = _aristas_de_modulos(PAQUETES_DEL_PROGRAMA)
    return _componentes_fuertes(_grafo(aristas)), aristas


def test_el_detector_de_componentes_ve_dos_ciclos_separados():
    grafo = {"a": {"b"}, "b": {"a", "c"}, "c": {"d"}, "d": {"c"}, "e": {"a"}}
    assert _componentes_fuertes(grafo) == [frozenset({"a", "b"}), frozenset({"c", "d"})]
    assert _componentes_fuertes({"a": {"b"}, "b": {"c"}, "c": set()}) == []
    assert _componentes_fuertes({"a": {"b"}, "b": {"c"}, "c": {"a"}}) == [frozenset("abc")]


def test_el_grafo_de_modulos_ve_un_ciclo_por_import_local(tmp_path):
    """El rojo de verdad: dos modulos falsos que se importan, uno de ellos dentro de una funcion,
    forman un ciclo; el import bajo `if TYPE_CHECKING:` no cierra otro."""
    carpeta = tmp_path / "falso"
    carpeta.mkdir()
    (carpeta / "__init__.py").write_text("", encoding="utf-8")
    (carpeta / "a.py").write_text("from falso import b\n", encoding="utf-8")
    (carpeta / "b.py").write_text("def f():\n    from falso.a import g\n", encoding="utf-8")
    (carpeta / "c.py").write_text(
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from falso import a\n",
        encoding="utf-8",
    )
    (carpeta / "d.py").write_text("from falso import c\n", encoding="utf-8")
    aristas = _aristas_de_modulos(frozenset({"falso"}), raiz=tmp_path)
    assert aristas[("falso.b", "falso.a")] == "falso/b.py:2"
    assert _componentes_fuertes(_grafo(aristas)) == [frozenset({"falso.a", "falso.b"})]


def test_no_aparecen_ciclos_nuevos():
    componentes, aristas = _ciclos_de_modulos()
    nuevos = [
        _describir_componente(c, aristas)
        for c in componentes
        if not any(c & conocido for conocido in CICLOS_CONOCIDOS)
    ]
    assert nuevos == [], "ciclos de importacion nuevos:\n" + "\n".join(nuevos)


def test_un_ciclo_conocido_no_crece():
    componentes, aristas = _ciclos_de_modulos()
    crecidos = [
        f"{_describir_componente(c, aristas)}\n  nuevos: {sorted(c - conocido)}"
        for c in componentes
        for conocido in CICLOS_CONOCIDOS
        if c & conocido and not c <= conocido
    ]
    assert crecidos == [], "ciclos conocidos que crecieron:\n" + "\n".join(crecidos)


def test_ciclos_conocidos_sin_sobrantes():
    """Un ciclo conocido que se achico o desaparecio obliga a actualizar o borrar su fila."""
    componentes, _ = _ciclos_de_modulos()
    sobrantes = [sorted(c) for c in CICLOS_CONOCIDOS if c not in componentes]
    assert sobrantes == [], f"actualizar o borrar de CICLOS_CONOCIDOS: {sobrantes}; hoy: " + str(
        [sorted(c) for c in componentes]
    )


def _ciclos_de_paquetes():
    grafo = {
        paquete: set(_imports_de_ejecucion_de_paquete(paquete)) & PAQUETES_DEL_PROGRAMA
        for paquete in PAQUETES_DEL_PROGRAMA
    }
    return _componentes_fuertes(grafo)


def test_no_aparecen_ciclos_nuevos_de_paquetes():
    """Ni un segundo ciclo entre paquetes ni un paquete mas en el conocido."""
    fuera = [
        f"{sorted(c)} (nuevos: {sorted(c - CICLO_DE_PAQUETES_CONOCIDO)})"
        for c in _ciclos_de_paquetes()
        if not c <= CICLO_DE_PAQUETES_CONOCIDO
    ]
    assert fuera == [], f"ciclos de paquetes fuera de CICLO_DE_PAQUETES_CONOCIDO: {fuera}"


def test_ciclo_de_paquetes_sin_sobrantes():
    hoy = _ciclos_de_paquetes()
    esperado = [CICLO_DE_PAQUETES_CONOCIDO] if CICLO_DE_PAQUETES_CONOCIDO else []
    assert hoy == esperado, f"actualizar CICLO_DE_PAQUETES_CONOCIDO a {[sorted(c) for c in hoy]}"


# --- Tarea 1.4: una sola presentacion numerica en la API ----------------------------------------

#: Donde vivira la presentacion unica de la API (tarea 2.2); aun no existe, se excluye por nombre.
PRESENTACION_DE_LA_API = "api/presentacion.py"


def _menciona(anotacion: ast.expr | None, nombre: str) -> bool:
    return anotacion is not None and any(
        (isinstance(n, ast.Name) and n.id == nombre)
        or (isinstance(n, ast.Attribute) and n.attr == nombre)
        for n in ast.walk(anotacion)
    )


def _es_presentadora(funcion: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Funcion privada con un parametro anotado `Decimal` que devuelve `str`."""
    argumentos = funcion.args
    parametros = [*argumentos.posonlyargs, *argumentos.args, *argumentos.kwonlyargs]
    return (
        funcion.name.startswith("_")
        and any(_menciona(p.annotation, "Decimal") for p in parametros)
        and _menciona(funcion.returns, "str")
    )


def _es_sitio_de_presentacion(nodo: ast.AST) -> bool:
    if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
        return _es_presentadora(nodo)
    if isinstance(nodo, ast.Call):
        if isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "quantize":
            return True
        return (
            isinstance(nodo.func, ast.Name)
            and nodo.func.id == "format"
            and len(nodo.args) == 2
            and isinstance(nodo.args[1], ast.Constant)
            and isinstance(nodo.args[1].value, str)
            and nodo.args[1].value.endswith("f")
        )
    nombre = (
        nodo.id
        if isinstance(nodo, ast.Name)
        else nodo.attr
        if isinstance(nodo, ast.Attribute)
        else ""
    )
    return nombre.startswith("ROUND_HALF_")


def _sitios_de_presentacion(archivo: Path) -> list[int]:
    """Lineas donde `archivo` presenta una cifra por su cuenta: `.quantize(`, un `ROUND_HALF_*`,
    `format(x, "f")` (o `".2f"`) o una funcion privada `Decimal -> str`. Lo que va dentro de un
    sitio no cuenta otra vez: `_x(v: Decimal) -> str: return format(v, "f")` es un sitio, y
    `v.quantize(q, rounding=ROUND_HALF_UP)` tambien. `texto_de_cifra` no es un sitio."""
    dentro: set[int] = set()
    sitios: list[int] = []
    for nodo in ast.walk(_arbol(archivo)):
        if id(nodo) in dentro or not _es_sitio_de_presentacion(nodo):
            continue
        sitios.append(nodo.lineno)
        dentro.update(id(hijo) for hijo in ast.walk(nodo))
    return sorted(sitios)


def _presentacion_suelta_en_api() -> dict[str, list[int]]:
    return {
        _ruta(archivo): sitios
        for archivo in _archivos("api")
        if _ruta(archivo) != PRESENTACION_DE_LA_API and (sitios := _sitios_de_presentacion(archivo))
    }


#: Archivo de `api/` -> sitios que presentan cifras por su cuenta (2026-11-17, a802d728). La ola 2
#: los lleva a `api/presentacion.py`.
PRESENTACION_SUELTA_EN_API: dict[str, int] = {
    "api/esquemas_corte.py": 3,
    "api/esquemas_hoja.py": 1,
    "api/esquemas_informe.py": 1,
    "api/esquemas_vial.py": 4,
    "api/rutas/admin_asistente.py": 1,
    "api/rutas/aprobaciones.py": 1,
    "api/rutas/auditorias.py": 2,
    "api/rutas/auditorias_libro.py": 1,
    "api/rutas/computos.py": 2,
    "api/rutas/consulta.py": 1,
    "api/rutas/control.py": 1,
    "api/rutas/entregas.py": 1,
    "api/rutas/fcas.py": 1,
    "api/rutas/hoja_libro.py": 1,
    "api/rutas/indices.py": 1,
    "api/rutas/libros.py": 7,
    "api/rutas/mercado.py": 4,
    "api/rutas/obras.py": 5,
    "api/rutas/procura.py": 1,
    "api/rutas/produccion.py": 5,
    "api/rutas/produccion_planta.py": 5,
    "api/rutas/rendimientos.py": 1,
    "api/rutas/revision.py": 1,
    "api/rutas/riesgo.py": 2,
    "api/rutas/tablero.py": 2,
}


def test_la_api_presenta_cifras_en_un_solo_sitio():
    peores = sorted(
        f"{ruta}: {len(sitios)} sitios (congelado {PRESENTACION_SUELTA_EN_API.get(ruta, 0)}): "
        + ", ".join(f"{ruta}:{linea}" for linea in sitios)
        for ruta, sitios in _presentacion_suelta_en_api().items()
        if len(sitios) > PRESENTACION_SUELTA_EN_API.get(ruta, 0)
    )
    assert peores == [], f"la cifra se presenta en {PRESENTACION_DE_LA_API}:\n" + "\n".join(peores)


def test_la_api_presenta_cifras_en_un_solo_sitio_sin_sobrantes():
    hoy = _presentacion_suelta_en_api()
    sobrantes = sorted(
        f"{ruta}: {congelado} -> {len(hoy.get(ruta, []))}"
        for ruta, congelado in PRESENTACION_SUELTA_EN_API.items()
        if len(hoy.get(ruta, [])) < congelado
    )
    assert sobrantes == [], "bajar o borrar en PRESENTACION_SUELTA_EN_API: " + "; ".join(sobrantes)


def test_la_api_presenta_cifras_en_un_solo_sitio_ve_la_falta(tmp_path):
    fuentes = {
        'def _x(v: Decimal) -> str:\n    return format(v, "f")\n': [1],
        "def _y(v: Decimal) -> str:\n    return str(v.quantize(Decimal('0.01')))\n": [1],
        "t = v.quantize(Q, rounding=ROUND_HALF_UP)\n": [1],
        "import decimal\nmodo = decimal.ROUND_HALF_EVEN\n": [2],
        'a = format(v, "f")\nb = format(v, ".2f")\nc = format(n, "d")\n': [1, 2],
        "def publica(v: Decimal) -> str:\n    return texto_de_cifra(v)\n": [],
        "def _z(v: int) -> str:\n    return str(v)\n": [],
    }
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"modulo_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = _sitios_de_presentacion(archivo)
    assert detectadas == fuentes


# --- Tarea 1.5: tope de tamano por modulo -------------------------------------------------------

TOPE_DE_LINEAS = 1000


def _lineas_de_produccion(raiz: Path = RAIZ) -> dict[str, int]:
    """Lineas de cada `.py` de produccion: los paquetes fuera de `core/` y de `tests/`, y los
    sueltos de la raiz (`start.py`)."""
    archivos = [*raiz.glob("*.py")] + [
        archivo
        for paquete in sorted(set(PAQUETES_FUERA_DEL_NUCLEO) - {"tests"})
        for archivo in (raiz / paquete).rglob("*.py")
    ]
    return {
        archivo.relative_to(raiz).as_posix(): len(archivo.read_text(encoding="utf-8").splitlines())
        for archivo in sorted(archivos)
    }


#: Modulos que ya pasan del tope (2026-11-17, a802d728) -> sus lineas ese dia. Ninguno crece; la
#: ola 4 los parte dejando una fachada que reexporta.
MODULOS_GRANDES: dict[str, int] = {
    "aplicacion/hoja.py": 3195,
    "scripts/recorrido_ux_playwright.py": 2321,
    "scripts/fusion_verificar.py": 2124,
    "adapters/hoja_empresa/reglas.py": 1707,
    "aplicacion/control.py": 1584,
    "aplicacion/composicion.py": 1471,
    "adapters/hoja_empresa/pdf.py": 1389,
    "api/rutas/hoja.py": 1348,
    "adapters/hoja_empresa/escritor/calculos.py": 1317,
    "scripts/probar_precios_maprex.py": 1222,
    "scripts/anonimizar_libro.py": 1163,
    "api/rutas/presupuestos.py": 1132,
    "scripts/informe_ti001.py": 1102,
    "api/esquemas_hoja.py": 1061,
    "aplicacion/hoja_vista.py": 1055,
    "api/rutas/libros.py": 1038,
}


def test_ningun_modulo_pasa_del_tope():
    nuevos = sorted(
        f"{ruta} ({lineas} lineas)"
        for ruta, lineas in _lineas_de_produccion().items()
        if lineas > TOPE_DE_LINEAS and ruta not in MODULOS_GRANDES
    )
    assert nuevos == [], f"modulos de mas de {TOPE_DE_LINEAS} lineas: {nuevos}"


def test_un_modulo_grande_no_crece_sobre_su_tope():
    hoy = _lineas_de_produccion()
    crecidos = sorted(
        f"{ruta}: {congelado} -> {hoy[ruta]}"
        for ruta, congelado in MODULOS_GRANDES.items()
        if hoy.get(ruta, 0) > congelado
    )
    assert crecidos == [], f"modulos grandes que crecieron: {crecidos}"


def test_modulos_grandes_sin_sobrantes_bajo_el_tope():
    """Si un modulo baja del tope se borra su fila; si baja de su valor, el valor se baja al
    numero nuevo que muestra el mensaje."""
    hoy = _lineas_de_produccion()
    sobrantes = []
    for ruta, congelado in sorted(MODULOS_GRANDES.items()):
        lineas = hoy.get(ruta, 0)
        if lineas <= TOPE_DE_LINEAS:
            sobrantes.append(f"{ruta}: {lineas} lineas, ya cabe en el tope (borrar la fila)")
        elif lineas < congelado:
            sobrantes.append(f'"{ruta}": {lineas},  (era {congelado})')
    assert sobrantes == [], "actualizar MODULOS_GRANDES:\n" + "\n".join(sobrantes)


def test_el_tope_ve_la_falta(tmp_path):
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "grande.py").write_text("x = 1\n" * (TOPE_DE_LINEAS + 1), encoding="utf-8")
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "nucleo.py").write_text("x = 1\n" * 5000, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("x = 1\n" * 5000, encoding="utf-8")
    (tmp_path / "start.py").write_text("x = 1\n", encoding="utf-8")
    assert _lineas_de_produccion(tmp_path) == {"api/grande.py": TOPE_DE_LINEAS + 1, "start.py": 1}


# --- Tarea 1.6: toda tabla esta en el modelo de datos -------------------------------------------


def _tablas_del_programa() -> set[str]:
    """Las tablas de las dos bases (`migraciones/metadatos.py`); se importa aqui para no cargar
    todos los modelos al recoger las pruebas de este archivo."""
    from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION

    return {nombre for meta in (*METADATAS_CASO, *METADATAS_INSTALACION) for nombre in meta.tables}


def _tablas_sin_documentar(tablas: set[str], texto: str) -> set[str]:
    """Las tablas cuyo nombre no aparece, exacto y entre comillas invertidas, en `texto`."""
    return {tabla for tabla in tablas if f"`{tabla}`" not in texto}


def _texto_del_modelo_de_datos() -> str:
    return (RAIZ / "docs" / "modelo_datos.md").read_text(encoding="utf-8")


#: Tablas que `docs/modelo_datos.md` no nombra (2026-11-17, a802d728). Cada fila se borra cuando
#: su tabla entra en el documento (trabajo de documentacion aparte).
TABLAS_SIN_DOCUMENTAR: frozenset[str] = frozenset(
    """
    apu_desperdicio apu_desperdicio_guardado cambio_precio clave_api clave_empresa
    codigo_instalacion composicion_apu descarte_version ejecucion empresa_propia
    empresa_registrada eslabon_version esp_sobrescrituras evento_acceso ficha_obra hallazgo
    hoja_importaciones incidencia_cambio insumo intento_acceso item_computo lista_precios
    modulo_cambio mp_aprobacion_evento mp_carpeta mp_causa_retraso mp_compra mp_eleccion
    mp_indice_aprobacion mp_nota_medicion mp_observacion mp_plazo_entrega mp_precio_corte
    mp_precio_objetivo paq_dictamen paq_recibido partida partida_presupuestada presupuesto
    prod_calculo prod_costo prod_publicacion prod_receta prod_receta_componente punto_curva
    sesion vial_tramo vial_tramos_guardado
    """.split()
)


def test_toda_tabla_esta_en_el_modelo_de_datos():
    faltan = _tablas_sin_documentar(_tablas_del_programa(), _texto_del_modelo_de_datos())
    nuevas = sorted(faltan - TABLAS_SIN_DOCUMENTAR)
    assert nuevas == [], f"tablas que docs/modelo_datos.md no nombra entre `comillas`: {nuevas}"


def test_toda_tabla_esta_en_el_modelo_de_datos_sin_sobrantes():
    """Una tabla que ya esta documentada, o que ya no existe, se borra de la lista."""
    faltan = _tablas_sin_documentar(_tablas_del_programa(), _texto_del_modelo_de_datos())
    sobrantes = sorted(TABLAS_SIN_DOCUMENTAR - faltan)
    assert sobrantes == [], f"borrar de TABLAS_SIN_DOCUMENTAR: {sobrantes}"


def test_el_modelo_de_datos_ve_la_falta():
    texto = "La tabla `partida` guarda ...; `presupuesto_version` no es `presupuesto`.\n"
    tablas = {"partida", "presupuesto", "insumo", "clave_api"}
    assert _tablas_sin_documentar(tablas, texto) == {"insumo", "clave_api"}
    assert _tablas_sin_documentar({"precio"}, "`precio_unitario` y precio a secas") == {"precio"}


# --- Tarea 1.7: todo RF del ERS esta en el plan de pruebas --------------------------------------

#: `RF-N` con el guion normal o con el de no separacion (U+2011), que es el que usa el ERS.
_RF = re.compile("(?<![A-Za-z0-9])RF[-‑]([0-9]+)")


def _requisitos(texto: str) -> set[str]:
    """Los `RF-N` que nombra `texto`, normalizados con el guion normal."""
    return {f"RF-{numero}" for numero in _RF.findall(texto)}


def _seccion_de_trazabilidad(plan: str) -> str:
    """De `docs/plan_pruebas.md`, lo que va de `## 8.` (RF -> prueba) a `## 9.`."""
    inicio = plan.index("\n## 8.")
    return plan[inicio : plan.index("\n## 9.", inicio)]


def _rf_sin_prueba() -> set[str]:
    ers = (RAIZ / "docs" / "ERS.md").read_text(encoding="utf-8")
    plan = (RAIZ / "docs" / "plan_pruebas.md").read_text(encoding="utf-8")
    return _requisitos(ers) - _requisitos(_seccion_de_trazabilidad(plan))


def _rangos_de_rf(*rangos: tuple[int, int]) -> frozenset[str]:
    return frozenset(f"RF-{n}" for desde, hasta in rangos for n in range(desde, hasta + 1))


#: RF del ERS sin fila en `docs/plan_pruebas.md` §8 (2026-11-17, a802d728): 80 de 191. Rangos
#: cerrados en los dos extremos.
RF_SIN_PRUEBA: frozenset[str] = _rangos_de_rf(
    (80, 89),
    (101, 110),
    (119, 119),
    (126, 126),
    (128, 128),
    (131, 132),
    (137, 137),
    (140, 140),
    (147, 147),
    (155, 156),
    (159, 161),
    (166, 168),
    (170, 202),
    (204, 214),
)


def test_todo_rf_tiene_fila_en_el_plan_de_pruebas():
    nuevos = sorted(_rf_sin_prueba() - RF_SIN_PRUEBA, key=lambda rf: int(rf[3:]))
    assert nuevos == [], f"RF del ERS sin fila en docs/plan_pruebas.md §8: {nuevos}"


def test_todo_rf_tiene_fila_en_el_plan_de_pruebas_sin_sobrantes():
    """Un RF que ya tiene su fila en §8, o que salio del ERS, se borra de la lista."""
    sobrantes = sorted(RF_SIN_PRUEBA - _rf_sin_prueba(), key=lambda rf: int(rf[3:]))
    assert sobrantes == [], f"borrar de RF_SIN_PRUEBA: {sobrantes}"


def test_la_trazabilidad_del_plan_de_pruebas_lee_los_dos_guiones():
    texto = "RF‑7 y RF-8 se piden; NRF-9 y RF10 no son requisitos; RF-12 vale.\n"
    assert _requisitos(texto) == {"RF-7", "RF-8", "RF-12"}
    plan = "## 7. Otra\nRF-1\n## 8. Trazabilidad\n| RF‑2 |\n## 9. RNF\nRF-3\n"
    assert _requisitos(_seccion_de_trazabilidad(plan)) == {"RF-2"}


# --- Tarea 2.1: un solo `decimal_desde_texto` ---------------------------------------------------


def _definiciones(nombre: str, raiz: Path = RAIZ) -> list[str]:
    """`archivo:linea` de cada `def nombre` de produccion (fuera de `core/` y de `tests/`)."""
    return sorted(
        f"{ruta}:{nodo.lineno}"
        for ruta in _lineas_de_produccion(raiz)
        for nodo in ast.walk(_arbol(raiz / ruta))
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef) and nodo.name == nombre
    )


def test_una_sola_lectura_de_decimal_de_maquina():
    definiciones = _definiciones("decimal_desde_texto")
    assert len(definiciones) == 1, f"una sola lectura en aplicacion/composicion.py: {definiciones}"
    assert definiciones[0].startswith("aplicacion/composicion.py:")
