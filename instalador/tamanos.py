"""Tamaño de los instaladores contra RNF-19 (spec S5 §4.3 y §11.2). 1 MB = 1 000 000 de bytes
(RP10-6): es la lectura con menos margen."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

MB = 1_000_000
LIMITES = {"basico": 150 * MB, "completo": 650 * MB}


def evaluar(perfil: str, bytes_: int) -> tuple[bool, str]:
    if perfil not in LIMITES:
        raise ValueError(f"perfil desconocido: {perfil!r}; válidos: {', '.join(LIMITES)}")
    limite = LIMITES[perfil]
    ok = 0 < bytes_ <= limite
    return ok, f"{perfil}: {bytes_ / MB:.1f} MB de {limite / MB:.0f} MB " + (
        "(cumple)" if ok else "(NO cumple)"
    )


def _nombre(version: str, perfil: str) -> str:
    return f"Silice-{version}{'-completo' if perfil == 'completo' else ''}.exe"


def _commit() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    resultado = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return resultado.stdout.strip() or "desconocido"


def medir(carpeta: Path, version: str, perfil: str) -> dict:
    exe = carpeta / _nombre(version, perfil)
    if not exe.is_file():
        raise FileNotFoundError(f"no existe {exe.name} en {carpeta}")
    bytes_ = exe.stat().st_size
    ok, mensaje = evaluar(perfil, bytes_)
    return {
        "perfil": perfil,
        "version": version,
        "archivo": exe.name,
        "bytes": bytes_,
        "limite": LIMITES[perfil],
        "ok": ok,
        "mensaje": mensaje,
        "commit": _commit(),
    }


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--perfil", required=True, choices=list(LIMITES))
    analizador.add_argument("--carpeta", required=True, type=Path)
    analizador.add_argument("--version", required=True)
    analizador.add_argument("--salida", type=Path)
    argumentos = analizador.parse_args(argv)
    datos = medir(argumentos.carpeta, argumentos.version, argumentos.perfil)
    if argumentos.salida:
        argumentos.salida.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    print(datos["mensaje"])
    return 0 if datos["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
