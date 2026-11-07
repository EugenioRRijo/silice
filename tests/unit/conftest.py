"""Recolección de `tests/unit/` según la plataforma.

La regla vive en `tests/fixtures/plataforma.py` (INV-052).
"""

from __future__ import annotations

import sys

from tests.fixtures.plataforma import archivos_a_ignorar

collect_ignore = archivos_a_ignorar(sys.platform)
