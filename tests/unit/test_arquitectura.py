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


def _es_una_clase(nodo: ast.expr) -> bool:
    """`Usuario` o `models.Proyecto`: un nombre en CamelCase. `VARIABLE_BASE` (una constante en
    mayusculas) no lo es."""
    nombre = (
        nodo.id
        if isinstance(nodo, ast.Name)
        else nodo.attr
        if isinstance(nodo, ast.Attribute)
        else ""
    )
    return nombre[:1].isupper() and any(letra.islower() for letra in nombre)


def _es_consulta(nodo: ast.Call) -> bool:
    funcion = nodo.func
    if isinstance(funcion, ast.Name):
        return funcion.id == "select"
    if not isinstance(funcion, ast.Attribute):
        return False
    if funcion.attr in {"select", "query", "execute"}:
        return True
    if funcion.attr != "get":
        return False
    nombrados = {k.arg: k.value for k in nodo.keywords if k.arg is not None}
    entidad = nodo.args[0] if nodo.args else nombrados.get("entity")
    tiene_ident = len(nodo.args) >= 2 or "ident" in nombrados
    return entidad is not None and tiene_ident and _es_una_clase(entidad)


def _llamadas_select(archivo: Path) -> list[int]:
    """Lineas de cada consulta a la base, por AST (un comentario no cuenta): `select(...)` o
    `x.select(...)`, `x.query(...)`, `x.execute(...)` y `x.get(<Modelo>, id)` (anexo A.7), tambien
    con `ident=` y `entity=` nombrados (DS-50)."""
    return sorted(
        nodo.lineno
        for nodo in ast.walk(_arbol(archivo))
        if isinstance(nodo, ast.Call) and _es_consulta(nodo)
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
    queda fuera: lo vigila `test_las_rutas_no_importan_los_modelos_del_nucleo`."""
    hallados: dict[str, int] = {}
    for linea, modulo in _modulos_usados(archivo, raiz):
        es_modelo = modulo == "core.models" or modulo.startswith("core.models.")
        if modulo.startswith("core.") and not es_modelo and not _es_nucleo_de_superficie(modulo):
            hallados.setdefault(modulo, linea)
    return hallados


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
    # Tarea 4.2: lo que salio de hoja.py con sus rutas (subconjuntos de la fila de hoja.py).
    "api/rutas/hoja_cadena.py": frozenset({"core.catalog"}),
    "api/rutas/hoja_lecturas.py": frozenset({"core.budget.moneda", "core.catalog"}),
    "api/rutas/listas.py": frozenset({"core.catalog", "core.catalog.precios"}),
    "api/rutas/mercado.py": frozenset(
        {"core.catalog", "core.catalog.errores", "core.catalog.moneda"}
    ),
    "api/rutas/obras.py": frozenset({"core.catalog", "core.catalog.indices"}),
    # Tarea 4.1: la fila de siempre de presupuestos.py, repartida entre sus cuatro modulos.
    "api/rutas/presupuestos.py": frozenset(
        {"core.budget", "core.catalog", "core.verification.informe"}
    ),
    "api/rutas/presupuestos_ayudas.py": frozenset(
        {"core.budget", "core.budget.instantanea", "core.catalog", "core.verification.informe"}
    ),
    "api/rutas/presupuestos_calculo.py": frozenset({"core.verification.informe"}),
    "api/rutas/presupuestos_escenarios.py": frozenset(
        {"core.budget", "core.catalog", "core.verification.informe"}
    ),
    "api/rutas/proyectos.py": frozenset({"core.catalog"}),
    "api/rutas/reajuste.py": frozenset({"core.budget.reajuste"}),
    "api/rutas/rendimientos.py": frozenset({"core.catalog"}),
    "api/rutas/revision.py": frozenset({"core.budget.comparacion"}),
    "api/rutas/sesion.py": frozenset({"core.catalog"}),
    "api/rutas/tablero.py": frozenset({"core.catalog"}),
}


def test_las_rutas_no_consultan_la_base():
    """Prohibicion pura desde el cierre de la ola 3 (2026-11-17): la consulta va en `aplicacion/`,
    `seguridad/` o `produccion/`, nunca en `api/rutas`.

    No ve: `bd.refresh(x)`, `bd.scalars(...)`/`bd.scalar(...)` sobre una sentencia hecha en otro
    sitio ni `x.get(modelo, id)` con el modelo en una variable en minusculas (DS-50)."""
    sitios = sorted(
        f"{_ruta(archivo)}:{linea}"
        for archivo in _archivos_de_rutas()
        for linea in _llamadas_select(archivo)
    )
    assert sitios == [], "la consulta va en aplicacion/, no en la ruta:\n" + "\n".join(sitios)


def test_las_rutas_no_consultan_la_base_ve_la_falta(tmp_path):
    archivo = tmp_path / "ruta.py"
    archivo.write_text(
        "import sqlalchemy as sa\nfrom sqlalchemy import select\n\n"
        "# select(Partida) en un comentario no cuenta\n"
        'consulta = select(1).where(True)\notra = sa.select(2)\ntexto = "select(3)"\n',
        encoding="utf-8",
    )
    assert _llamadas_select(archivo) == [5, 6]


def test_las_rutas_no_consultan_la_base_ve_get_query_y_execute(tmp_path):
    """Anexo A.7: `sesion.get(<Modelo>, id)`, `.query(` y `.execute(` tambien son consultas. Un
    `dict.get("clave", x)` o un `os.environ.get(CONSTANTE, "")` no lo son."""
    fuentes = {
        "fila = sesion.get(Usuario, usuario_id)\n": [1],
        "fila = bd.get(models.Proyecto, 3)\n": [1],
        "filas = sesion.query(Usuario).all()\n": [1],
        "fila = sesion.get(Usuario, ident=usuario_id)\n": [1],
        "fila = sesion.get(entity=Usuario, ident=usuario_id)\n": [1],
        'valor = datos.get("clave", default=0)\n': [],
        'sesion.execute(text("DELETE FROM x"))\n': [1],
        'valor = datos.get("clave", 0)\n': [],
        'base = os.environ.get(VARIABLE_BASE, "")\n': [],
        "valor = cache.get(clave)\n": [],
    }
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"ruta_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = _llamadas_select(archivo)
    assert detectadas == fuentes


def test_las_rutas_no_importan_los_modelos_del_nucleo():
    """Prohibicion pura desde el cierre de la ola 3 (2026-11-17): una ruta recibe las filas de
    `aplicacion/`; el tipo de una firma, si hace falta, va bajo `if TYPE_CHECKING:`."""
    sitios = sorted(
        f"{_ruta(archivo)}:{lineas[0]}"
        for archivo in _archivos_de_rutas()
        if (lineas := _importa_modelos_del_nucleo(archivo))
    )
    assert sitios == [], f"una ruta no importa core.models: {sitios}"


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

#: La presentacion unica de la API (tarea 2.2): se excluye por nombre.
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


def _campos_decimales(arbol: ast.AST) -> tuple[set[str], set[str]]:
    """Nombres de campo de clase anotados con `Decimal` (`Decimal | None` incluido) y los
    anotados con otro numero (`int`, `float`). Los anotados `str` no cuentan como otra cosa: son
    los esquemas de respuesta, que llevan el mismo nombre con la cifra ya en texto."""
    decimales: set[str] = set()
    otros: set[str] = set()
    for clase in ast.walk(arbol):
        if not isinstance(clase, ast.ClassDef):
            continue
        for campo in clase.body:
            if isinstance(campo, ast.AnnAssign) and isinstance(campo.target, ast.Name):
                if _menciona(campo.annotation, "Decimal"):
                    decimales.add(campo.target.id)
                elif _menciona(campo.annotation, "int") or _menciona(campo.annotation, "float"):
                    otros.add(campo.target.id)
    return decimales, otros


@functools.cache
def _campos_decimales_del_programa() -> frozenset[str]:
    """Los campos de clase que en todo el programa (el nucleo incluido: la API lee sus contratos)
    son `Decimal` y en ninguna clase son otro numero: `c.total` no se lee como `Decimal` porque
    algun `total: int` lo vuelve ambiguo (limite conocido de la guardia: no ve tipos)."""
    decimales: set[str] = set()
    otros: set[str] = set()
    for paquete in sorted(PAQUETES_DEL_PROGRAMA):
        for archivo in _archivos(paquete):
            de_aqui, otros_de_aqui = _campos_decimales(_arbol(archivo))
            decimales |= de_aqui
            otros |= otros_de_aqui
    return frozenset(decimales - otros)


def _es_un_decimal(nodo: ast.expr, parametros: set[str], campos: frozenset[str]) -> bool:
    """`Decimal(...)`, un parametro anotado `Decimal` o `x.campo` con `campo` decimal."""
    if isinstance(nodo, ast.Call):
        return (isinstance(nodo.func, ast.Name) and nodo.func.id == "Decimal") or (
            isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "Decimal"
        )
    if isinstance(nodo, ast.Name):
        return nodo.id in parametros
    return isinstance(nodo, ast.Attribute) and nodo.attr in campos


def _str_de_un_decimal(arbol: ast.AST, campos: frozenset[str]) -> set[int]:
    """Los `id` de cada `str(<Decimal>)` del arbol y de cada valor de f-string `<Decimal>` sin
    formato (`f"{v}"`, `f"{v!s}"`, que son `str(v)`: DS-50) o con formato fijo (`f"{v:.2f}"`: un
    `float` con `.Nf` no cuenta, DS-52). Un parametro cuenta dentro de su funcion."""

    def operando(nodo: ast.AST) -> ast.expr | None:
        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id == "str"
            and len(nodo.args) == 1
            and not nodo.keywords
        ):
            return nodo.args[0]
        if isinstance(nodo, ast.FormattedValue):
            como_str = nodo.format_spec is None and nodo.conversion in {-1, ord("s")}
            if como_str or _es_formato_fijo(nodo):
                return nodo.value
        return None

    def es_str(nodo: ast.AST, parametros: set[str]) -> bool:
        valor = operando(nodo)
        return valor is not None and _es_un_decimal(valor, parametros, campos)

    hallados = {id(n) for n in ast.walk(arbol) if es_str(n, set())}
    for funcion in ast.walk(arbol):
        if not isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        argumentos = funcion.args
        parametros = {
            p.arg
            for p in (*argumentos.posonlyargs, *argumentos.args, *argumentos.kwonlyargs)
            if _menciona(p.annotation, "Decimal")
        }
        hallados.update(id(n) for n in ast.walk(funcion) if es_str(n, parametros))
    return hallados


def _es_formato_fijo(nodo: ast.AST) -> bool:
    """`{v:f}` o `{v:.2f}` dentro de un f-string (lo mismo que `format(v, "f")`)."""
    return (
        isinstance(nodo, ast.FormattedValue)
        and isinstance(nodo.format_spec, ast.JoinedStr)
        and bool(nodo.format_spec.values)
        and all(isinstance(v, ast.Constant) for v in nodo.format_spec.values)
        and "".join(str(v.value) for v in nodo.format_spec.values).endswith("f")
    )


def _sitios_de_presentacion(archivo: Path) -> list[int]:
    """Lineas donde `archivo` presenta una cifra por su cuenta: `.quantize(`, un `ROUND_HALF_*`,
    `format(x, "f")` (o `".2f"`), su forma de f-string `f"{x:f}"`, un `str(<Decimal>)` o una
    funcion privada `Decimal -> str`. Lo que va dentro de un sitio no cuenta otra vez:
    `_x(v: Decimal) -> str: return format(v, "f")` es un sitio, y
    `v.quantize(q, rounding=ROUND_HALF_UP)` tambien. `texto_de_cifra` no es un sitio."""
    arbol = _arbol(archivo)
    campos_del_archivo, _ = _campos_decimales(arbol)
    str_decimales = _str_de_un_decimal(
        arbol, _campos_decimales_del_programa() | frozenset(campos_del_archivo)
    )
    dentro: set[int] = set()
    sitios: list[int] = []
    for nodo in ast.walk(arbol):
        if id(nodo) in dentro:
            continue
        es_sitio = _es_sitio_de_presentacion(nodo) or id(nodo) in str_decimales
        if not es_sitio:
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
    "api/rutas/admin_asistente.py": 1,
    "api/rutas/auditorias.py": 2,
    "api/rutas/computos.py": 2,
    "api/rutas/consulta.py": 1,
    # 1 de 2026-11-17 y 1 de 2026-11-18 (DS-50): `f"{c.monto}"` en `costos_sin_tasa` (:671).
    "api/rutas/control.py": 2,
    "api/rutas/mercado.py": 1,
    "api/rutas/procura.py": 1,
    "api/rutas/produccion_planta.py": 5,
    # Anexo A.7 (2026-11-18, DS-42): lo que la guardia ve desde que cuenta `f"{x:.Nf}"` y
    # `str(<Decimal>)`. Los `f"{x:f}"` pasaron a `presentacion.exacto` (mismo texto); estos no:
    # `str` escribe `1E+2` donde `exacto` escribe `100`, y `.2f` redondea al par donde
    # `redondeado` lo hace al alza, asi que moverlos cambia la salida. Desde DS-52 (2026-11-18) el
    # `.Nf` solo cuenta sobre un `Decimal`: salieron `composicion.py:487` e `indices.py:175`
    # (floats: un puntaje y un tamano en MB). Desde DS-52 (2026-11-19) los `str(<Decimal>)` de
    # `api/rutas/` pasan por `presentacion.exacto` (el mismo texto sin notacion cientifica;
    # `tests/unit/test_api_sin_notacion_cientifica.py`); queda la alicuota del IVA, una constante.
    "api/esquemas.py": 1,
    # El de 2026-11-17 (`_advertencia`); los dos de A.7 salieron con DS-52.
    "api/rutas/rendimientos.py": 1,
}


def test_la_api_presenta_cifras_en_un_solo_sitio():
    """Ningun archivo de `api/` (fuera de `api/presentacion.py`) suma sitios que presenten cifras.

    No ve: `"{}".format(v)` ni `"%s" % v`; un `Decimal` en una variable local
    (`v = Decimal(a)`; `str(v)`); `str(x.total)`, `str(x.cantidad)` o `str(x.dias)`, cuyos campos
    son `int` en alguna clase y la guardia no ve tipos (DS-43, DS-50)."""
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


def test_la_presentacion_ve_los_f_strings_y_el_str_de_un_decimal(tmp_path):
    """Anexo A.7: `f"{v:f}"` es `format(v, "f")`, y `str(<Decimal>)` presenta la cifra a su manera
    (con notacion cientifica: `str(Decimal("1E+2")) == "1E+2"`). Un `Decimal` se reconoce por su
    anotacion: un parametro, o un campo de clase (del archivo o del programa)."""
    fuentes = {
        'def f(v: Decimal) -> str:\n    return f"{v:f}"\n': [2],
        'def f(v: Decimal) -> str:\n    return f"total {v:.2f} Bs"\n': [2],
        't = f"{n:d} {texto}"\n': [],
        "def f(v: Decimal) -> dict:\n    return {'x': str(v)}\n": [2],
        "def f(v: Decimal | None) -> dict:\n    return {'x': None if v is None else str(v)}\n": [2],
        "t = str(Decimal('1.5'))\n": [1],
        "class C:\n    cuenta_rara_de_prueba: Decimal\n\n\ndef f(c):\n"
        "    return str(c.cuenta_rara_de_prueba)\n": [6],
        "def f(e: ValueError) -> str:\n    return str(e)\n": [],
        "def f(c):\n    return str(c.nombre_raro_de_prueba)\n": [],
    }
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"modulo_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = _sitios_de_presentacion(archivo)
    assert detectadas == fuentes


def test_la_presentacion_ve_el_f_string_sin_formato_de_un_decimal(tmp_path):
    """DS-50 (3): `f"{v}"` y `f"{v!s}"` son `str(v)` cuando `v` es un `Decimal` (escriben `1E+2`
    donde `exacto` escribe `100`); un `int` o un texto no cuentan."""
    fuentes = {
        'def f(v: Decimal) -> str:\n    return f"{v}"\n': [2],
        'def f(v: Decimal) -> str:\n    return f"total {v!s} Bs"\n': [2],
        "t = f\"{Decimal('1.5')}\"\n": [1],
        "class C:\n    cuenta_rara_de_prueba: Decimal\n\n\ndef f(c):\n"
        '    return f"{c.cuenta_rara_de_prueba} Bs"\n': [6],
        'def f(v: int) -> str:\n    return f"{v}"\n': [],
        'def f(e: ValueError) -> str:\n    return f"{e}"\n': [],
    }
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"modulo_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = _sitios_de_presentacion(archivo)
    assert detectadas == fuentes


def test_la_presentacion_no_cuenta_el_formato_fijo_de_un_float(tmp_path):
    """DS-52: `f"{x:.Nf}"` presenta la cifra por su cuenta solo si `x` es un `Decimal` (por la
    misma regla que `str(<Decimal>)`); un tamano en MB o un puntaje `float` no son cifras de la
    obra."""
    fuentes = {
        't = f"pesa {tamano / 2**20:.1f} MB"\n': [],
        'def f(p: float) -> str:\n    return f"{p:.2f}"\n': [],
        'def f(s):\n    return f"{s.puntaje_raro_de_prueba:.2f}"\n': [],
        'def f(v: Decimal) -> str:\n    return f"{v:.2f}"\n': [2],
        "t = f\"{Decimal('1.5'):.1f}\"\n": [1],
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
    # 2026-11-27: la capa del marco pasó a recorrido_marco.py.
    "scripts/recorrido_ux_playwright.py": 2185,
    "scripts/fusion_verificar.py": 2124,
    "adapters/hoja_empresa/reglas.py": 1145,
    "aplicacion/composicion.py": 1471,
    "adapters/hoja_empresa/pdf.py": 1389,
    "adapters/hoja_empresa/escritor/calculos.py": 1317,
    "scripts/probar_precios_maprex.py": 1222,
    "scripts/anonimizar_libro.py": 1163,
    "scripts/informe_ti001.py": 1102,
    "api/esquemas_hoja.py": 1042,
    "aplicacion/hoja_vista.py": 1033,
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


# --- Ola 4: partir un modulo grande sin perder nombres ------------------------------------------
#
# Mover sin cambiar conducta: el modulo partido sigue ofreciendo, y lista en `__all__`, los nombres
# publicos que definia antes de partirse. Cada lista se midio ANTES de mover (dd468057) con las
# definiciones de primer nivel que no empiezan por `_` (funciones, clases y asignaciones).


def _definidos(archivo: Path) -> set[str]:
    """Los nombres publicos que `archivo` define en su primer nivel, leidos del AST: un import no
    cuenta (es de otro modulo)."""
    nombres: set[str] = set()
    for nodo in _arbol(archivo).body:
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            nombres.add(nodo.name)
        elif isinstance(nodo, ast.Assign):
            nombres.update(t.id for t in nodo.targets if isinstance(t, ast.Name))
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            nombres.add(nodo.target.id)
    return {nombre for nombre in nombres if not nombre.startswith("_")}


def test_definidos_ve_funciones_clases_y_asignaciones_y_no_imports(tmp_path):
    archivo = tmp_path / "modulo.py"
    archivo.write_text(
        "from x import importado\nA = 1\nB: int = 2\n_C = 3\n\n\nclass D: ...\n\n\n"
        "def e(): ...\n\n\nasync def f(): ...\n\n\ndef _g(): ...\n",
        encoding="utf-8",
    )
    assert _definidos(archivo) == {"A", "B", "D", "e", "f"}


#: Tarea 4.1: lo que `api/rutas/presupuestos.py` definia antes de partirse en `presupuestos`,
#: `presupuestos_calculo`, `presupuestos_escenarios` y `presupuestos_ayudas`.
PUBLICOS_DE_RUTAS_PRESUPUESTOS = frozenset(
    {
        "MAX_PENDIENTES_CON_PROPUESTAS",
        "actualizar_presupuesto",
        "base_de_escenarios",
        "calcular_presupuesto",
        "calcular_presupuesto_excel",
        "crear_presupuesto",
        "crear_proyecto_de_presupuestos",
        "declarar_rendimiento_propuesto",
        "descartar_version_revalorada",
        "escenarios_de_presupuesto",
        "escenarios_en_csv",
        "exportar_presupuesto_excel",
        "importar_presupuesto_de_tercero",
        "informe_de_auditoria",
        "listar_presupuestos",
        "obtener_presupuesto",
        "revalorar_presupuesto",
        "router",
    }
)


def test_rutas_presupuestos_reexporta_lo_mismo():
    from api.rutas import presupuestos

    assert sorted(getattr(presupuestos, "__all__", ())) == sorted(PUBLICOS_DE_RUTAS_PRESUPUESTOS)
    assert [n for n in sorted(PUBLICOS_DE_RUTAS_PRESUPUESTOS) if not hasattr(presupuestos, n)] == []
    # Entre los cuatro no nace ni se pierde un nombre publico: solo cambian de casa.
    familia = (
        "presupuestos",
        "presupuestos_calculo",
        "presupuestos_escenarios",
        "presupuestos_ayudas",
    )
    definidos = set().union(*(_definidos(RAIZ / "api" / "rutas" / f"{m}.py") for m in familia))
    assert definidos == PUBLICOS_DE_RUTAS_PRESUPUESTOS


#: Tarea 4.2: lo que `api/rutas/hoja.py` definia antes de partirse (77 nombres).
PUBLICOS_DE_RUTAS_HOJA = frozenset(
    {
        "CodigoDePartida",
        "CuentaDeLaHoja",
        "CuentaQueConvierte",
        "CuentaQueVe",
        "FORMA_ANTES",
        "FORMA_APU",
        "FORMA_BUSQUEDA",
        "FORMA_CADENA",
        "FORMA_CANTIDADES",
        "FORMA_CONVERTIR",
        "FORMA_COTIZAR",
        "FORMA_GUARDAR",
        "FORMA_INSUMO",
        "FORMA_LINEA",
        "FORMA_PARAMETROS",
        "FORMA_PARTIDA",
        "FORMA_PLAN",
        "FORMA_QUITAR",
        "FORMA_QUITAR_LINEA",
        "FORMA_RENDIMIENTOS",
        "FORMA_RESTAURAR",
        "FORMA_RETIRAR",
        "FORMA_REV",
        "IdDeBorrador",
        "MENSAJE_BASE",
        "MENSAJE_CON_VERSIONES",
        "MENSAJE_FALTA",
        "MENSAJE_FORMA",
        "MENSAJE_FORMA_ESPACIO",
        "MENSAJE_OTRO_CASO",
        "MENSAJE_PARTIDA",
        "MENSAJE_REV",
        "MENSAJE_SIN_PLAN",
        "MENSAJE_SIN_PREPARAR",
        "MENSAJE_SIN_VERSION",
        "MENSAJE_SOLO_CUENTA",
        "MENSAJE_YA_TIENE_PLAN",
        "SIN_LINEA_BASE",
        "VER",
        "abrir_borrador",
        "agregar_linea_apu",
        "agregar_partida",
        "antes_y_despues",
        "buscar_insumos",
        "cadena_de_sellos",
        "cambiar_insumo",
        "cambios_del_borrador",
        "convertir_version",
        "cotizar_insumo",
        "crear_plan_secuencial",
        "descartar_borrador",
        "editar_apu",
        "editar_cantidades",
        "editar_espacio",
        "editar_parametros",
        "editar_plan",
        "guardar_borrador",
        "leer_borrador",
        "listar_borradores",
        "listar_importaciones",
        "listar_versiones",
        "plan_desde_rendimientos",
        "precios",
        "precios_atipicos",
        "quitar_linea_apu",
        "quitar_partida",
        "restaurar_version",
        "retirar_cotizacion",
        "router",
        "trazabilidad",
        "vista_apu",
        "vista_auditoria",
        "vista_equilibrio",
        "vista_espacio",
        "vista_parametros",
        "vista_plan",
        "vista_presupuesto",
    }
)
#: Las rutas que pasan a `hoja_lecturas` y a `hoja_cadena`, cada una con su `router`.
EN_HOJA_LECTURAS = frozenset(
    {
        "antes_y_despues",
        "buscar_insumos",
        "cambios_del_borrador",
        "precios",
        "precios_atipicos",
        "router",
        "trazabilidad",
        "vista_apu",
        "vista_auditoria",
        "vista_equilibrio",
        "vista_espacio",
        "vista_parametros",
        "vista_plan",
        "vista_presupuesto",
    }
)
EN_HOJA_CADENA = frozenset(
    {
        "cadena_de_sellos",
        "convertir_version",
        "cotizar_insumo",
        "restaurar_version",
        "retirar_cotizacion",
        "router",
    }
)


def test_rutas_hoja_reparte_lo_mismo():
    """`api/rutas/hoja.py` no es fachada: sus hermanos (`hoja_exportar`, `hoja_libro`, `hoja_plano`)
    toman de el la clase de ruta y los ayudantes, y reexportarlos cerraria un ciclo. Lo que se
    fija es el reparto: ningun nombre publico nace ni se pierde, y cada uno vive donde se dice."""
    casas = ("hoja", "hoja_lecturas", "hoja_cadena")
    definidos = {m: _definidos(RAIZ / "api" / "rutas" / f"{m}.py") for m in casas}
    assert set().union(*definidos.values()) == PUBLICOS_DE_RUTAS_HOJA
    assert definidos["hoja_lecturas"] == EN_HOJA_LECTURAS
    assert definidos["hoja_cadena"] == EN_HOJA_CADENA
    quedan = PUBLICOS_DE_RUTAS_HOJA - EN_HOJA_LECTURAS - EN_HOJA_CADENA
    assert definidos["hoja"] == quedan | {"router"}


#: Tarea 4.3: lo que `aplicacion/control.py` definia antes de partirse (75 nombres; su `__all__`
#: de entonces listaba 56, y `aplicacion.reajuste` ya importaba tres de los que faltaban).
PUBLICOS_DE_CONTROL = frozenset(
    {
        "COLUMNAS_ALERTAS",
        "COLUMNAS_DECISIONES",
        "COLUMNAS_INDICADORES",
        "COLUMNAS_LINEAS",
        "COLUMNAS_OPCIONES",
        "COLUMNAS_PARAMETROS",
        "COLUMNAS_REPROYECCION",
        "COLUMNAS_VALUACIONES",
        "ControlInvalido",
        "DIAS_POR_OMISION",
        "DiasDelPlan",
        "Hueco",
        "LARGO_MAXIMO_A_CORREGIR",
        "MAXIMO_DE_PARTIDAS_DEL_CONTRATO",
        "MENSAJE_SIN_DECLARADOS",
        "METODOS_DE_PRECIOS",
        "METODO_COMPROBACION",
        "METODO_DECLARADOS",
        "METODO_ESCALATORIA",
        "METODO_NINGUNO",
        "NATURALEZA_DATO",
        "NATURALEZA_SUPUESTO",
        "NO_APLICA",
        "NO_DISPONIBLE",
        "PARAMETROS_EDITABLES",
        "PLANTILLAS_DEL_NUCLEO",
        "PartidaDelContrato",
        "PartidasDeUnaVersion",
        "PrecioElegido",
        "alertas_en_filas",
        "anular",
        "calcular_el_control",
        "calcular_las_opciones",
        "catalogo_de_frases",
        "con_tildes",
        "corte_por_defecto",
        "curva_pv_ev_ac",
        "declarar_linea_base",
        "describir_linea_base",
        "dia_con_fecha",
        "dias_de_las_etiquetas",
        "dias_por_periodo_del_plan",
        "elegir_opcion",
        "estado_de_valuaciones",
        "estudios_que_suma",
        "filas_de_decisiones",
        "filas_de_indicadores",
        "filas_de_opciones",
        "filas_de_parametros",
        "filas_de_reproyeccion",
        "filas_de_valuaciones",
        "filas_del_plan_reproyectado",
        "guardar_los_parametros",
        "hay_valuaciones",
        "importar_excel",
        "impuestos_de_valuaciones",
        "leer_excel",
        "lineas_desde_filas",
        "parametros_actuales",
        "parametros_desde_filas",
        "partidas_de_la_linea_base",
        "partidas_de_la_version",
        "perspectiva_de_la_linea_base",
        "precios_del_corte",
        "registrar_costo_real",
        "registrar_y_controlar",
        "renglones_de_la_version",
        "subtotales_de_valuaciones",
        "supuestos_de_opcion",
        "tablas_de_control",
        "texto_monto",
        "tiene_linea_base",
        "valuaciones_para_anular",
        "versiones_para_la_linea_base",
        "versiones_revaloradas",
    }
)


def test_control_reexporta_lo_mismo():
    from aplicacion import control

    assert sorted(control.__all__) == sorted(PUBLICOS_DE_CONTROL)
    assert [n for n in sorted(PUBLICOS_DE_CONTROL) if not hasattr(control, n)] == []
    # Entre los seis no nace ni se pierde un nombre publico: solo cambian de casa.
    familia = ("", "_comun", "_linea_base", "_calculo", "_tablas", "_parametros")
    definidos = set().union(*(_definidos(RAIZ / "aplicacion" / f"control{m}.py") for m in familia))
    assert definidos == PUBLICOS_DE_CONTROL


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


# --- Tarea 2.5: una sola politica de «rendimiento vigente» y una sola busqueda de obra ----------


def _es_estimado(nodo: ast.AST) -> bool:
    """`TipoRendimiento.ESTIMADO` (o su `.value`) dentro de una comparacion."""
    return any(
        isinstance(n, ast.Attribute)
        and n.attr == "ESTIMADO"
        and isinstance(n.value, ast.Name)
        and n.value.id == "TipoRendimiento"
        for n in ast.walk(nodo)
    )


def _compara_con_estimado(nodo: ast.AST) -> bool:
    """Una comparacion con `TipoRendimiento.ESTIMADO` (o su `.value`) o con el texto `"estimado"`
    que guarda la base (sin mirar mayusculas). Un docstring que lo nombra no es comparacion."""
    if not isinstance(nodo, ast.Compare):
        return False
    return _es_estimado(nodo) or any(
        isinstance(p, ast.Constant) and isinstance(p.value, str) and p.value.lower() == "estimado"
        for p in (nodo.left, *nodo.comparators)
    )


def _ordena_con_igual(nodo: ast.AST) -> bool:
    """`a <= b`, `a >= b`, `not a < b` o `not a > b`: «no posterior a», en cualquier sentido."""
    if isinstance(nodo, ast.Compare):
        return any(isinstance(op, ast.LtE | ast.GtE) for op in nodo.ops)
    return (
        isinstance(nodo, ast.UnaryOp)
        and isinstance(nodo.op, ast.Not)
        and isinstance(nodo.operand, ast.Compare)
        and any(isinstance(op, ast.Lt | ast.Gt) for op in nodo.operand.ops)
    )


def _cabeceras(sentencia: ast.stmt) -> list[ast.AST]:
    """Lo que una sentencia evalua sin entrar en su cuerpo: la condicion de un `if` o un `while`,
    lo que recorre un `for`, los `with`; una sentencia simple entera. Las definiciones no cuentan
    aqui (sus sentencias se miran una a una)."""
    if isinstance(sentencia, ast.If | ast.While):
        return [sentencia.test]
    if isinstance(sentencia, ast.For | ast.AsyncFor):
        return [sentencia.iter]
    if isinstance(sentencia, ast.With | ast.AsyncWith):
        return [item.context_expr for item in sentencia.items]
    if isinstance(sentencia, ast.Match):
        return [sentencia.subject]
    compuestas = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Try, ast.TryStar)
    return [] if isinstance(sentencia, compuestas) else [sentencia]


def _politicas_de_vigencia(archivo: Path) -> list[int]:
    """Lineas de cada sentencia que compara con lo «estimado» y, en la misma sentencia, ordena
    fechas con igual (`<=`, `>=`, `not <`, `not >`): la politica de «rendimiento estimado vigente a
    la fecha» escrita por su cuenta, sea en Python (`a and b`, un `any(...)`) o en un filtro SQL
    (`.where(a, b)`, `and_(a, b)` o dos `.where` encadenados). Una politica partida en dos
    sentencias (`if tipo != ESTIMADO: continue` y luego la fecha) no la ve."""
    lineas = set()
    for sentencia in ast.walk(_arbol(archivo)):
        if not isinstance(sentencia, ast.stmt):
            continue
        nodos = [n for cabecera in _cabeceras(sentencia) for n in ast.walk(cabecera)]
        if any(map(_compara_con_estimado, nodos)) and any(map(_ordena_con_igual, nodos)):
            lineas.add(sentencia.lineno)
    return sorted(lineas)


def test_la_politica_de_vigencia_vive_en_un_solo_sitio():
    """Solo `aplicacion.elaboracion.es_rendimiento_vigente` escribe «el estimado vigente a la
    fecha».

    No ve: el rango con `.between(a, b)`, `TipoRendimiento.ESTIMADO` leido por atributo de otro
    modulo (`models.TipoRendimiento.ESTIMADO`) ni la politica partida en dos sentencias (DS-50)."""
    sitios = {
        ruta: lineas
        for ruta in _lineas_de_produccion()
        if (lineas := _politicas_de_vigencia(RAIZ / ruta))
    }
    assert list(sitios) == ["aplicacion/elaboracion.py"], sitios
    assert len(sitios["aplicacion/elaboracion.py"]) == 1, "solo es_rendimiento_vigente la escribe"


def test_la_politica_de_vigencia_ve_la_falta(tmp_path):
    fuentes = {
        "x = r.tipo is TipoRendimiento.ESTIMADO and r.fecha <= fecha\n": [1],
        "x = r.tipo == TipoRendimiento.ESTIMADO.value and r.fecha <= fecha\n": [1],
        "x = r.tipo is TipoRendimiento.MEDIDO and r.fecha <= fecha\n": [],
        "x = r.tipo is TipoRendimiento.ESTIMADO and r.fecha == fecha\n": [],
        # Anexo A.7: el orden al reves, `not <`, el texto de la base y los filtros SQL.
        'x = any(r.tipo == "estimado" and fecha >= r.fecha for r in rs)\n': [1],
        "x = r.tipo is TipoRendimiento.ESTIMADO and not fecha < r.fecha\n": [1],
        "x = r.tipo is TipoRendimiento.ESTIMADO and not (r.fecha > fecha)\n": [1],
        "if r.tipo == TipoRendimiento.ESTIMADO.value and r.fecha <= fecha:\n    pass\n": [1],
        "q = select(R).where(R.tipo == TipoRendimiento.ESTIMADO, R.fecha <= fecha)\n": [1],
        'q = (\n    select(R)\n    .where(R.tipo == "estimado")\n    .where(R.fecha <= f)\n)\n': [
            1
        ],
        'q = select(R).where(and_(R.tipo == "ESTIMADO", R.fecha <= f))\n': [1],
        'x = r.tipo == "medido" and r.fecha <= fecha\n': [],
        '"""Vigente es el "estimado" con fecha <= la del presupuesto."""\n': [],
        'x = r.tipo == "estimado" and r.fecha < fecha\n': [],
    }
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"vigencia_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = _politicas_de_vigencia(archivo)
    assert detectadas == fuentes


#: Archivos que la repiten y no se pueden tocar (2026-11-17): `aplicacion/hoja.py` es un archivo
#: del auditor del experimento congelado (`asistente/experimento/protocolo.json`, RS-9; Eugenio,
#: 2026-10-18: el protocolo no se toca) y cambiarlo rompe
#: `test_experimento_congelado_vigente.py`. Sale de aqui cuando se vuelva a congelar a proposito.
#: 2026-11-18 (DS-50): `aplicacion/importaciones.py:168` (`select(Proyecto.id)`) y
#: `aplicacion/mercado.py:475` (`exists()`) repiten la busqueda pidiendo una columna o la existencia
#: de la obra; salen cuando llamen a `aplicacion.proyectos.proyecto_por_nombre`.
BUSQUEDA_DE_OBRA_CONGELADA: frozenset[str] = frozenset(
    {"aplicacion/hoja.py", "aplicacion/importaciones.py", "aplicacion/mercado.py"}
)


def _es_la_obra(nodo: ast.AST) -> bool:
    """`Proyecto` o `models.Proyecto`: la entidad entera, no una columna suya."""
    return (isinstance(nodo, ast.Name) and nodo.id == "Proyecto") or (
        isinstance(nodo, ast.Attribute) and nodo.attr == "Proyecto"
    )


def _es_nombre_de_la_obra(nodo: ast.AST) -> bool:
    return isinstance(nodo, ast.Attribute) and nodo.attr == "nombre" and _es_la_obra(nodo.value)


def _filtra_por_nombre(llamada: ast.Call) -> bool:
    """`.where(Proyecto.nombre == x)` (en cualquier lado del `==`), `.filter(...)` igual, o
    `.filter_by(nombre=x)`."""
    metodo = llamada.func.attr if isinstance(llamada.func, ast.Attribute) else ""
    if metodo == "filter_by":
        return any(clave.arg == "nombre" for clave in llamada.keywords)
    return metodo in {"where", "filter"} and any(
        isinstance(n, ast.Compare)
        and any(isinstance(op, ast.Eq) for op in n.ops)
        and any(map(_es_nombre_de_la_obra, (n.left, *n.comparators)))
        for argumento in llamada.args
        for n in ast.walk(argumento)
    )


def _raiz_de_la_cadena(llamada: ast.Call) -> ast.Call:
    """La primera llamada de `a(...).b(...).c(...)` (la `a(...)`)."""
    while isinstance(llamada.func, ast.Attribute) and isinstance(llamada.func.value, ast.Call):
        llamada = llamada.func.value
    return llamada


def _es_la_obra_o_su_columna(nodo: ast.AST) -> bool:
    """`Proyecto`, `models.Proyecto` o una columna suya (`Proyecto.id`)."""
    return _es_la_obra(nodo) or (isinstance(nodo, ast.Attribute) and _es_la_obra(nodo.value))


def _consulta_de_la_obra(llamada: ast.Call) -> bool:
    """`select(Proyecto)` o `x.query(Proyecto)`: solo se pide la obra, entera o en columnas suyas
    (`select(Proyecto.id)`, DS-50); o `exists()` sin argumentos, la existencia de lo filtrado."""
    funcion = llamada.func
    nombre = (
        funcion.id
        if isinstance(funcion, ast.Name)
        else funcion.attr
        if isinstance(funcion, ast.Attribute)
        else ""
    )
    if nombre == "exists":
        return not llamada.args and not llamada.keywords
    return (
        nombre in {"select", "query"}
        and len(llamada.args) >= 1
        and all(map(_es_la_obra_o_su_columna, llamada.args))
    )


def _busquedas_de_obra_por_nombre(archivo: Path) -> list[int]:
    """Lineas de cada `select(Proyecto)` (o `query(Proyecto)`) cuya cadena filtra por
    `Proyecto.nombre ==`, por AST: el `.where(` partido en varias lineas, el `==` al reves y el
    nombre sin `models.` cuentan; un comentario no. Tambien `select(Proyecto.<columna>)` y
    `exists().where(Proyecto.nombre == x)` (DS-50). Pedir otra entidad unida a la obra
    (`select(Presupuesto).join(Proyecto).where(...)`) no es buscar la obra."""
    return sorted(
        {
            raiz.lineno
            for nodo in ast.walk(_arbol(archivo))
            if isinstance(nodo, ast.Call)
            and _filtra_por_nombre(nodo)
            and _consulta_de_la_obra(raiz := _raiz_de_la_cadena(nodo))
        }
    )


def test_una_sola_busqueda_de_obra_por_nombre():
    """En `api/` y `aplicacion/` (lo que atiende al programa) la consulta vive en
    `aplicacion.proyectos.proyecto_por_nombre`. Los sembradores de `scripts/` quedan fuera: corren
    sobre una base nueva, antes del programa.

    No ve: la consulta partida en dos sentencias (`q = select(Proyecto)` y luego
    `q = q.where(Proyecto.nombre == n)`), ni el filtro por `.in_(...)`, `.like(...)` u otro
    operador que no sea `==` (DS-50)."""
    sitios = sorted(
        ruta
        for paquete in ("api", "aplicacion")
        for archivo in _archivos(paquete)
        if _busquedas_de_obra_por_nombre(archivo) and (ruta := _ruta(archivo))
    )
    assert sorted(set(sitios) - BUSQUEDA_DE_OBRA_CONGELADA) == ["aplicacion/proyectos.py"]


def test_una_sola_busqueda_de_obra_por_nombre_sin_sobrantes():
    for ruta in BUSQUEDA_DE_OBRA_CONGELADA:
        assert _busquedas_de_obra_por_nombre(RAIZ / ruta), (
            f"borrar {ruta} de BUSQUEDA_DE_OBRA_CONGELADA"
        )


def test_una_sola_busqueda_de_obra_por_nombre_ve_la_falta(tmp_path):
    """Anexo A.7: por AST, no por una subcadena de una linea."""
    fuentes = {
        "q = select(models.Proyecto).where(models.Proyecto.nombre == n)\n": [1],
        "q = select(models.Proyecto).where(\n    models.Proyecto.nombre == n\n)\n": [1],
        "q = (\n    select(models.Proyecto)\n    .where(models.Proyecto.nombre == n)\n)\n": [2],
        "q = select(Proyecto).where(Proyecto.nombre == n)\n": [1],
        "q = select(models.Proyecto).where(n == models.Proyecto.nombre).limit(1)\n": [1],
        "q = sesion.query(models.Proyecto).filter(models.Proyecto.nombre == n)\n": [1],
        "q = sesion.query(models.Proyecto).filter_by(nombre=n)\n": [1],
        # DS-50 (2): una columna de la obra o su existencia tambien es buscarla por nombre.
        "q = select(models.Proyecto.id).where(models.Proyecto.nombre == n)\n": [1],
        "q = select(Proyecto.id, Proyecto.moneda).where(Proyecto.nombre == n)\n": [1],
        "q = select(exists().where(models.Proyecto.nombre == n))\n": [1],
        "q = sa.exists().where(Proyecto.nombre == n)\n": [1],
        "q = select(Presupuesto.id).join(Proyecto).where(Proyecto.nombre == n)\n": [],
        # Lo que no es buscar la obra: otra entidad unida a la obra, otra columna, otro orden.
        "q = select(Presupuesto).join(Proyecto).where(Proyecto.nombre == n)\n": [],
        "q = select(models.Proyecto).where(models.Proyecto.id == n)\n": [],
        "q = select(models.Proyecto).order_by(models.Proyecto.nombre)\n": [],
        '# select(models.Proyecto).where(models.Proyecto.nombre == n)\nt = "x"\n': [],
    }
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"obra_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = _busquedas_de_obra_por_nombre(archivo)
    assert detectadas == fuentes


# --- Anexo A.2: un router con `RutaSinCache` no pone `Cache-Control` a mano --------------------


def _modulo_de(archivo: Path) -> str:
    return ".".join(archivo.relative_to(RAIZ).with_suffix("").parts)


def _usa_ruta_sin_cache(modulo: object) -> bool:
    """Algun `APIRouter` del modulo con `route_class` derivada de `RutaSinCache`, o alguna de sus
    rutas de esa clase (`route_class_override`, como en `casos.py`)."""
    from fastapi import APIRouter

    from api.sin_cache import RutaSinCache

    return any(
        isinstance(valor, APIRouter)
        and (
            issubclass(valor.route_class, RutaSinCache)
            or any(isinstance(ruta, RutaSinCache) for ruta in valor.routes)
        )
        for valor in vars(modulo).values()
    )


def _es_cabecera_de_cache(valor: object) -> bool:
    """Un diccionario de cabeceras con `Cache-Control` (sin mirar mayusculas)."""
    from collections.abc import Mapping

    return isinstance(valor, Mapping) and any(
        isinstance(clave, str) and clave.lower() == "cache-control" for clave in valor
    )


def _importados(arbol: ast.Module) -> dict[str, object]:
    """Nombre local -> objeto, de cada `from x import y` absoluto del modulo que se puede
    resolver (`y` como atributo de `x` o como su submodulo), y de cada `import a.b.c` (como
    `a`, `a.b` y `a.b.c`) o `import a.b.c as m` (como `m`) (DS-50). Lo que no se importa se
    ignora."""
    import importlib

    hallados: dict[str, object] = {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                try:
                    modulo = importlib.import_module(alias.name)
                except ImportError:
                    continue
                if alias.asname:
                    hallados[alias.asname] = modulo
                    continue
                partes = alias.name.split(".")
                for cuantas in range(1, len(partes) + 1):
                    prefijo = ".".join(partes[:cuantas])
                    hallados[prefijo] = importlib.import_module(prefijo)
            continue
        if not (isinstance(nodo, ast.ImportFrom) and nodo.module and not nodo.level):
            continue
        try:
            origen = importlib.import_module(nodo.module)
        except ImportError:
            continue
        for alias in nodo.names:
            nombre = alias.asname or alias.name
            if hasattr(origen, alias.name):
                hallados[nombre] = getattr(origen, alias.name)
            else:
                try:
                    hallados[nombre] = importlib.import_module(f"{nodo.module}.{alias.name}")
                except ImportError:
                    continue
    return hallados


def _cabecera_de_cache_a_mano(archivo: Path) -> list[int]:
    """Lineas de cada texto `"Cache-Control"` del codigo (una clave de `headers=` o de
    `response.headers[...]`) y de cada uso de un diccionario con esa cabecera importado de otro
    modulo (`SIN_CACHE` por nombre, o `modulo.SIN_CACHE`). Los docstrings que la nombran no
    cuentan; el texto `"no-store"` suelto tampoco (es el valor, no la cabecera)."""
    arbol = _arbol(archivo)
    importados = _importados(arbol)
    lineas: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Constant):
            if isinstance(nodo.value, str) and nodo.value.lower() == "cache-control":
                lineas.add(nodo.lineno)
        elif isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Load):
            if _es_cabecera_de_cache(importados.get(nodo.id)):
                lineas.add(nodo.lineno)
        elif (
            isinstance(nodo, ast.Attribute)
            and (punteado := _punteado(nodo.value)) in importados
            and _es_cabecera_de_cache(getattr(importados[punteado], nodo.attr, None))
        ):
            lineas.add(nodo.lineno)
    return sorted(lineas)


def _punteado(nodo: ast.expr) -> str | None:
    """`m` o `api.rutas.x` como texto; `None` si no es una cadena de nombres."""
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute) and (base := _punteado(nodo.value)) is not None:
        return f"{base}.{nodo.attr}"
    return None


def test_un_router_sin_cache_no_pone_la_cabecera_a_mano():
    """`RutaSinCache` ya pone `no-store` en toda respuesta, tambien en los errores; repetirlo a
    mano es una segunda fuente que puede desviarse (H11). Las pruebas de `no-store` de cada router
    son el oraculo de conducta.

    No ve: el diccionario armado en la ruta con la clave en una variable (`clave = "Cache-" +
    "Control"`), ni el que llega por una funcion o por `importlib.import_module` (DS-50)."""
    import importlib

    sitios = sorted(
        f"{_ruta(archivo)}:{linea}"
        for archivo in _archivos_de_rutas()
        if _usa_ruta_sin_cache(importlib.import_module(_modulo_de(archivo)))
        for linea in _cabecera_de_cache_a_mano(archivo)
    )
    assert sitios == [], "RutaSinCache ya pone la cabecera:\n" + "\n".join(sitios)


def test_la_cabecera_a_mano_ve_la_falta(tmp_path):
    archivo = tmp_path / "ruta.py"
    archivo.write_text(
        '"""Toda respuesta lleva `Cache-Control: no-store`."""\n'
        'SIN_CACHE = {"Cache-Control": "no-store"}\n'
        'def f(response):\n    response.headers["cache-control"] = "no-store"\n',
        encoding="utf-8",
    )
    assert _cabecera_de_cache_a_mano(archivo) == [2, 4]


def test_la_cabecera_a_mano_ve_un_sin_cache_importado(tmp_path):
    """Anexo A.7: el diccionario `{"Cache-Control": ...}` de otro modulo, importado por nombre o
    leido como atributo del modulo, es la misma cabecera a mano. El texto `"no-store"` de
    `api.sin_cache` no es la cabecera (solo su valor)."""
    archivo = tmp_path / "ruta.py"
    archivo.write_text(
        "from api.rutas.indices import SIN_CACHE\n"
        "from api.rutas import reajuste\n"
        "from api.sin_cache import SIN_CACHE as VALOR\n"
        'def f():\n    raise HTTPException(404, "x", headers=SIN_CACHE)\n'
        "def g(response):\n    response.headers.update(reajuste.SIN_CACHE)\n"
        "def h():\n    return VALOR\n",
        encoding="utf-8",
    )
    assert _cabecera_de_cache_a_mano(archivo) == [5, 7]


def test_la_cabecera_a_mano_ve_un_sin_cache_por_import_de_modulo(tmp_path):
    """DS-50 (5): `import api.rutas.x as m` + `m.SIN_CACHE` y `import api.rutas.x` +
    `api.rutas.x.SIN_CACHE` son el mismo diccionario importado."""
    archivo = tmp_path / "ruta.py"
    archivo.write_text(
        "import api.rutas.indices as m\n"
        "import api.rutas.reajuste\n"
        "import api.sin_cache\n"
        "def f(response):\n    response.headers.update(m.SIN_CACHE)\n"
        "def g():\n    return api.rutas.reajuste.SIN_CACHE\n"
        "def h():\n    return api.sin_cache.SIN_CACHE\n",
        encoding="utf-8",
    )
    assert _cabecera_de_cache_a_mano(archivo) == [5, 7]


def test_la_guardia_reconoce_los_routers_sin_cache():
    """No pasa en vacio: ve la clase propia (`entregas`), la de Administracion (`admin_empresa`) y
    la que se pone ruta por ruta (`casos`); no ve un router que solo usa `RutaSinEco`."""
    import importlib

    vistos = {
        nombre: _usa_ruta_sin_cache(importlib.import_module(f"api.rutas.{nombre}"))
        for nombre in ("entregas", "admin_empresa", "casos", "composicion")
    }
    assert vistos == {"entregas": True, "admin_empresa": True, "casos": True, "composicion": False}
