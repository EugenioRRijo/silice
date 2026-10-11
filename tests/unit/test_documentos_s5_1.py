"""Los documentos de S5-1 (spec S5 §13): la ERS trae RF-96 y RNF-20, el plan de pruebas cita sus
pruebas reales y los manuales ya no ofrecen la ruta libre del caso."""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _texto(relativa: str) -> str:
    return (RAIZ / relativa).read_text(encoding="utf-8")


def test_la_ers_trae_rf_96_y_rnf_20() -> None:
    ers = _texto("docs/ERS.md")
    assert re.search(r"^\| RF‑96 \|", ers, re.M)
    assert "RNF‑20" in ers


def test_el_plan_de_pruebas_cita_pruebas_que_existen() -> None:
    plan = _texto("docs/plan_pruebas.md")
    citadas = set(
        re.findall(r"`(tests/[\w/]+\.py)::(\w+)`", plan.split("### 8.2", 1)[1].split("## 9.", 1)[0])
    )
    assert citadas
    for archivo, prueba in citadas:
        assert f"def {prueba}(" in _texto(archivo), f"{archivo}::{prueba}"


def test_los_manuales_ya_no_ofrecen_la_ruta_libre_del_caso() -> None:
    for relativa in ("docs/manual_usuario.md", "README.md"):
        assert "Archivo del caso (SQLite)" not in _texto(relativa), relativa


def test_el_registro_de_cambios_trae_t0_y_s5_1() -> None:
    cambios = _texto("CHANGELOG.md")
    assert "## [Sin publicar]" in cambios and "caso_0001_base_0_5_0" in cambios
    for pieza in ("SILICE_CASO", "dependencias", "guardia de red", "meta_silice.py"):
        assert pieza in cambios, pieza
