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
TOPE_JSON = 64 * 1024
#: Nombre de archivo -> tipo de imagen. Nunca SVG.
LOGOS = {"logo.png": "image/png", "logo.jpg": "image/jpeg", "logo.webp": "image/webp"}
_FIRMAS = {
    "image/png": re.compile(rb"\x89PNG\r\n\x1a\n"),
    "image/jpeg": re.compile(rb"\xff\xd8\xff"),
    "image/webp": re.compile(rb"RIFF.{4}WEBP", re.DOTALL),
}
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
    archivo = carpeta / ARCHIVO_JSON
    try:
        if archivo.stat().st_size > TOPE_JSON:
            return {}
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):  # ausente, ilegible, roto o muy anidado
        return {}
    return datos if isinstance(datos, dict) else {}


def leer_logo(carpeta: Path) -> tuple[bytes, str] | None:
    """Los bytes del logo y su tipo, o `None` si no hay uno admitido, dentro del tope y con la
    firma de su formato. Lee a lo sumo `TOPE_LOGO + 1` bytes: un archivo que crece no se cuela."""
    for nombre, tipo in LOGOS.items():
        try:
            with (carpeta / nombre).open("rb") as f:
                contenido = f.read(TOPE_LOGO + 1)
        except OSError:  # ausente, carpeta o ilegible
            continue
        if len(contenido) <= TOPE_LOGO and _FIRMAS[tipo].match(contenido):
            return contenido, tipo
    return None


def leer_tema(carpeta: Path) -> Tema:
    colores = _colores(carpeta)
    return Tema(
        acento=_color(colores.get("acento")),
        marco=_color(colores.get("marco")),
        lateral=_color(colores.get("lateral")),
        tiene_logo=leer_logo(carpeta) is not None,
    )
