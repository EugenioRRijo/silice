"""Construye el instalador de Sílice (spec S5 §7.1; RF-97, RNF-20). Solo en Windows.

    uv run python instalador/construir.py --perfil basico|completo
    uv run python instalador/construir.py --perfil basico --solo-iss --version 1.0.1
    uv run python instalador/construir.py --perfil basico --solo-carpeta   # sin Inno Setup
    uv run python instalador/construir.py --perfil basico --solo-sumas \\
        --extra pip-audit-basico.json

Parte solo de `uv.lock` (`--frozen`): instalar no ejecuta un resolvedor. El resultado queda en
`build/salida/`: `Silice-<versión>[-completo].exe`, `manifiesto.json` y `SHA256SUMS-<perfil>`.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from instalador import manifiesto as mf  # noqa: E402
from instalador.medir_capas import REQUISITO as _REQUISITO  # noqa: E402
from instalador.medir_capas import normalizar as _normal  # noqa: E402
from instalador.medir_capas import paquetes_de  # noqa: E402,F401  (lo usan las pruebas)
from operacion import programa  # noqa: E402
from operacion.version import a_semver  # noqa: E402
from operacion.version import version as version_del_proyecto  # noqa: E402

Ejecutar = Callable[..., None]

# Medido el 2026-10-12: con `--compile-bytecode` el basico pesa 833,9 MB instalado y 164,2 MB
# comprimido (xz -9), sobre el limite de 150 MB de RNF-19; sin el, 649,6 MB y 125,7 MB. Los .pyc de
# los paquetes de terceros no viajan; `codigo\` si se compila (`compilar`). Cambiarlo es un ruling.
_BYTECODE: tuple[str, ...] = ()


def formatear_sumas(entradas: Mapping[str, str]) -> bytes:
    """Formato de `sha256sum`: `<hex>  <nombre>` por línea, ordenado por nombre, solo LF.

    Es el mismo formato que `operacion.firma_sumas.formatear_sumas` (Tarea 3, que genera
    Eugenio y aún no está en `main`); se duplica aquí para no depender de ella.
    """
    return "".join(f"{h}  {n}\n" for n, h in sorted(entradas.items())).encode("utf-8")


@dataclass(frozen=True)
class Rutas:
    raiz: Path = RAIZ

    @property
    def build(self) -> Path:
        return self.raiz / "build"

    @property
    def py(self) -> Path:
        return self.build / "py"

    @property
    def app(self) -> Path:
        return self.build / "app"

    @property
    def salida(self) -> Path:
        return self.build / "salida"


def _ejecutar(
    orden: Sequence[str], entorno: Mapping[str, str] | None = None, cwd: Path | None = None
) -> None:
    subprocess.run([str(p) for p in orden], env=entorno, cwd=cwd, check=True)


def solo_los_nuevos(basica: str, completa: str) -> str:
    """Las líneas de `completa` cuyo paquete la capa básica no trae (diferencia de conjuntos)."""
    ya = set(paquetes_de(basica))
    nuevas = []
    for linea in completa.splitlines():
        coincidencia = _REQUISITO.match(linea.strip())
        if coincidencia and _normal(coincidencia.group(1)) not in ya:
            nuevas.append(linea.strip())
            ya.add(_normal(coincidencia.group(1)))
    return "\n".join(nuevas) + ("\n" if nuevas else "")


def extras_de(m: mf.Manifiesto, similitud: bool) -> list[str]:
    extras = [*m.extras_basica, *(["ifc"] if m.ifc else [])]
    return [*extras, *m.extras_similitud] if similitud else extras


def exportar(extras: Sequence[str], salida: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    pares = [parte for extra in extras for parte in ("--extra", extra)]
    ejecutar(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            *pares,
            "--output-file",
            str(salida),
        ]
    )


def instalar_python(version: str, rutas: Rutas, ejecutar: Ejecutar = _ejecutar) -> Path:
    ejecutar(["uv", "python", "install", version, "--install-dir", str(rutas.py)])
    candidatos = sorted(rutas.py.glob(f"cpython-{version}-*/python.exe"))
    if not candidatos:
        raise FileNotFoundError(f"uv no dejó un python.exe de {version} en {rutas.py}")
    destino = rutas.app / "python"
    shutil.copytree(candidatos[0].parent, destino)
    return destino / "python.exe"


def instalar_capa(python: Path, requisitos: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    ejecutar(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--break-system-packages",
            *_BYTECODE,
            "--no-deps",
            "-r",
            str(requisitos),
        ]
    )


def instalar_similitud(
    python: Path, requisitos: Path, destino: Path, ejecutar: Ejecutar = _ejecutar
) -> None:
    ejecutar(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--target",
            str(destino),
            "--no-deps",
            *_BYTECODE,
            "-r",
            str(requisitos),
        ]
    )


def escribir_pth(app: Path) -> None:
    """`site` une cada línea de un .pth a su carpeta (`python\\Lib\\site-packages`): tres `..`
    llegan a `{app}`. El Inno lo instala solo con el componente de similitud."""
    (app / "silice_similitud.pth").write_text(
        "..\\..\\..\\modulos\\similitud\\paquetes\n", encoding="utf-8"
    )


def descargar_modelo(python: Path, app: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    from ml.normalization import MODELO_POR_DEFECTO

    similitud = app / "modulos" / "similitud"
    entorno = {
        **os.environ,
        "HF_HOME": str(similitud / "hf"),
        "PYTHONPATH": str(similitud / "paquetes"),
    }
    entorno.pop("HF_HUB_OFFLINE", None)
    ejecutar(
        [
            str(python),
            "-s",
            "-c",
            "from sentence_transformers import SentenceTransformer as S; "
            f"S({MODELO_POR_DEFECTO!r})",
        ],
        entorno,
    )


def licencias(python: Path, app: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    """Corre `licencias.py` con el Python construido, aislado (`-E -s`) y mirando solo sus
    carpetas: sin esto entrarían los paquetes del usuario que construye."""
    sitio = app / "python" / "Lib" / "site-packages"
    paquetes = app / "modulos" / "similitud" / "paquetes"
    carpetas = [sitio, *([paquetes] if paquetes.is_dir() else [])]
    ejecutar(
        [
            str(python),
            "-E",
            "-s",
            str(RAIZ / "instalador" / "licencias.py"),
            "--salida",
            str(app / "LICENCIAS"),
            *[parte for c in carpetas for parte in ("--solo-ruta", str(c))],
        ]
    )
    shutil.copyfile(RAIZ / "LICENSE", app / "LICENCIAS" / "Silice-LICENSE.txt")


def copiar_codigo(m: mf.Manifiesto, destino: Path) -> None:
    mf.armar_arbol(RAIZ, destino, m)


def compilar(python: Path, codigo: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    ejecutar([str(python), "-m", "compileall", "-q", "-j", "0", str(codigo)])


def escribir_manifiesto_json(app: Path, version: str) -> Path:
    relativas = [p.relative_to(app) for p in (app / "codigo").rglob("*") if p.is_file()]
    return programa.escribir(app, [*relativas, Path("python/python.exe")], version)


def asegurar_bom(origen: Path, destino: Path) -> Path:
    """Inno Setup lee un .iss UTF-8 solo si trae BOM; sin él, rompe «Sílice»."""
    datos = origen.read_bytes()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos if datos.startswith(b"\xef\xbb\xbf") else b"\xef\xbb\xbf" + datos)
    return destino


def buscar_iscc(
    entorno: Mapping[str, str] | None = None, existe: Callable[[Path], bool] = Path.is_file
) -> Path:
    env = os.environ if entorno is None else entorno
    candidatas = [Path(p) / "ISCC.exe" for p in env.get("PATH", "").split(os.pathsep) if p]
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        if env.get(variable):
            base = Path(env[variable]) / ("Programs" if variable == "LOCALAPPDATA" else "")
            candidatas += [base / "Inno Setup 6" / "ISCC.exe", base / "Inno Setup 7" / "ISCC.exe"]
    for candidata in candidatas:
        if existe(candidata):
            return candidata
    raise FileNotFoundError(
        "No se encontró ISCC.exe de Inno Setup. Instálelo con "
        "`winget install --id JRSoftware.InnoSetup -e` y vuelva a intentar."
    )


def tamanos_de_la_carpeta(app: Path, perfil: str) -> list[str]:
    """Líneas legibles con el tamaño sin comprimir de `build\\app` y de cada parte grande."""

    def total(carpeta: Path) -> int:
        return sum(p.stat().st_size for p in carpeta.rglob("*") if p.is_file())

    partes = ["python", "codigo", "LICENCIAS", "modulos"]
    lineas = [f"carpeta {perfil}: {total(app) / 1_000_000:.1f} MB sin comprimir"]
    lineas += [
        f"  {parte}: {total(app / parte) / 1_000_000:.1f} MB"
        for parte in partes
        if (app / parte).is_dir()
    ]
    return lineas


def nombre_instalador(version: str, perfil: str) -> str:
    return f"Silice-{version}{'-completo' if perfil == 'completo' else ''}.exe"


def comando_iscc(iscc: Path, iss: Path, version: str, perfil: str, rutas: Rutas) -> list[str]:
    # El perfil completo se marca con un símbolo sin valor (`#ifdef Completo`): ISPP no tiene que
    # adivinar si «completo» es una cadena.
    return [
        str(iscc),
        f"/DVersion={version}",
        *(["/DCompleto"] if perfil == "completo" else []),
        f"/DOrg={rutas.app}",
        f"/DSalida={rutas.salida}",
        f"/DRaiz={rutas.raiz}",
        str(iss),
    ]


def escribir_sumas(carpeta: Path, perfil: str, nombres: Sequence[str]) -> Path:
    entradas = {n: hashlib.sha256((carpeta / n).read_bytes()).hexdigest() for n in nombres}
    destino = carpeta / f"SHA256SUMS-{perfil}"
    destino.write_bytes(formatear_sumas(entradas))
    return destino


def construir(
    perfil: str,
    *,
    version: str | None = None,
    solo_iss: bool = False,
    solo_carpeta: bool = False,
    rutas: Rutas | None = None,
    ejecutar: Ejecutar = _ejecutar,
) -> list[Path]:
    rutas = rutas or Rutas()
    m = mf.cargar()
    semver = version or a_semver(version_del_proyecto())
    rutas.salida.mkdir(parents=True, exist_ok=True)
    if not solo_iss:
        shutil.rmtree(rutas.app, ignore_errors=True)
        python = instalar_python(m.python, rutas, ejecutar)
        basica = rutas.build / "req-basica.txt"
        exportar(extras_de(m, similitud=False), basica, ejecutar)
        instalar_capa(python, basica, ejecutar)
        if perfil == "completo":
            completa, nuevos = rutas.build / "req-completa.txt", rutas.build / "req-similitud.txt"
            exportar(extras_de(m, similitud=True), completa, ejecutar)
            nuevos.write_text(
                solo_los_nuevos(basica.read_text("utf-8"), completa.read_text("utf-8")), "utf-8"
            )
            instalar_similitud(
                python, nuevos, rutas.app / "modulos" / "similitud" / "paquetes", ejecutar
            )
            escribir_pth(rutas.app)
            descargar_modelo(python, rutas.app, ejecutar)
        copiar_codigo(m, rutas.app / "codigo")
        compilar(python, rutas.app / "codigo", ejecutar)
        licencias(python, rutas.app, ejecutar)
        escribir_manifiesto_json(rutas.app, semver)
    if solo_carpeta:
        # Sin Inno Setup: la carpeta `build/app` queda lista y se reportan sus tamaños.
        return [rutas.app]
    iss = asegurar_bom(RAIZ / "instalador" / "silice.iss", rutas.build / "silice.iss")
    ejecutar(comando_iscc(buscar_iscc(), iss, semver, perfil, rutas), None, RAIZ)
    if (rutas.app / "manifiesto.json").is_file():
        shutil.copyfile(rutas.app / "manifiesto.json", rutas.salida / "manifiesto.json")
    sumas = escribir_sumas(
        rutas.salida, perfil, [nombre_instalador(semver, perfil), "manifiesto.json"]
    )
    return [rutas.salida / nombre_instalador(semver, perfil), sumas]


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--perfil", required=True, choices=["basico", "completo"])
    analizador.add_argument("--version", help="SemVer; por defecto la de pyproject.toml")
    analizador.add_argument(
        "--solo-iss", action="store_true", help="recompila sin reconstruir el árbol"
    )
    analizador.add_argument(
        "--solo-carpeta",
        action="store_true",
        help="arma build/app y reporta tamaños, sin compilar Inno Setup",
    )
    analizador.add_argument(
        "--solo-sumas", action="store_true", help="regenera SHA256SUMS-<perfil>"
    )
    analizador.add_argument(
        "--extra", action="append", default=[], help="archivo más para las sumas"
    )
    argumentos = analizador.parse_args(argv)
    rutas = Rutas()
    semver = argumentos.version or a_semver(version_del_proyecto())
    if argumentos.solo_sumas:
        nombres = [
            nombre_instalador(semver, argumentos.perfil),
            "manifiesto.json",
            *argumentos.extra,
        ]
        print(escribir_sumas(rutas.salida, argumentos.perfil, nombres))
        return 0
    for salida in construir(
        argumentos.perfil,
        version=argumentos.version,
        solo_iss=argumentos.solo_iss,
        solo_carpeta=argumentos.solo_carpeta,
    ):
        print(salida)
    if argumentos.solo_carpeta:
        for linea in tamanos_de_la_carpeta(rutas.app, argumentos.perfil):
            print(linea)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
