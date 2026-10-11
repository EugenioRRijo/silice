"""La CI corre la suite sin red y descarga el modelo antes (maestro §6.3, RV-17; S5 §11.1)."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
FLUJO = RAIZ / ".github" / "workflows" / "ci.yml"


def _pruebas() -> dict:
    return yaml.safe_load(FLUJO.read_text(encoding="utf-8"))["jobs"]["pruebas"]


def _indice(trabajo: dict, fragmento: str) -> int:
    for indice, paso in enumerate(trabajo["steps"]):
        if fragmento in str(paso.get("run", "")):
            return indice
    raise AssertionError(f"ningun paso corre {fragmento!r}")


def test_la_suite_corre_sin_red() -> None:
    assert _pruebas()["env"]["HF_HUB_OFFLINE"] == "1"


def test_el_modelo_se_descarga_antes_de_pytest_y_con_cache() -> None:
    trabajo = _pruebas()
    descarga = _indice(trabajo, "scripts/descargar_modelo.py")
    assert descarga < _indice(trabajo, "pytest -W error")
    assert trabajo["steps"][descarga]["env"]["HF_HUB_OFFLINE"] == "0"
    cache = next(
        indice
        for indice, paso in enumerate(trabajo["steps"])
        if str(paso.get("uses", "")).startswith("actions/cache")
    )
    assert cache < descarga


def test_la_meta_de_silice_corre_tras_la_suite_con_historia_completa() -> None:
    trabajo = _pruebas()
    checkout = next(
        paso
        for paso in trabajo["steps"]
        if str(paso.get("uses", "")).startswith("actions/checkout")
    )
    assert checkout["with"]["fetch-depth"] == 0
    meta = _indice(trabajo, "scripts/meta_silice.py")
    assert _indice(trabajo, "pytest -W error") < meta
    assert _indice(trabajo, "scripts/medir_rnf11.py") < meta
    assert "--junit reporte-pruebas.xml" in trabajo["steps"][meta]["run"]
