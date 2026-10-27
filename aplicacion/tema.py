"""Tema de la empresa: colores y logo leídos de `<datos>/tema/` (rediseño del marco, Tarea 1).

El repositorio lleva un tema neutro; nombre, logo y paleta de la empresa viven fuera de él. Esta
lectura nunca falla: un `tema.json` ausente, ilegible o con otra forma, un color que no es
`#rrggbb`, un logo de más de 512 KB o en un formato no admitido (el SVG puede llevar scripts) se
descartan y quedan en `None` / `False`, que el front traduce al tema neutro.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

NOMBRE_CARPETA = "tema"
ARCHIVO_JSON = "tema.json"
TOPE_LOGO = 512 * 1024
#: Nombre de archivo -> tipo de imagen. Nunca SVG.
LOGOS = {"logo.png": "image/png", "logo.jpg": "image/jpeg", "logo.webp": "image/webp"}
_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


@dataclass(frozen=True)
class Tema:
    acento: str | None
    marco: str | None
    lateral: str | None
    tiene_logo: bool


def _color(valor: object) -> str | None:
    return valor if isinstance(valor, str) and _COLOR.fullmatch(valor) else None


def _colores(carpeta: Path) -> dict:
    try:
        datos = json.loads((carpeta / ARCHIVO_JSON).read_text(encoding="utf-8"))
    except (OSError, ValueError):  # ausente, ilegible, no UTF-8 o JSON roto
        return {}
    return datos if isinstance(datos, dict) else {}


def _cabe(archivo: Path) -> bool:
    try:
        return archivo.is_file() and archivo.stat().st_size <= TOPE_LOGO
    except OSError:
        return False


def logo_de(carpeta: Path) -> tuple[Path, str] | None:
    """El archivo del logo y su tipo, o `None` si no hay uno admitido y dentro del tope."""
    for nombre, tipo in LOGOS.items():
        if _cabe(carpeta / nombre):
            return carpeta / nombre, tipo
    return None


def leer_tema(carpeta: Path) -> Tema:
    colores = _colores(carpeta)
    return Tema(
        acento=_color(colores.get("acento")),
        marco=_color(colores.get("marco")),
        lateral=_color(colores.get("lateral")),
        tiene_logo=logo_de(carpeta) is not None,
    )
