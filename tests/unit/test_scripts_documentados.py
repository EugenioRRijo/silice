"""INV-051: cada script de `scripts/` tiene su fila en `scripts/README.md`.

Criterio declarado (QA-14): todo `scripts/*.py` **salvo `scripts/__init__.py`** aparece en la tabla
del README como una celda que empieza con su nombre entre comillas invertidas. `__init__.py` es el
paquete y lo documenta su propio docstring.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_SCRIPTS = RAIZ / "scripts"
README = CARPETA_SCRIPTS / "README.md"

#: La primera celda de una fila de la tabla: `| `nombre.py` |`.
_FILA = re.compile(r"^\|\s*`([^`]+\.py)`\s*\|", re.MULTILINE)


def _documentados() -> set[str]:
    return set(_FILA.findall(README.read_text(encoding="utf-8")))


def test_cada_script_tiene_su_fila_en_el_readme() -> None:
    scripts = {archivo.name for archivo in CARPETA_SCRIPTS.glob("*.py")} - {"__init__.py"}
    faltan = sorted(scripts - _documentados())
    assert faltan == [], f"{len(faltan)} script(s) sin fila en scripts/README.md: {faltan}"


def test_el_readme_no_documenta_scripts_que_no_existen() -> None:
    sobran = sorted(n for n in _documentados() if not (CARPETA_SCRIPTS / n).is_file())
    assert sobran == []
