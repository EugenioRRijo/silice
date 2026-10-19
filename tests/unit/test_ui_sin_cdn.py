"""La interfaz clásica no pide nada fuera del equipo (RNF-08; spec S5 §10.2).

Tras retirar el Visor 3D (2026-10-19) ya no hay ninguna excepción de CDN: `ui/` no incrusta
bibliotecas de terceros ni cita hosts de CDN, y la carpeta `ui/estaticos/` (donde vivía three.js)
no existe.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CDN = re.compile(
    r"cdnjs|unpkg\.com|jsdelivr|googleapis|gstatic|<script\s+src=|<link\s", re.IGNORECASE
)


def test_ui_no_cita_ninguna_cdn_ni_carga_scripts_externos() -> None:
    citas = [
        f"{ruta.relative_to(RAIZ)}:{numero}"
        for ruta in (RAIZ / "ui").rglob("*.py")
        for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1)
        if CDN.search(linea)
    ]
    assert citas == []


def test_ui_no_trae_bibliotecas_de_terceros_incrustadas() -> None:
    assert not (RAIZ / "ui" / "estaticos").exists()
    assert list((RAIZ / "ui").rglob("*.min.js")) == []


def test_git_ya_no_declara_binario_el_three() -> None:
    atributos = (RAIZ / ".gitattributes").read_text(encoding="utf-8")
    assert "three" not in atributos
