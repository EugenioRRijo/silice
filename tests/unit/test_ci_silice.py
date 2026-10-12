"""La CI corre la suite sin red y descarga el modelo antes (maestro §6.3, RV-17; S5 §11.1)."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
FLUJO = RAIZ / ".github" / "workflows" / "ci.yml"


def _trabajo(nombre: str) -> dict:
    return yaml.safe_load(FLUJO.read_text(encoding="utf-8"))["jobs"][nombre]


def _pruebas() -> dict:
    return _trabajo("pruebas")


def _agregar() -> dict:
    return _trabajo("agregar")


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
    assert descarga < _indice(trabajo, "uv run --no-sync pytest")
    assert trabajo["steps"][descarga]["env"]["HF_HUB_OFFLINE"] == "0"
    cache = next(
        indice
        for indice, paso in enumerate(trabajo["steps"])
        if str(paso.get("uses", "")).startswith("actions/cache")
    )
    assert cache < descarga


def test_la_suite_se_reparte_en_tramos_que_cubren_todos_los_archivos() -> None:
    trabajo = _pruebas()
    assert trabajo["strategy"]["fail-fast"] is False
    assert "scripts/dividir_suite.py" in trabajo["steps"][_indice(trabajo, "dividir_suite")]["run"]
    assert "--junitxml=reporte-$SISTEMA-$TRAMO.xml" in str(trabajo["steps"])


def test_la_meta_de_silice_y_las_garantias_corren_en_agregar_con_historia_completa() -> None:
    trabajo = _agregar()
    assert trabajo["needs"] == "pruebas"
    assert trabajo["if"] == "always()"
    checkout = next(
        paso
        for paso in trabajo["steps"]
        if str(paso.get("uses", "")).startswith("actions/checkout")
    )
    assert checkout["with"]["fetch-depth"] == 0
    union = _indice(trabajo, "scripts/unir_junit.py")
    assert union < _indice(trabajo, "scripts/verificar_omitidas.py")
    assert union < _indice(trabajo, "scripts/medir_rnf11.py") < _indice(trabajo, "meta_silice.py")
    meta = _indice(trabajo, "scripts/meta_silice.py")
    assert "--junit reporte-pruebas-ubuntu-latest.xml" in trabajo["steps"][meta]["run"]
    assert _indice(trabajo, "coverage combine") < _indice(trabajo, "--fail-under=80")
    assert _indice(trabajo, "git diff --exit-code") > union
    assert 'test "${{ needs.pruebas.result }}" = "success"' in trabajo["steps"][-1]["run"]
