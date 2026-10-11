"""NORMAS §3 y su enmienda concuerdan (maestro §6.1, RV-2; plan 0.6.0, tarea A5).

NORMAS cambia solo cuando el documento dice que Eugenio la ratifico. La enmienda
fue ratificada el 2026-10-11; la prueba exige que las tres reglas esten en NORMAS.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ENMIENDA = RAIZ / "docs" / "bitacora" / "2026-10-silice-enmienda-normas-3.md"
REGLAS = (
    "Como máximo tres worktrees vivos",
    "ramas cortas por fase",
    "un solo carril de núcleo",
)
_ESTADO = re.compile(
    r"^\*\*Estado:\*\* (PROPUESTA|RATIFICADA por Eugenio el \d{4}-\d{2}-\d{2})$", re.MULTILINE
)


def test_la_enmienda_declara_las_tres_reglas_y_su_estado() -> None:
    texto = ENMIENDA.read_text(encoding="utf-8")
    for regla in REGLAS:
        assert regla in texto, regla
    assert _ESTADO.search(texto) is not None


def test_normas_aplica_la_enmienda_solo_si_esta_ratificada() -> None:
    estado = _ESTADO.search(ENMIENDA.read_text(encoding="utf-8")).group(1)
    normas = (RAIZ / "NORMAS.md").read_text(encoding="utf-8")
    for regla in REGLAS:
        assert (regla in normas) is estado.startswith("RATIFICADA"), regla


def test_la_enmienda_ratificada_esta_en_normas_y_ya_no_queda_la_regla_vieja() -> None:
    texto = ENMIENDA.read_text(encoding="utf-8")
    assert "RATIFICADA por Eugenio el 2026-10-11" in texto
    normas = (RAIZ / "NORMAS.md").read_text(encoding="utf-8")
    assert "Solo coexisten el checkout principal y el worktree del sprint vigente" not in normas
