"""Ayudas para leer un informe de auditoria en las pruebas (INV-052).

Antes vivia en `tests/integration/test_auditoria_7_de_7.py`, y
`tests/integration/test_composicion_extremo_a_extremo.py` lo importaba de ahi; lo compartido entre
pruebas vive en `tests/fixtures/` (regla A-6 del plan de C3).
"""

from __future__ import annotations

from core.contracts import Severidad


def detectadas(informe) -> set[tuple[str, str | None]]:
    """Lo que el informe senala: `(regla, partida)` de cada hallazgo de severidad ERROR o mas."""
    return {
        (hallazgo.regla, informe.partida_de(hallazgo))
        for hallazgo in informe.hallazgos
        if hallazgo.severidad >= Severidad.ERROR
    }
