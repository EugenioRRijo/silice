"""Genera `operacion/silice.ico` desde `frontend-desktop/public/silice.svg` (F5 ventana, V3).

    uv run --no-sync python instalador/icono.py

El SVG es la fuente única del ícono (favicon de la interfaz, ventana, accesos e instalador). Se
dibuja con Microsoft Edge sin interfaz (`--headless`, ya en Windows 10 22H2 y 11) a 1024 px y Pillow
(que trae matplotlib, extra `informes`) arma un `.ico` con 16, 24, 32, 48, 64, 128 y 256 px. Se
corre a mano solo cuando cambia el SVG; el `.ico` queda en el repositorio y viaja con `operacion/`.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SVG = RAIZ / "frontend-desktop" / "public" / "silice.svg"
ICO = RAIZ / "operacion" / "silice.ico"
TAMANOS = (16, 24, 32, 48, 64, 128, 256)
EDGE = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)


def _edge() -> Path:
    for ruta in EDGE:
        if ruta.is_file():
            return ruta
    hallado = shutil.which("msedge")
    if hallado:
        return Path(hallado)
    raise FileNotFoundError("no se encontró Microsoft Edge para dibujar el SVG")


def dibujar(svg: Path, png: Path, lado: int = 1024) -> None:
    """El SVG (256 × 256) a un PNG de `lado` px con fondo transparente."""
    escala = lado / 256
    with tempfile.TemporaryDirectory() as perfil:
        subprocess.run(  # noqa: S603
            [
                str(_edge()),
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--user-data-dir={perfil}",
                "--window-size=256,256",
                f"--force-device-scale-factor={escala:g}",
                "--default-background-color=00000000",
                f"--screenshot={png}",
                svg.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    if not png.is_file():
        raise RuntimeError("Edge no dejó la captura del SVG")


def armar_ico(png: Path, ico: Path) -> None:
    from PIL import Image

    with Image.open(png) as imagen:
        base = imagen.convert("RGBA")
    if base.size[0] != base.size[1]:
        raise RuntimeError(f"la captura no es cuadrada: {base.size}")
    ico.parent.mkdir(parents=True, exist_ok=True)
    base.save(ico, format="ICO", sizes=[(t, t) for t in TAMANOS])


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--svg", type=Path, default=SVG)
    analizador.add_argument("--salida", type=Path, default=ICO)
    argumentos = analizador.parse_args(argv)
    with tempfile.TemporaryDirectory() as carpeta:
        png = Path(carpeta) / "silice.png"
        dibujar(argumentos.svg, png)
        armar_ico(png, argumentos.salida)
    print(f"{argumentos.salida} ({', '.join(str(t) for t in TAMANOS)} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
