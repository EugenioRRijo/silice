"""Hace ejecutable la hipótesis central (NORMAS.md §1 y §2).

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
PAQUETES_FUERA_DEL_NUCLEO = (
    "adapters",
    "ml",
    "ui",
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


#: Lo que cada modulo de ui/ no importa en tiempo de ejecucion (fuera de `if TYPE_CHECKING:`).
#: Reglas de interfaz del plan de C3 (Global Constraints) e INV-043 para la pagina de componer.
PROHIBIDOS_EN_UI: dict[str, tuple[str, ...]] = {
    "ui/paginas/componer.py": ("core.budget", "core.costing", "sqlalchemy.orm", "tempfile"),
    # U-6 de la pista U de C5 (A-2 de GC5): el plan por defecto lo decide `ui.elaboracion.plan_de`.
    "ui/paginas/elaborar.py": ("core.budget",),
    # RA-2: "no escribe en la base" vigilado tambien por core.catalog, core.budget y sqlalchemy.
    "ui/composicion.py": (
        "streamlit",
        "pandas",
        "ui.caso",
        "sqlalchemy",
        "core.catalog",
        "core.budget",
    ),
    "ui/elaboracion.py": ("streamlit", "pandas", "ui.caso"),
    # SF 1.8: la hoja orquesta el borrador y la elaboracion sin pintar (FR-5: sin Streamlit).
    "ui/hoja.py": ("streamlit", "pandas", "ui.caso"),
    # ARQ-A2: el fragmento pinta; no abre la base ni lee el catalogo.
    "ui/resultado.py": ("sqlalchemy.orm", "core.costing", "core.catalog"),
    # RF-37: los recorridos se declaran en un modulo sin Streamlit ni base de datos (A6, R-3).
    "ui/recorridos.py": ("streamlit", "sqlalchemy", "core.catalog", "ui.caso", "ui.app"),
    # SF4: las operaciones sobre proyectos no pintan ni leen la sesion de Streamlit.
    "ui/proyectos.py": ("streamlit", "pandas", "ui.caso", "ui.app", "ui.barra"),
    # Tarea 4.9 (RT-S4-3): la logica de la pantalla de la arenera se prueba sin Streamlit.
    "ui/existencias.py": ("streamlit", "pandas"),
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


#: Las paginas de ui/ (y su `__init__`): el marco `ui/app.py` las importa, ninguna lo importa a el.
PAGINAS_DE_UI = sorted((RAIZ / "ui" / "paginas").glob("*.py"))


def test_solo_ui_app_importa_la_barra_de_herramientas():
    """SF4 4.2: `ui/barra.py` es parte del marco; lo importa SOLO `ui/app.py`."""
    importadores = sorted(
        archivo.relative_to(RAIZ).as_posix()
        for archivo in (RAIZ / "ui").rglob("*.py")
        if archivo.name != "barra.py"
        and any(
            nombre == "ui.barra" or nombre.startswith("ui.barra.")
            for nombre in _imports_de_ejecucion(archivo)
        )
    )
    assert importadores == ["ui/app.py"]


def _importa_el_marco(ruta: Path) -> list[str]:
    """Lo que `ruta` importa de `ui.app` en tiempo de ejecucion (`_imports_de_ejecucion`)."""
    return sorted(
        nombre
        for nombre in _imports_de_ejecucion(ruta)
        if nombre == "ui.app" or nombre.startswith("ui.app.")
    )


def test_la_guardia_del_marco_recorre_las_paginas():
    """Sin parametrizar a proposito (O-1 de la revision de la pista C de C4): si `PAGINAS_DE_UI`
    quedara vacia, pytest omitiria la prueba parametrizada en vez de fallar."""
    assert RAIZ / "ui" / "paginas" / "escenarios.py" in PAGINAS_DE_UI


@pytest.mark.parametrize("pagina", PAGINAS_DE_UI, ids=_ruta)
def test_ninguna_pagina_importa_el_marco(pagina):
    """M-2 de la revision de arquitectura de GC3: el grafo `ui.app -> ui.paginas.*` es aciclico
    (`ui/app.py`) solo si ninguna pagina importa `ui.app`, ni con `import ui.app` ni con
    `from ui import app` (`_imports_de_ejecucion` registra `ui.app` en los dos casos)."""
    marco = _importa_el_marco(pagina)
    assert not marco, f"{_ruta(pagina)} importa {marco}: el marco importa las paginas, no al reves"


def test_la_guardia_del_marco_ve_cada_forma_de_importarlo(tmp_path):
    """Las mordidas de la guardia, fijadas (O-2 de la revision de la pista C de C4), como
    `test_la_guardia_ve_las_importaciones_relativas`: cada forma de importar `ui.app` en tiempo
    de ejecucion se detecta, y un nombre que solo empieza igual o un import de tipado no.
    Limite declarado, comun a `_imports_de_ejecucion`: `from .. import app` e
    `importlib.import_module("ui.app")` no se ven (ninguna pagina usa esas formas)."""
    fuentes = {
        "import ui.app\n": True,
        "import ui.app as marco\n": True,
        "from ui import app\n": True,
        "from ui.app import render\n": True,
        "def perezosa():\n    from ui import app\n": True,
        "from ui import app_nueva\n": False,
        "import ui.apply\n": False,
        "from ui import caso\n": False,
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from ui import app\n": False,
    }
    detectadas = {}
    for numero, fuente in enumerate(fuentes):
        archivo = tmp_path / f"pagina_{numero}.py"
        archivo.write_text(fuente, encoding="utf-8")
        detectadas[fuente] = bool(_importa_el_marco(archivo))
    assert detectadas == fuentes


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


# --- SF1: el grafo de dependencias de adapters/espacio y de ui.hoja no tiene ciclos --------------


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


def test_ui_hoja_depende_de_adapters_espacio_y_este_no_depende_de_ui():
    """La arista es ui.hoja -> adapters.espacio y no existe la inversa: sin ciclo entre capas."""
    de_hoja = {m for m in _imports(RAIZ / "ui" / "hoja.py") if m.startswith("adapters")}
    assert de_hoja and all(
        m == "adapters.espacio" or m.startswith("adapters.espacio.") for m in de_hoja
    ), de_hoja
    inversa = [
        f"{_ruta(a)}: {m}"
        for a in _archivos("adapters/espacio")
        for m in _imports(a)
        if m == "ui" or m.startswith("ui.")
    ]
    assert not inversa, inversa
