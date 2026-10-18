"""Lo que viaja en el instalador es exactamente lo del manifiesto (RF-97 h; spec S5 §7.1 y §12).

Base: PLAN_SILICE_100 T13. Ajustes registrados en la bitácora 2026-10-silice-100: el paquete
`paquete` del plan no existía y se quitó; luego el coordinador agregó `paquete` y `auditoria` (la
interfaz ya los importa) y la 1.5 agregó `fusion` y el extra `pdf` (commit 80c205a); se sumó
`data/ids/silice_instalaciones.ids` a la lista blanca de datos.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from instalador import manifiesto as mf

RAIZ = Path(__file__).resolve().parents[2]
#: las banderas del lanzador del producto (RP10-7)
BANDERAS = ("-E", "-s", "-B", "-X", "utf8")
PROHIBIDOS = ("tests/fixtures/bcv/", "tests/fixtures/bases/", "docs/", ".venv/", ".worktrees/")


def _entorno_limpio() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}


@pytest.fixture(scope="module")
def arbol(tmp_path_factory) -> Path:
    destino = tmp_path_factory.mktemp("producto") / "codigo"
    mf.armar_arbol(RAIZ, destino, mf.cargar())
    return destino


def test_el_manifiesto_declara_lo_que_decide_el_spec() -> None:
    m = mf.cargar()
    assert m.python == "3.13.13"
    assert "xgboost" not in m.extras_basica and "ml" not in m.extras_basica
    assert set(m.extras_basica) == {
        "ui",
        "api",
        "planos",
        "informes",
        "bcv",
        "civil",
        "anomalias",
        "ia",
        "pdf",  # 1.5
    }
    assert m.ifc is False  # RP10-4: bcf-client es GPLv3 hasta que S3-0 resuelva
    assert m.extras_similitud == ("similitud",)
    assert set(m.paquetes) == {
        "core",
        "adapters",
        "ml",
        "ui",
        "api",
        "operacion",
        "migraciones",
        "seguridad",
        "asistente",
        "paquete",
        "auditoria",
        "fusion",
    }
    assert "instalador" not in m.paquetes  # herramienta de construcción: no viaja
    assert set(m.archivos) == {"pyproject.toml", "LICENSE"}
    assert {".pdf", ".db", ".xls", ".xlsx"} <= set(m.datos_excluir_sufijos)


def test_un_manifiesto_sin_una_clave_o_con_ifc_de_texto_es_invalido(tmp_path: Path) -> None:
    texto = mf.RUTA_MANIFIESTO.read_text(encoding="utf-8")
    sin_python = tmp_path / "sin_python.toml"
    sin_python.write_text(texto.replace("[python]", "[piton]"), encoding="utf-8")
    with pytest.raises(mf.ManifiestoInvalido, match="falta la clave"):
        mf.cargar(sin_python)
    ifc_texto = tmp_path / "ifc_texto.toml"
    ifc_texto.write_text(texto.replace("ifc = false", 'ifc = "false"'), encoding="utf-8")
    with pytest.raises(mf.ManifiestoInvalido, match="ifc"):
        mf.cargar(ifc_texto)


def _repo_chico(raiz: Path) -> Path:
    archivos = {
        "scripts/__init__.py": "",
        "scripts/seed.py": "from tests.fixtures import base\nfrom . import hermano\n"
        "def f():\n    from scripts.diferido import g\n    return g\n",
        "scripts/hermano.py": "import json\n",
        "scripts/diferido.py": "def g(): ...\n",
        "scripts/inutil.py": "import tests.fixtures.otro\n",
        "tests/__init__.py": "",
        "tests/fixtures/__init__.py": "",
        "tests/fixtures/base.py": "import json\n",
        "tests/fixtures/otro.py": "",
    }
    for relativa, texto in archivos.items():
        ruta = raiz / relativa
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8")
    return raiz


def test_el_cierre_sigue_importaciones_absolutas_relativas_y_diferidas(tmp_path: Path) -> None:
    cierre = mf.cierre_de_importaciones(_repo_chico(tmp_path), ["scripts.seed"])
    assert {p.as_posix() for p in cierre} == {
        "scripts/__init__.py",
        "scripts/seed.py",
        "scripts/hermano.py",
        "scripts/diferido.py",
        "tests/__init__.py",
        "tests/fixtures/__init__.py",
        "tests/fixtures/base.py",
    }  # ni `scripts/inutil.py` ni `tests/fixtures/otro.py`: nadie del cierre los importa


def test_el_cierre_de_un_modulo_que_no_existe_es_vacio(tmp_path: Path) -> None:
    assert mf.cierre_de_importaciones(_repo_chico(tmp_path), ["scripts.no_existe"]) == set()


def test_el_cierre_de_importaciones_de_la_siembra_esta_completo() -> None:
    m = mf.cargar()
    cierre = {p.as_posix() for p in mf.cierre_de_importaciones(RAIZ, m.cierre_desde)}
    assert {"scripts/seed.py", "scripts/seed_demo.py", "scripts/simular_lista.py"} <= cierre
    assert "tests/fixtures/apu_linea_base.py" in cierre  # scripts.seed lo importa (NORMAS §6)
    assert not [p for p in cierre if p.startswith(PROHIBIDOS) or p.endswith((".xls", ".xlsx"))]
    assert all(
        p.startswith(("scripts/", "tests/")) or p.split("/")[0] in m.paquetes for p in cierre
    )
    # el cierre no arrastra pruebas: de tests/ solo fixtures y los __init__ de sus paquetes
    assert not [
        p
        for p in cierre
        if p.startswith("tests/")
        and not p.startswith("tests/fixtures/")
        and p != "tests/__init__.py"
    ]


def test_nunca_viajan_fixtures_bcv_bases_ni_db(arbol: Path) -> None:
    viajan = {p.relative_to(arbol).as_posix() for p in arbol.rglob("*") if p.is_file()}
    assert not [p for p in viajan if p.startswith(PROHIBIDOS)]
    assert not [p for p in viajan if p.endswith((".db", ".xls", ".xlsx", ".pyc"))]
    assert not [p for p in viajan if p.startswith("data/") and p.endswith(".pdf")]
    assert not [p for p in viajan if p.startswith("instalador/")]
    assert not [
        p
        for p in viajan
        if p.startswith("tests/")
        and not p.startswith("tests/fixtures/")
        and p not in {"tests/__init__.py"}
    ]
    # lo que la lista blanca sí manda
    assert {"pyproject.toml", "LICENSE", "data/ids/silice_instalaciones.ids"} <= viajan
    assert [p for p in viajan if p.startswith("data/precios/maprex_2026-07/")]
    assert all(p.endswith(".csv") for p in viajan if p.startswith("data/precios/maprex_2026-07/"))


def test_un_unico_config_toml_y_es_el_oficial(arbol: Path) -> None:
    assert [p.relative_to(arbol).as_posix() for p in arbol.rglob("config.toml")] == [
        ".streamlit/config.toml"
    ]
    assert (
        arbol / ".streamlit" / "config.toml"
    ).read_bytes() == mf.RUTA_CONFIG_OFICIAL.read_bytes()


def test_la_configuracion_oficial_incluye_la_del_repositorio_y_las_opciones_fijas() -> None:
    oficial = tomllib.loads(mf.RUTA_CONFIG_OFICIAL.read_text(encoding="utf-8"))
    desarrollo = tomllib.loads((RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    faltan = [
        f"{seccion}.{clave}"
        for seccion, claves in desarrollo.items()
        for clave, valor in claves.items()
        if oficial.get(seccion, {}).get(clave) != valor
    ]
    assert faltan == []
    assert oficial["server"]["address"] == "127.0.0.1" and oficial["server"]["headless"] is True
    assert (
        oficial["server"]["fileWatcherType"] == "none" and oficial["server"]["runOnSave"] is False
    )
    assert (
        oficial["client"]["toolbarMode"] == "minimal"
        and oficial["global"]["developmentMode"] is False
    )
    assert oficial["browser"]["gatherUsageStats"] is False


def test_ui_y_api_se_importan_solo_con_el_arbol_del_manifiesto(arbol: Path) -> None:
    modulos = [
        "ui.app",
        "api.main",
        "operacion.__main__",
        "migraciones.comun",
        "scripts.seed",
        "scripts.seed_demo",
        "scripts.simular_lista",
    ]
    # Además de los pedidos, todo módulo cargado que venga del repositorio delata un hueco del
    # manifiesto (el repositorio no está en sys.path del hijo, pero un .pth podría ponerlo).
    programa = (
        "import importlib, json, sys\n"
        f"pedidos = {{n: importlib.import_module(n).__file__ for n in {modulos!r}}}\n"
        "cargados = {n: getattr(m, '__file__', None) for n, m in list(sys.modules.items())}\n"
        "print(json.dumps({'pedidos': pedidos, 'cargados': cargados}))\n"
    )
    hijo = subprocess.run(
        [sys.executable, *BANDERAS, "-c", programa],
        cwd=arbol,
        env=_entorno_limpio(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert hijo.returncode == 0, hijo.stderr[-2000:]
    datos = json.loads(hijo.stdout.splitlines()[-1])
    fuera = {
        n: r
        for n, r in datos["pedidos"].items()
        if not Path(r).resolve().is_relative_to(arbol.resolve())
    }
    assert fuera == {}  # nada pedido se importó del repositorio: todo salió del árbol
    entorno_virtual = Path(sys.prefix).resolve()  # los paquetes de terceros (.venv)
    del_repositorio = sorted(
        n
        for n, r in datos["cargados"].items()
        if r
        and Path(r).resolve().is_relative_to(RAIZ.resolve())
        and not Path(r).resolve().is_relative_to(entorno_virtual)
    )
    assert del_repositorio == []


def test_la_demostracion_se_siembra_con_el_arbol_del_manifiesto(
    arbol: Path, tmp_path: Path
) -> None:
    destino = tmp_path / "demo.db"
    programa = (
        f"from scripts.seed_demo import main\nraise SystemExit(main(['--db', {str(destino)!r}]))\n"
    )
    hijo = subprocess.run(
        [sys.executable, *BANDERAS, "-c", programa],
        cwd=arbol,
        env=_entorno_limpio(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert hijo.returncode == 0, hijo.stderr[-2000:]
    assert destino.stat().st_size > 0


def test_un_paquete_declarado_que_no_existe_falla(tmp_path: Path) -> None:
    m = mf.cargar()
    roto = replace(m, paquetes=("no_existe", *m.paquetes))
    with pytest.raises(mf.ManifiestoInvalido, match="no_existe"):
        mf.archivos_de_codigo(RAIZ, roto)


def test_un_archivo_o_un_dato_declarado_que_no_existe_falla(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    m = mf.Manifiesto("3.13.13", (), False, (), ("pkg",), (), (), (), (), "")
    with pytest.raises(mf.ManifiestoInvalido, match="NO_EXISTE.txt"):
        mf.archivos_de_codigo(tmp_path, replace(m, archivos=("NO_EXISTE.txt",)))
    with pytest.raises(mf.ManifiestoInvalido, match="data/no_existe"):
        mf.archivos_de_codigo(tmp_path, replace(m, datos_incluir=("data/no_existe",)))
    assert mf.archivos_de_codigo(tmp_path, m) == [Path("pkg/__init__.py")]


def test_un_dato_prohibido_hace_fallar_el_armado() -> None:
    m = mf.cargar()
    roto = replace(m, datos_incluir=(*m.datos_incluir, "docs"))
    with pytest.raises(mf.ManifiestoInvalido, match="docs/"):
        mf.archivos_de_codigo(RAIZ, roto)


def test_las_bases_de_prueba_no_viajan_aunque_se_declaren(tmp_path: Path) -> None:
    """Un árbol mínimo: la lista blanca pide `tests/fixtures/bases`, la lista negra lo frena."""
    for relativa in ("pkg/__init__.py", "tests/fixtures/bases/v0_5_0/ficha.json"):
        (tmp_path / relativa).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relativa).write_text("{}", encoding="utf-8")
    m = mf.Manifiesto(
        python="3.13.13",
        extras_basica=(),
        ifc=False,
        extras_similitud=(),
        paquetes=("pkg",),
        archivos=(),
        cierre_desde=(),
        datos_incluir=("tests/fixtures/bases",),
        datos_excluir_sufijos=(".db",),
        interfaz_dist="",
    )
    with pytest.raises(mf.ManifiestoInvalido, match="tests/fixtures/bases/v0_5_0/ficha.json"):
        mf.archivos_de_codigo(tmp_path, m)
    assert mf.archivos_de_codigo(tmp_path, replace(m, datos_incluir=())) == [
        Path("pkg/__init__.py")
    ]


def test_los_sufijos_excluidos_se_quedan_fuera_de_los_datos(tmp_path: Path) -> None:
    for relativa in ("data/x/a.csv", "data/x/b.pdf", "data/x/c.DB", "data/x/d.xlsx"):
        (tmp_path / relativa).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relativa).write_bytes(b"x")
    m = mf.Manifiesto(
        "3.13.13", (), False, (), (), (), (), ("data/x",), (".pdf", ".db", ".xlsx"), ""
    )
    assert mf.archivos_de_codigo(tmp_path, m) == [Path("data/x/a.csv")]


def test_nadie_fuera_de_tests_importa_instalador() -> None:
    from tests.fixtures.arquitectura import archivos, importaciones, ruta

    m = mf.cargar()
    infractores = sorted(
        ruta(a)
        for paquete in m.paquetes
        for a in archivos(paquete)
        if any(n == "instalador" or n.startswith("instalador.") for n in importaciones(a))
    )
    assert infractores == []
