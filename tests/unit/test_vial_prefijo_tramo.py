"""El prefijo del origen de una cantidad derivada de un tramo se define una sola vez (árbitro xhigh del
2026-11-13, ronda 2, M8): en `adapters/vial/modelo.py`, y lo importan la derivación, las reglas
viales y la Hoja; nadie lo escribe como literal."""

from __future__ import annotations

import re
from pathlib import Path

from adapters.vial import modelo, reglas
from aplicacion import hoja_partidas, hoja_vial

RAIZ = Path(__file__).resolve().parents[2]


def test_una_sola_definicion_del_prefijo() -> None:
    assert modelo.PREFIJO_TRAMO == "tramo:"
    assert reglas.PREFIJO_TRAMO is modelo.PREFIJO_TRAMO
    assert hoja_partidas.PREFIJO_TRAMO is modelo.PREFIJO_TRAMO
    assert hoja_vial.PREFIJO_TRAMO is modelo.PREFIJO_TRAMO


def test_nadie_escribe_el_prefijo_como_literal() -> None:
    literal = re.compile(r"""(f?["'])tramo:""")
    fuera = [
        f"{ruta.relative_to(RAIZ)}:{n}"
        for carpeta in ("adapters", "aplicacion", "api", "fusion")
        for ruta in (RAIZ / carpeta).rglob("*.py")
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1)
        if literal.search(linea) and "PREFIJO_TRAMO =" not in linea
    ]
    assert fuera == []
