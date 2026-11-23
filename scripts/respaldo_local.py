"""Respaldo local de Sílice FUERA de OneDrive (plan del consejo, días 1-2).

OneDrive sincroniza, no respalda: un borrado o un conflicto en `.git` se copia a la nube y a los
demás equipos. Este respaldo guarda en otra carpeta lo que NO se recupera desde GitHub:

* `repositorio.bundle`: todas las ramas y etiquetas del repositorio en un solo archivo, también
  las que nunca se subieron (`git bundle create --all`), verificado al terminar.
* `sin-commit/`: por cada árbol de trabajo (`git worktree list`), el parche de lo modificado y
  sin commit (`<árbol>.patch`) y una copia de los archivos nuevos sin seguimiento.
* `solo-en-el-equipo/`: por cada árbol, los archivos que git ignora y que no se pueden regenerar
  (libros de `docs/auditoria/`, bases `*.db`, los Word de la raíz, la configuración local). No
  entra lo que se reconstruye solo: `node_modules`, `.venv`, cachés y compilados.
* `extras/`: carpetas fuera del repositorio (la memoria de Claude, las skills propias, el Word de
  decisiones), si existen.
* `MANIFIESTO.txt`: el SHA-256 de cada archivo, para comprobar el respaldo con `verificar`.

Contiene datos reales: va a un disco local o externo, NUNCA a la nube ni al repositorio.

    uv run python scripts/respaldo_local.py               # a C:/RespaldoSilice/AAAAMMDD-HHMM
    uv run python scripts/respaldo_local.py --destino E:/RespaldoSilice --conservar 8
    uv run python scripts/respaldo_local.py verificar C:/RespaldoSilice/20261123-2000

Para restaurar: `git clone repositorio.bundle TESIS`, `git apply sin-commit/<árbol>.patch` en
cada árbol y copiar de vuelta `sin-commit/<árbol>/` y `solo-en-el-equipo/<árbol>/`.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

REGENERABLES = frozenset({
    ".git", "node_modules", "node_modules.viejo", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", ".vite", "dist", "build", "coverage",
    "dist_portable", "demo_dist", "graphify-out", "target",
})
SUFIJOS_REGENERABLES = (".pyc", ".pyo")
TOPE_BYTES = 300 * 1024 * 1024  # un archivo más grande se anota y no se copia
SELLO = re.compile(r"^\d{8}-\d{4}$")
MANIFIESTO = "MANIFIESTO.txt"


# --- git -----------------------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout


def arboles(repo: Path) -> list[Path]:
    """El árbol principal primero y después los demás árboles de trabajo que existen en disco."""
    salida = _git(repo, "worktree", "list", "--porcelain").decode("utf-8")
    rutas = [Path(linea[len("worktree "):]) for linea in salida.splitlines()
             if linea.startswith("worktree ")]
    return [p for p in rutas if p.exists()]


def _nombres(rutas: Sequence[Path], principal: Path) -> dict[Path, str]:
    """Un nombre de carpeta por árbol: «principal» y el nombre del árbol (con su carpeta madre si
    dos se llaman igual)."""
    nombres: dict[Path, str] = {}
    usados: set[str] = {"principal"}
    for ruta in rutas:
        if ruta.resolve() == principal.resolve():
            nombres[ruta] = "principal"
            continue
        nombre = ruta.name
        if nombre in usados:
            nombre = f"{ruta.parent.name}-{ruta.name}"
        usados.add(nombre)
        nombres[ruta] = nombre
    return nombres


def _lista_z(datos: bytes) -> list[str]:
    return [p for p in datos.decode("utf-8").split("\0") if p]


# --- copiar --------------------------------------------------------------------------------------


def _regenerable(relativa: str) -> bool:
    partes = relativa.replace("\\", "/").strip("/").split("/")
    return any(p in REGENERABLES for p in partes) or relativa.endswith(SUFIJOS_REGENERABLES)


def _dentro(ruta: Path, otras: Iterable[Path]) -> bool:
    ruta = ruta.resolve()
    return any(ruta == o or ruta.is_relative_to(o) for o in otras)


def _archivos(base: Path, relativa: str, excluir: Sequence[Path]) -> Iterator[str]:
    """Los archivos bajo `relativa` (archivo o carpeta), sin lo regenerable ni otros árboles."""
    origen = base / relativa
    if origen.is_file():
        if not _regenerable(relativa):
            yield relativa.replace("\\", "/")
        return
    for actual, carpetas, archivos in os.walk(origen):
        actual_p = Path(actual)
        carpetas[:] = [c for c in carpetas
                       if c not in REGENERABLES and not _dentro(actual_p / c, excluir)]
        for a in archivos:
            rel = (actual_p / a).relative_to(base).as_posix()
            if not _regenerable(rel):
                yield rel


def _copiar(base: Path, relativas: Iterable[str], destino: Path, notas: list[str]) -> None:
    for rel in relativas:
        origen = base / rel
        try:
            if origen.stat().st_size > TOPE_BYTES:
                notas.append(f"no copiado por tamaño (> 300 MB): {base.name}/{rel}")
                continue
            final = destino / rel
            final.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origen, final)
        except OSError as exc:
            notas.append(f"no se pudo copiar {base.name}/{rel}: {exc.strerror or exc}")


# --- manifiesto ----------------------------------------------------------------------------------


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def escribir_manifiesto(carpeta: Path, cabecera: Sequence[str]) -> None:
    lineas = [f"# {c}" for c in cabecera]
    for p in sorted(carpeta.rglob("*")):
        rel = p.relative_to(carpeta).as_posix()
        if p.is_file() and rel != MANIFIESTO:
            lineas.append(f"{_sha256(p)}  {rel}")
    (carpeta / MANIFIESTO).write_text("\n".join(lineas) + "\n", encoding="utf-8")


def verificar(carpeta: Path) -> list[str]:
    """Las rutas del manifiesto que faltan o cuyo SHA-256 cambió (lista vacía si está sano)."""
    malos = []
    for linea in (Path(carpeta) / MANIFIESTO).read_text(encoding="utf-8").splitlines():
        if not linea or linea.startswith("#"):
            continue
        suma, _, rel = linea.partition("  ")
        ruta = Path(carpeta) / rel
        if not ruta.is_file() or _sha256(ruta) != suma:
            malos.append(rel)
    return malos


# --- respaldar -----------------------------------------------------------------------------------


def onedrive() -> tuple[Path, ...]:
    """Las carpetas de OneDrive de este equipo (variables de entorno de Windows)."""
    rutas = {Path(os.environ[v]) for v in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")
             if os.environ.get(v)}
    rutas.add(Path.home() / "OneDrive")
    return tuple(sorted(rutas))


def _comprobar_destino(destino: Path, repo: Path, prohibidas: Iterable[Path]) -> None:
    if _dentro(destino, [repo.resolve()]):
        raise ValueError(f"«{destino}» está dentro del repositorio: el respaldo va fuera de él.")
    if _dentro(destino, [Path(p).resolve() for p in prohibidas]):
        raise ValueError(
            f"«{destino}» está dentro de OneDrive: el respaldo va a un disco local o externo, "
            "no a una carpeta que se sincroniza con la nube."
        )


def _podar(destino: Path, conservar: int) -> list[str]:
    """Borra los respaldos más viejos de esta herramienta (carpetas con sello y manifiesto)."""
    propios = sorted(p for p in destino.iterdir()
                     if p.is_dir() and SELLO.match(p.name) and (p / MANIFIESTO).exists())
    borrados = []
    for viejo in propios[:-conservar] if conservar > 0 else []:
        shutil.rmtree(viejo)
        borrados.append(viejo.name)
    return borrados


def respaldar(repo: Path, destino: Path, *, prohibidas: Iterable[Path] | None = None,
              sello: str | None = None, conservar: int = 5,
              extras: Mapping[str, Path] | None = None) -> Path:
    """Hace un respaldo completo en `destino/sello` y devuelve esa carpeta."""
    repo = Path(repo).resolve()
    destino = Path(destino)
    _comprobar_destino(destino, repo, onedrive() if prohibidas is None else prohibidas)
    sello = sello or datetime.now().strftime("%Y%m%d-%H%M")
    carpeta = destino / sello
    if carpeta.exists():
        raise FileExistsError(f"«{carpeta}» ya existe; no se pisa un respaldo.")
    carpeta.mkdir(parents=True)
    notas: list[str] = []

    paquete = carpeta / "repositorio.bundle"
    _git(repo, "bundle", "create", str(paquete), "--all")
    _git(repo, "bundle", "verify", str(paquete))

    todos = arboles(repo)
    nombres = _nombres(todos, repo)
    cabezas = []
    for arbol in todos:
        nombre = nombres[arbol]
        # solo se excluyen los árboles anidados DENTRO de este (el principal contiene a .worktrees/)
        otros = [a.resolve() for a in todos
                 if a.resolve() != arbol.resolve() and a.resolve().is_relative_to(arbol.resolve())]
        cabeza = _git(arbol, "rev-parse", "--short", "HEAD").decode().strip()
        rama = _git(arbol, "branch", "--show-current").decode().strip() or "sin rama"
        cabezas.append(f"{nombre}: {arbol} @ {cabeza} ({rama})")
        parche = _git(arbol, "diff", "HEAD", "--binary")
        if parche:
            (carpeta / "sin-commit").mkdir(exist_ok=True)
            (carpeta / "sin-commit" / f"{nombre}.patch").write_bytes(parche)
        nuevos = [r for r in _lista_z(_git(arbol, "ls-files", "--others", "--exclude-standard",
                                           "-z"))
                  if not _regenerable(r) and not _dentro(arbol / r, otros)]
        _copiar(arbol, nuevos, carpeta / "sin-commit" / nombre, notas)
        ignorados = _lista_z(_git(arbol, "ls-files", "--others", "--ignored", "--exclude-standard",
                                  "--directory", "-z"))
        archivos = [a for rel in ignorados
                    if not _regenerable(rel) and not _dentro(arbol / rel, otros)
                    for a in _archivos(arbol, rel, otros)]
        _copiar(arbol, archivos, carpeta / "solo-en-el-equipo" / nombre, notas)

    for nombre, origen in (extras or {}).items():
        origen = Path(origen)
        if not origen.exists():
            notas.append(f"extra «{nombre}» no encontrado: {origen}")
            continue
        if origen.is_file():
            _copiar(origen.parent, [origen.name], carpeta / "extras" / nombre, notas)
        else:
            _copiar(origen, list(_archivos(origen, ".", [])), carpeta / "extras" / nombre, notas)

    escribir_manifiesto(carpeta, [
        f"Respaldo de Sílice {sello}, hecho con scripts/respaldo_local.py",
        f"Repositorio: {repo}",
        "CONTIENE DATOS REALES: no subir a la nube ni al repositorio.",
        *[f"Árbol {c}" for c in cabezas],
        *[f"Nota: {n}" for n in notas],
    ])
    _podar(destino, conservar)
    return carpeta


def _destino_por_omision() -> Path:
    return Path("C:/RespaldoSilice") if os.name == "nt" else Path.home() / "RespaldoSilice"


def _extras_por_omision() -> dict[str, Path]:
    claude = Path.home() / ".claude"
    proyecto = "c--Users-" + Path.home().name + "-OneDrive-Escritorio-TESIS"
    escritorio = Path(os.environ.get("OneDrive", Path.home() / "OneDrive")) / "Escritorio"
    return {
        "memoria-claude": claude / "projects" / proyecto / "memory",
        # solo las skills propias: las de terceros se reinstalan
        "skill-disenar-desde-la-tarea": claude / "skills" / "disenar-desde-la-tarea",
        "skill-unslop-interfaz": claude / "skills" / "unslop-interfaz",
        "decisiones-silice": escritorio / "Decisiones Silice",
    }


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = analizador.add_subparsers(dest="orden")
    v = sub.add_parser("verificar", help="comprueba un respaldo contra su manifiesto")
    v.add_argument("carpeta")
    analizador.add_argument("--destino", default=str(_destino_por_omision()))
    analizador.add_argument("--conservar", type=int, default=5)
    analizador.add_argument("--repo", default=str(RAIZ))
    args = analizador.parse_args(argv)

    if args.orden == "verificar":
        malos = verificar(Path(args.carpeta))
        print("Respaldo sano." if not malos
              else "Archivos dañados o faltantes:\n" + "\n".join(malos))
        return 0 if not malos else 1
    repo = Path(args.repo)
    principal = arboles(repo)[0] if arboles(repo) else repo
    carpeta = respaldar(principal, Path(args.destino), conservar=args.conservar,
                        extras=_extras_por_omision())
    archivos = sum(1 for p in carpeta.rglob("*") if p.is_file())
    tamano = sum(p.stat().st_size for p in carpeta.rglob("*") if p.is_file()) / (1024 * 1024)
    print(f"Respaldo hecho en {carpeta}: {archivos} archivos, "
          f"{f'{tamano:.1f}'.replace('.', ',')} MB.")
    notas = [linea for linea in (carpeta / MANIFIESTO).read_text(encoding="utf-8").splitlines()
             if linea.startswith("# Nota:")]
    if notas:
        print("\n".join(notas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
