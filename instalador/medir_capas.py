"""Mide el Python autónomo y cada capa del instalador (spec S5 §1.3 y S5-0.3).

    uv run python instalador/medir_capas.py --tabla

Instala en una copia desechable del Python 3.13 de `uv` todo lo que el instalador completo llevaría
(capa por capa, desde `uv.lock`), suma el tamaño de cada paquete desde su `RECORD` y estima lo que
daría LZMA2 con `tar | xz -9`. Deja `docs/bitacora/2026-10-silice-100-capas.json` y, con `--tabla`,
el cuadro de §1.3 en Markdown. Necesita internet y unos 4 GB libres; no toca el repositorio.
"""

from __future__ import annotations

import argparse
import csv
import json
import lzma
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REQUISITO = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._\-]*)==([^\s;]+)")
MB = 1_000_000
LIMITE_BASICO_MB = 150.0
FIJAS = ("basica", "bcv", "civil", "anomalias", "ia")
ORDEN_DE_RECORTE = ("civil", "anomalias")
#: capa -> extras acumulados (el spec §7.2: «base + ui + api + planos + informes», luego cada extra)
CAPAS: dict[str, list[str]] = {
    "base": [],
    "basica": ["ui", "api", "planos", "informes"],
    "bcv": ["ui", "api", "planos", "informes", "bcv"],
    "civil": ["ui", "api", "planos", "informes", "bcv", "civil"],
    "anomalias": ["ui", "api", "planos", "informes", "bcv", "civil", "anomalias"],
    "ia": ["ui", "api", "planos", "informes", "bcv", "civil", "anomalias", "ia"],
    "similitud": [
        "ui",
        "api",
        "planos",
        "informes",
        "bcv",
        "civil",
        "anomalias",
        "ia",
        "similitud",
    ],
}


def normalizar(nombre: str) -> str:
    return re.sub(r"[-_.]+", "-", nombre).lower()


def paquetes_de(requisitos: str) -> dict[str, str]:
    encontrados = {}
    for linea in requisitos.splitlines():
        coincidencia = REQUISITO.match(linea.strip())
        if coincidencia:
            encontrados[normalizar(coincidencia.group(1))] = coincidencia.group(2)
    return encontrados


def capas_nuevas(exportaciones: Mapping[str, str]) -> dict[str, set[str]]:
    """Por capa (en el orden del diccionario), los paquetes que las anteriores no traían."""
    vistos: set[str] = set()
    capas = {}
    for capa, requisitos in exportaciones.items():
        nombres = set(paquetes_de(requisitos))
        capas[capa] = nombres - vistos
        vistos |= nombres
    return capas


def _archivos_de(sitio: Path, dist_info: Path) -> list[Path]:
    registro = dist_info / "RECORD"
    if not registro.is_file():
        return []
    archivos = []
    with registro.open(encoding="utf-8", newline="") as flujo:
        for fila in csv.reader(flujo):
            if not fila or fila[0].startswith(".."):
                continue
            ruta = sitio / fila[0]
            if ruta.is_file() and ruta.name != "RECORD":
                archivos.append(ruta)
    return archivos


def tamano_de_dist_info(sitio: Path, dist_info: Path) -> int:
    return sum(p.stat().st_size for p in _archivos_de(sitio, dist_info))


class _ContadorXz:
    def __init__(self) -> None:
        self._compresor = lzma.LZMACompressor(format=lzma.FORMAT_XZ, preset=9)
        self.total = 0

    def write(self, datos: bytes) -> int:
        self.total += len(self._compresor.compress(datos))
        return len(datos)

    def cerrar(self) -> int:
        self.total += len(self._compresor.flush())
        return self.total


def estimar_xz(archivos: Iterable[Path]) -> int:
    """Bytes que daría `tar | xz -9` de esos archivos (la estimación del spec §1.3)."""
    contador = _ContadorXz()
    with tarfile.open(fileobj=contador, mode="w|") as tar:  # type: ignore[arg-type]
        for archivo in archivos:
            tar.add(archivo, arcname=archivo.name, recursive=False)
    return contador.cerrar()


def decidir_recorte(
    python_mb: float,
    capas_mb: Mapping[str, float],
    codigo_mb: float = 7.0,
    limite: float = LIMITE_BASICO_MB,
) -> list[str]:
    """Qué capas pasarían a opcionales para que el básico quepa: primero `civil`, luego
    `anomalias` (spec S5 §7.2). `ValueError` si ni así cabe."""
    total = python_mb + codigo_mb + sum(capas_mb[c] for c in FIJAS)
    recortes: list[str] = []
    for capa in ORDEN_DE_RECORTE:
        if total <= limite:
            break
        total -= capas_mb[capa]
        recortes.append(capa)
    if total > limite:
        raise ValueError(
            f"ni recortando {', '.join(ORDEN_DE_RECORTE)} cabe en {limite:.0f} MB ({total:.1f})"
        )
    return recortes


def tabla_markdown(datos: Mapping) -> str:
    coma = lambda v: f"{v:.1f}".replace(".", ",")  # noqa: E731
    filas = [
        "| Capa | Paquetes | Instalado (MB) | Comprimido, xz ‑9 (MB) |",
        "|---|---|---|---|",
        f"| Python autónomo | — | {coma(datos['python']['instalado_mb'])} "
        f"| {coma(datos['python']['comprimido_mb'])} |",
    ]
    total = datos["python"]["comprimido_mb"]
    for capa, d in datos["capas"].items():
        filas.append(
            f"| {capa} | {d['paquetes']} | {coma(d['instalado_mb'])} | {coma(d['comprimido_mb'])} |"
        )
        total += d["comprimido_mb"]
    recorte = ", ".join(datos["recorte"]) or "ninguno"
    filas += ["", f"Total comprimido (estimado xz -9): {coma(total)} MB. Recorte: {recorte}."]
    return "\n".join(filas)


def _correr(orden: Sequence[str]) -> str:
    return subprocess.run(list(orden), capture_output=True, text=True, check=True, cwd=RAIZ).stdout


def medir(version_python: str) -> dict:
    with tempfile.TemporaryDirectory() as carpeta:
        base = Path(carpeta)
        _correr(["uv", "python", "install", version_python, "--install-dir", str(base / "py")])
        origen = next((base / "py").glob(f"cpython-{version_python}-*"))
        copia = base / "python"
        shutil.copytree(origen, copia)
        exe = copia / "python.exe" if sys.platform == "win32" else copia / "bin" / "python3"
        python_archivos = [p for p in copia.rglob("*") if p.is_file()]
        resultado: dict = {
            "python": {
                "version": version_python,
                "instalado_mb": sum(p.stat().st_size for p in python_archivos) / MB,
                "comprimido_mb": estimar_xz(python_archivos) / MB,
            },
            "capas": {},
        }
        exportaciones = {}
        for capa, extras in CAPAS.items():
            pares = [x for e in extras for x in ("--extra", e)]
            exportaciones[capa] = _correr(
                ["uv", "export", "--frozen", "--no-dev", "--no-emit-project", "--no-hashes", *pares]
            )
        completa = base / "req-completa.txt"
        completa.write_text(exportaciones["similitud"], encoding="utf-8")
        _correr(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(exe),
                "--break-system-packages",
                "--no-deps",
                "-r",
                str(completa),
            ]
        )
        sitio = next(copia.rglob("site-packages"))
        por_capa = capas_nuevas(exportaciones)
        for capa, nombres in por_capa.items():
            archivos: list[Path] = []
            for info in sitio.glob("*.dist-info"):
                if normalizar(info.name.removesuffix(".dist-info").rsplit("-", 1)[0]) in nombres:
                    archivos += _archivos_de(sitio, info)
            resultado["capas"][capa] = {
                "paquetes": len(nombres),
                "instalado_mb": sum(p.stat().st_size for p in archivos) / MB,
                "comprimido_mb": estimar_xz(archivos) / MB,
            }
    mb = {c: d["comprimido_mb"] for c, d in resultado["capas"].items()}
    mb["basica"] += mb["base"]  # la «básica» del spec es la base más ui, api, planos e informes
    resultado["recorte"] = decidir_recorte(resultado["python"]["comprimido_mb"], mb)
    return resultado


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--python", default="3.13.13")
    analizador.add_argument(
        "--salida", type=Path, default=RAIZ / "docs/bitacora/2026-10-silice-100-capas.json"
    )
    analizador.add_argument("--tabla", action="store_true")
    argumentos = analizador.parse_args(argv)
    datos = medir(argumentos.python)
    argumentos.salida.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(tabla_markdown(datos) if argumentos.tabla else json.dumps(datos, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
