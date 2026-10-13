"""Lo del flujo del instalador que no depende de `instalador.yml` (spec S5 §11.2; T17).

`.github/workflows/instalador.yml` no está en `main` (PR #79 sin fusionar: toca workflows y lo
fusiona Eugenio). Las pruebas del plan que leen ese flujo no aplican todavía; tampoco la de
`--hasta S5-4` en `ci.yml`, que la bitácora liga a T18. Queda lo que el plan exige de `ci.yml`
para que los dos flujos compartan herramientas: `uv` 0.11.9 y acciones a versión exacta.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
TEXTO_CI = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
CI = yaml.safe_load(TEXTO_CI)


def test_las_acciones_de_ci_estan_fijadas_a_una_version() -> None:
    """El criterio del plan (T17): `@vN` o `@vN.N.N`, nunca una rama ni `@main`; setup-uv a
    versión exacta (no publica la etiqueta flotante `v10`)."""
    usos = re.findall(r"uses:\s*(\S+)", TEXTO_CI)
    assert usos
    assert [uso for uso in usos if not re.search(r"@v\d+(\.\d+\.\d+)?$", uso)] == []
    assert all(re.search(r"@v\d+\.\d+\.\d+$", u) for u in usos if "setup-uv" in u)


def test_uv_de_ci_es_0_11_9_en_cada_trabajo() -> None:
    versiones = [
        paso["with"]["version"]
        for trabajo in CI["jobs"].values()
        for paso in trabajo["steps"]
        if str(paso.get("uses", "")).startswith("astral-sh/setup-uv")
    ]
    assert versiones and set(versiones) == {"0.11.9"}  # la que construye el instalador (T2, T14)
