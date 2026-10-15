"""Arma el release: un solo `SHA256SUMS` de ambos perfiles, listo para firmar (RP10-9).

    uv run python instalador/publicar.py reunir publicacion/basico publicacion/completo \
        --salida publicacion/release
    uv run python instalador/publicar.py comprobar publicacion/basico publicacion/completo
    git diff --name-only v1.0.0-rc.1..HEAD | uv run python instalador/publicar.py cambios

`reunir` copia los artefactos de cada perfil (bajados con `gh run download`) a una carpeta, verifica
que el `manifiesto.json` sea el mismo y escribe `SHA256SUMS` (sha256sum, dos espacios, solo LF).
La firma la pone el controlador en su equipo: `python -m operacion firmar-sumas`.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion import firma_sumas  # noqa: E402

#: Lo único que puede cambiar entre `v1.0.0-rc.N` y `v1.0.0` (spec S5 §9.3, RP10-13).
PERMITIDOS = ("pyproject.toml", "uv.lock", "CHANGELOG.md", "README.md")
PREFIJOS_PERMITIDOS = ("docs/",)


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def cambios_permitidos(archivos: Iterable[str]) -> list[str]:
    """Los archivos cambiados que NO deberían haber cambiado entre la candidata y la final."""
    return sorted(
        a
        for a in (x.strip().replace("\\", "/") for x in archivos)
        if a
        if a not in PERMITIDOS and not a.startswith(PREFIJOS_PERMITIDOS)
    )


def reunir(carpetas: Sequence[Path], salida: Path) -> Path:
    salida.mkdir(parents=True, exist_ok=True)
    entradas: dict[str, str] = {}
    for carpeta in carpetas:
        for archivo in sorted(carpeta.iterdir()):
            if not archivo.is_file() or archivo.name.startswith("SHA256SUMS"):
                continue
            huella = _sha256(archivo)
            if archivo.name in entradas and entradas[archivo.name] != huella:
                raise ValueError(f"{archivo.name} es distinto en dos perfiles; no puede haber dos")
            entradas[archivo.name] = huella
            shutil.copyfile(archivo, salida / archivo.name)
    sumas = salida / "SHA256SUMS"
    sumas.write_bytes(firma_sumas.formatear_sumas(entradas))
    return sumas


def comprobar_contra_ci(carpetas: Sequence[Path]) -> list[str]:
    """Cada archivo bajado coincide con el `SHA256SUMS-<perfil>` que dejó la CI."""
    problemas = []
    for carpeta in carpetas:
        for sumas in carpeta.glob("SHA256SUMS-*"):
            for nombre, huella in firma_sumas.parsear_sumas(sumas.read_bytes()).items():
                archivo = carpeta / nombre
                if not archivo.is_file():
                    problemas.append(f"{carpeta.name}: falta {nombre}")
                elif _sha256(archivo) != huella:
                    problemas.append(f"{carpeta.name}: {nombre} no coincide con lo que dejó la CI")
    return problemas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ordenes = analizador.add_subparsers(dest="orden", required=True)
    for nombre in ("reunir", "comprobar"):
        sub = ordenes.add_parser(nombre)
        sub.add_argument("carpetas", nargs="+", type=Path)
        if nombre == "reunir":
            sub.add_argument("--salida", type=Path, required=True)
    ordenes.add_parser("cambios")
    argumentos = analizador.parse_args(argv)
    if argumentos.orden == "cambios":
        ofensores = cambios_permitidos(sys.stdin.read().splitlines())
        print("\n".join(ofensores) or "solo cambian la versión, el CHANGELOG y los documentos")
        return 1 if ofensores else 0
    problemas = comprobar_contra_ci(argumentos.carpetas)
    if problemas:
        print("\n".join(problemas), file=sys.stderr)
        return 1
    if argumentos.orden == "reunir":
        print(reunir(argumentos.carpetas, argumentos.salida))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
