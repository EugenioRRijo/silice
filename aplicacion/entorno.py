"""El modo entrega para la API (`SILICE_MODO_ENTREGA`; punto 7 de la ola 0a, sesión 2b).

Duplica a propósito `ui.app.modo_entrega_activo`: la API no importa `ui/` y `ui/entorno.py` solo
usa la biblioteca estándar (no puede importar esta capa). Desde la 0.7.0 no hay alias que leer
(`ui.entorno.ALIAS_ANTERIORES` está vacío), así que la regla es la misma: encendido solo con el
valor exacto `"1"`. `tests/unit/test_aplicacion_entorno.py` compara las dos funciones.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

VARIABLE_MODO_ENTREGA = "SILICE_MODO_ENTREGA"
VALOR_MODO_ENTREGA = "1"


def modo_entrega_activo(entorno: Mapping[str, str] | None = None) -> bool:
    """True si `SILICE_MODO_ENTREGA` vale exactamente `"1"` (en `entorno` o en el del proceso)."""
    fuente = os.environ if entorno is None else entorno
    return fuente.get(VARIABLE_MODO_ENTREGA) == VALOR_MODO_ENTREGA
