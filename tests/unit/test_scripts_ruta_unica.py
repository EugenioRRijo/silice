"""INV-044 (scripts): la ruta de trabajo `data/apu.db` se define una sola vez en `scripts/`.

La fuente unica es `scripts.seed.RUTA_POR_DEFECTO`; los demas scripts la importan. Se busca el
literal en asignaciones (`NOMBRE = "data/apu.db"`) y en `default="data/apu.db"` de argparse, que
son las dos formas en que un script la redefine. `ui/caso.py` conserva su propia definicion,
parchable en las pruebas (dictamen C3-6), y queda fuera de este criterio porque no esta en
`scripts/`.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_SCRIPTS = RAIZ / "scripts"
FUENTE_UNICA = CARPETA_SCRIPTS / "seed.py"

#: Una asignacion (`X = "data/apu.db"`, con o sin anotacion) o un `default="data/apu.db"`.
_DEFINICION = re.compile(
    r"(?:^\s*[A-Za-z_]\w*(?:\s*:\s*[^=]+)?\s*=|\bdefault\s*=)"  # asignacion o default=
    r"""\s*["']data/apu\.db["']"""
)


def _definiciones(archivo: Path) -> list[int]:
    lineas = archivo.read_text(encoding="utf-8").splitlines()
    return [numero for numero, linea in enumerate(lineas, start=1) if _DEFINICION.search(linea)]


def test_la_ruta_de_trabajo_se_define_una_vez_en_scripts() -> None:
    redefiniciones = [
        f"{archivo.relative_to(RAIZ).as_posix()}:{numero}"
        for archivo in sorted(CARPETA_SCRIPTS.glob("*.py"))
        if archivo != FUENTE_UNICA
        for numero in _definiciones(archivo)
    ]
    assert redefiniciones == [], (
        "la ruta data/apu.db se redefine fuera de scripts.seed.RUTA_POR_DEFECTO: "
        + ", ".join(redefiniciones)
    )


def test_la_fuente_unica_define_la_ruta() -> None:
    # Guarda del criterio: si el patron dejara de reconocer la definicion, la prueba anterior
    # pasaria en vacio.
    assert len(_definiciones(FUENTE_UNICA)) == 1
