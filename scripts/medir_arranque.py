"""Mide RNF-19: del acceso directo a la salud 200 (spec S5 §4.3). Mediana de cinco, como RNF-11.

    uv run python scripts/medir_arranque.py [--python <python.exe de un Sílice instalado>]

Una corrida de calentamiento (crea las bases; se descarta) y cinco medidas de
`python -m operacion arrancar --sin-navegador` hasta que `/_stcore/health` responde 200. Usa una
carpeta de datos temporal y un puerto libre: no toca ningún dato real. Deja
`scripts/_salida_arranque.json` y, con `--tabla`, imprime el bloque para plan_pruebas §10.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion import config  # noqa: E402

LIMITE_S = 20.0
BANDERAS = ["-E", "-s", "-B", "-X", "utf8", "-m", "operacion"]


def resumen(valores: Sequence[float]) -> dict:
    if len(valores) != 5:
        raise ValueError(f"se miden exactamente cinco valores, no {len(valores)}")
    redondeados = [round(float(v), 2) for v in valores]
    return {"mediana_s": round(statistics.median(redondeados), 2), "valores_s": redondeados}


def tabla_markdown(datos: dict) -> str:
    coma = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
    valores = "; ".join(coma(v) for v in datos["valores_s"])
    return (
        "### Medición de arranque (RNF‑19)\n\n"
        f"{datos['fecha']}, {datos['equipo']}: {valores} s; mediana {coma(datos['mediana_s'])} s "
        f"frente al umbral de {int(LIMITE_S)} s en el equipo de desarrollo.\n"
    )


def _puerto_libre() -> int:
    with socket.socket() as zocalo:
        zocalo.bind(("127.0.0.1", 0))
        return int(zocalo.getsockname()[1])


def _salud(puerto: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/_stcore/health", timeout=1) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def una_vez(python: Path, cwd: Path, puerto: int, entorno: dict[str, str]) -> float:
    inicio = time.monotonic()
    servidor = subprocess.Popen(
        [str(python), *BANDERAS, "arrancar", "--sin-navegador"],
        cwd=cwd,
        env=entorno,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        while time.monotonic() - inicio < 120:
            if _salud(puerto):
                return time.monotonic() - inicio
            if servidor.poll() is not None:
                raise RuntimeError("Sílice terminó antes de responder la salud")
            time.sleep(0.1)
        raise TimeoutError("la salud no respondió en 120 s")
    finally:
        subprocess.run(
            [str(python), *BANDERAS, "parar"], cwd=cwd, env=entorno, check=False, timeout=60
        )
        try:
            servidor.wait(timeout=30)
        except subprocess.TimeoutExpired:
            servidor.terminate()  # solo el hijo que este mismo script lanzó


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--python", type=Path, default=Path(sys.executable))
    analizador.add_argument("--cwd", type=Path, default=RAIZ)
    analizador.add_argument(
        "--salida", type=Path, default=RAIZ / "scripts" / "_salida_arranque.json"
    )
    analizador.add_argument(
        "--tabla", action="store_true", help="imprime el bloque de plan_pruebas"
    )
    argumentos = analizador.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows (cp1252) no trae U+2011
    with tempfile.TemporaryDirectory() as carpeta:
        puerto = _puerto_libre()
        entorno = {
            "SILICE_DATOS": carpeta,
            "SILICE_USUARIO": carpeta,
            **{
                k: v
                for k, v in os.environ.items()
                if not k.upper().startswith(("PYTHON", "SILICE_"))
            },
        }
        config.guardar_ajustes(
            Path(carpeta) / "config" / "silice.toml", config.Ajustes(puerto=puerto)
        )
        una_vez(argumentos.python, argumentos.cwd, puerto, entorno)  # calentamiento: crea las bases
        valores = [una_vez(argumentos.python, argumentos.cwd, puerto, entorno) for _ in range(5)]
    datos = {
        **resumen(valores),
        "fecha": date.today().isoformat(),
        "equipo": platform.platform(),
        "python": platform.python_version(),
        "instalado": config.es_producto(argumentos.cwd / "codigo")
        or config.es_producto(argumentos.cwd),
    }
    argumentos.salida.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    print(tabla_markdown(datos) if argumentos.tabla else json.dumps(datos))
    return 0 if datos["mediana_s"] <= LIMITE_S else 1


if __name__ == "__main__":
    raise SystemExit(main())
