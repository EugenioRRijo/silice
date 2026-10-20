"""Qué archivos viajan en el instalador y cómo se arma el árbol `{app}\\codigo` (spec S5 §7.1).

Lista blanca (`manifiesto.toml`): los paquetes del producto completos, de `scripts/` y
`tests/fixtures/` solo el cierre de importaciones de los sembradores y del simulador (calculado
leyendo el árbol sintáctico), la lista blanca de `data/`, `pyproject.toml` y `LICENSE`, más el
`config.toml` oficial. Todo lo demás (`.venv`, `*.db`, `docs/`, los `.xls` del BCV, las bases de
prueba) está prohibido y, si algo lo trae, el armado falla en vez de copiarlo.
"""

from __future__ import annotations

import ast
import shutil
import tomllib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_MANIFIESTO = Path(__file__).with_name("manifiesto.toml")
RUTA_CONFIG_OFICIAL = Path(__file__).with_name("streamlit_config.toml")
RAICES_PROPIAS = frozenset(
    {
        "core",
        "adapters",
        "ml",
        "ui",
        "api",
        "operacion",
        "migraciones",
        "seguridad",
        "asistente",
        "aplicacion",
        "produccion",
        "scripts",
        "tests",
    }
)
DIRECTORIOS_EXCLUIDOS = frozenset(
    {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv", "node_modules"}
)
SUFIJOS_EXCLUIDOS = frozenset(
    {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".db-journal", ".db-wal", ".db-shm"}
)
PROHIBIDOS = (
    "tests/fixtures/bcv/",
    "tests/fixtures/bases/",
    "docs/",
    ".venv/",
    ".worktrees/",
    "data/apu.db",
    "data/casos/",
    "data/respaldos/",
)


class ManifiestoInvalido(ValueError):  # noqa: N818
    pass


@dataclass(frozen=True, slots=True)
class Manifiesto:
    python: str
    extras_basica: tuple[str, ...]
    ifc: bool
    extras_similitud: tuple[str, ...]
    paquetes: tuple[str, ...]
    archivos: tuple[str, ...]
    cierre_desde: tuple[str, ...]
    datos_incluir: tuple[str, ...]
    datos_excluir_sufijos: tuple[str, ...]
    interfaz_dist: str


def cargar(ruta: Path = RUTA_MANIFIESTO) -> Manifiesto:
    datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    try:
        ifc = datos["capas"]["ifc"]
        if not isinstance(ifc, bool):
            raise ManifiestoInvalido("capas.ifc debe ser true o false")
        return Manifiesto(
            python=str(datos["python"]["version"]),
            extras_basica=tuple(datos["capas"]["basica"]),
            ifc=ifc,
            extras_similitud=tuple(datos["capas"]["similitud"]),
            paquetes=tuple(datos["codigo"]["paquetes"]),
            archivos=tuple(datos["codigo"]["archivos"]),
            cierre_desde=tuple(datos["codigo"]["cierre_desde"]),
            datos_incluir=tuple(datos["datos"]["incluir"]),
            datos_excluir_sufijos=tuple(datos["datos"]["excluir_sufijos"]),
            interfaz_dist=str(datos["interfaz"]["dist"]),
        )
    except KeyError as error:
        raise ManifiestoInvalido(f"{ruta.name}: falta la clave {error}") from error


def _modulo_a_archivo(raiz: Path, modulo: str) -> Path | None:
    base = raiz.joinpath(*modulo.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def _importados(raiz: Path, archivo: Path) -> set[str]:
    """Módulos propios que `archivo` importa, en cualquier parte (también dentro de funciones)."""
    paquete = ".".join(archivo.relative_to(raiz).parent.parts)
    encontrados: set[str] = set()
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            encontrados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            base = nodo.module or ""
            if nodo.level:
                partes = paquete.split(".") if paquete else []
                partes = partes[: len(partes) - (nodo.level - 1)]
                base = ".".join([*partes, *([nodo.module] if nodo.module else [])])
            encontrados.add(base)
            encontrados.update(f"{base}.{alias.name}" for alias in nodo.names)
    return {m for m in encontrados if m and m.split(".")[0] in RAICES_PROPIAS}


def cierre_de_importaciones(raiz: Path, modulos: Sequence[str]) -> set[Path]:
    """Los archivos de los módulos de partida y de todo lo propio que importan, con los
    `__init__.py` de sus paquetes. Rutas relativas a `raiz`."""
    vistos: set[Path] = set()
    pendientes = list(modulos)
    while pendientes:
        modulo = pendientes.pop()
        archivo = _modulo_a_archivo(raiz, modulo)
        if archivo is None:
            continue
        partes = modulo.split(".")
        for n in range(1, len(partes)):
            inicio = raiz.joinpath(*partes[:n], "__init__.py")
            if inicio.is_file() and inicio not in vistos:
                vistos.add(inicio)
                pendientes.extend(_importados(raiz, inicio))
        if archivo not in vistos:
            vistos.add(archivo)
            pendientes.extend(_importados(raiz, archivo))
    return {a.relative_to(raiz) for a in vistos}


def _recorrer(carpeta: Path, raiz: Path) -> Iterator[Path]:
    for ruta in sorted(carpeta.rglob("*")):
        if not ruta.is_file():
            continue
        relativa = ruta.relative_to(raiz)
        if DIRECTORIOS_EXCLUIDOS & set(relativa.parts) or ruta.suffix in SUFIJOS_EXCLUIDOS:
            continue
        yield relativa


def _datos(raiz: Path, m: Manifiesto) -> set[Path]:
    salida: set[Path] = set()
    for patron in m.datos_incluir:
        if any(c in patron for c in "*?["):
            coincidencias = [p for p in raiz.glob(patron) if p.is_file()]
        elif (raiz / patron).is_dir():
            coincidencias = [p for p in (raiz / patron).rglob("*") if p.is_file()]
        elif (raiz / patron).is_file():
            coincidencias = [raiz / patron]
        else:
            raise ManifiestoInvalido(f"el dato declarado no existe: {patron}")
        for ruta in coincidencias:
            if ruta.suffix.lower() not in m.datos_excluir_sufijos:
                salida.add(ruta.relative_to(raiz))
    return salida


def archivos_de_codigo(raiz: Path, m: Manifiesto) -> list[Path]:
    """Los archivos que viajan, relativos a `raiz`, ordenados. Falla si falta algo declarado o si
    algo prohibido se cuela."""
    salida: set[Path] = set()
    for paquete in m.paquetes:
        carpeta = raiz / paquete
        if not carpeta.is_dir():
            raise ManifiestoInvalido(f"el paquete declarado no existe: {paquete}")
        salida.update(_recorrer(carpeta, raiz))
    salida.update(cierre_de_importaciones(raiz, m.cierre_desde))
    for archivo in m.archivos:
        if not (raiz / archivo).is_file():
            raise ManifiestoInvalido(f"el archivo declarado no existe: {archivo}")
        salida.add(Path(archivo))
    salida.update(_datos(raiz, m))
    prohibidos = sorted(
        p.as_posix()
        for p in salida
        if p.as_posix().startswith(PROHIBIDOS) or p.suffix in SUFIJOS_EXCLUIDOS
    )
    if prohibidos:
        raise ManifiestoInvalido("archivos prohibidos en el instalador: " + ", ".join(prohibidos))
    return sorted(salida)


def armar_arbol(raiz: Path, destino: Path, m: Manifiesto) -> list[Path]:
    """Copia los archivos del manifiesto a `destino` (= `{app}\\codigo`) y deja el `config.toml`
    oficial como único `.streamlit/config.toml`. Devuelve las rutas relativas copiadas."""
    archivos = archivos_de_codigo(raiz, m)
    for relativa in archivos:
        origen, copia = raiz / relativa, destino / relativa
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, copia)
    oficial = destino / ".streamlit" / "config.toml"
    oficial.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUTA_CONFIG_OFICIAL, oficial)
    return [*archivos, Path(".streamlit/config.toml")]


def copiar_interfaz(raiz: Path, destino: Path, m: Manifiesto) -> list[Path]:
    r"""Copia el `dist` ya compilado de la interfaz a `destino / <misma ruta relativa>` (con
    `destino` = `{app}\codigo`, `RAIZ` del producto, donde `api/interfaz.py` lo busca). No compila:
    si falta, está vacío o no trae `index.html`, falla diciendo cómo compilarlo."""
    origen = raiz / m.interfaz_dist
    como_compilar = (
        "compílela antes de construir el instalador: `npm ci && npm run build` en frontend-desktop"
    )
    archivos = sorted(p for p in origen.rglob("*") if p.is_file()) if origen.is_dir() else []
    if not archivos:
        raise ManifiestoInvalido(
            f"la interfaz compilada no existe o está vacía ({m.interfaz_dist}); {como_compilar}"
        )
    if not (origen / "index.html").is_file():
        raise ManifiestoInvalido(
            f"la interfaz compilada no trae index.html ({m.interfaz_dist}); {como_compilar}"
        )
    copiados: list[Path] = []
    for archivo in archivos:
        relativa = archivo.relative_to(raiz)
        copia = destino / relativa
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archivo, copia)
        copiados.append(relativa)
    return copiados
