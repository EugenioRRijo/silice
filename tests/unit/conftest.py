"""Qué archivos de `tests/unit/` no se recolectan según la plataforma.

Sin `skip` ni lista blanca de omitidas (`tests/unit/test_sin_omisiones.py`): lo que necesita un
paquete que solo existe en Windows no se recolecta en otra plataforma.
"""

from __future__ import annotations

import sys

#: Importan `webview` (pywebview), que `pyproject.toml` instala solo con `sys_platform == 'win32'`.
SOLO_WINDOWS = ("test_ventana_pywebview_real.py",)


def archivos_a_ignorar(plataforma: str) -> list[str]:
    """Archivos que `pytest` no debe recolectar en `plataforma` (el valor de `sys.platform`)."""
    return [] if plataforma == "win32" else list(SOLO_WINDOWS)


collect_ignore = archivos_a_ignorar(sys.platform)
