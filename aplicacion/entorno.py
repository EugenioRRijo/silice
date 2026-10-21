"""El modo entrega para la API (`SILICE_MODO_ENTREGA`; punto 7 de la ola 0a, sesión 2b).

Aquí viven también los nombres de las variables de entorno de Sílice y sus alias anteriores (plan
de la 0.6.0, tarea A1; movido de `ui/entorno.py` en el retiro de Streamlit, F5). Durante el
prototipo el producto se llamó AREN.IA (hoy Sílice) y sus variables llevaban ese prefijo. Desde la
0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`; `ARENIA_CASO` y `ARENIA_MODO_ENTREGA` se
aceptaron como alias hasta la 0.6.0 inclusive y **ya no se aceptan desde la 0.7.0**:
`ALIAS_ANTERIORES` quedó vacío (`tests/unit/test_entorno_silice.py` lo exige en cuanto
`pyproject.toml` pasa de la 0.6.0). Por eso el modo entrega se enciende solo con el valor exacto
`"1"`.

Regla de `leer_variable`: manda la variable nueva si tiene texto; si falta o está en blanco, su
alias (hoy ninguno); si ninguna, `None`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

VARIABLE_CASO = "SILICE_CASO"
VARIABLE_MODO_ENTREGA = "SILICE_MODO_ENTREGA"
VALOR_MODO_ENTREGA = "1"

#: Última versión que acepta los nombres anteriores.
ULTIMA_VERSION_CON_ALIAS = "0.6.0"

#: Nombre nuevo -> nombre anterior aceptado como alias hasta `ULTIMA_VERSION_CON_ALIAS`.
#: Retirados en la 0.7.0 (eran `ARENIA_CASO` y `ARENIA_MODO_ENTREGA`).
ALIAS_ANTERIORES: dict[str, str] = {}


def leer_variable(entorno: Mapping[str, str], nombre: str) -> str | None:
    """El valor de `nombre` en `entorno` o, si falta o está en blanco, el de su alias anterior.

    `None` si ninguna de las dos tiene texto.
    """
    for candidato in (nombre, ALIAS_ANTERIORES.get(nombre)):
        if candidato is None:
            continue
        valor = entorno.get(candidato)
        if valor is not None and valor.strip():
            return valor
    return None


def modo_entrega_activo(entorno: Mapping[str, str] | None = None) -> bool:
    """True si `SILICE_MODO_ENTREGA` vale exactamente `"1"` (en `entorno` o en el del proceso)."""
    fuente = os.environ if entorno is None else entorno
    return fuente.get(VARIABLE_MODO_ENTREGA) == VALOR_MODO_ENTREGA
