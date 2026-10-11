"""Variables de entorno de Sílice y sus alias anteriores (plan de la 0.6.0, tarea A1).

Durante el prototipo el producto se llamó AREN.IA (hoy Sílice) y sus variables llevaban ese prefijo.
Desde la 0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`; `ARENIA_CASO` y
`ARENIA_MODO_ENTREGA` se aceptan como alias solo hasta la 0.6.0 inclusive
(`tests/unit/test_entorno_silice.py` falla cuando `pyproject.toml` pase de esa versión con el alias
todavía declarado).

Regla: manda la variable nueva si tiene texto; si falta o está en blanco, su alias; si ninguna,
`None`. Si las dos tienen valores distintos, gana la nueva. Sin Streamlit ni terceros: lo importan
`ui.caso`, `ui.app` y `tests/conftest.py`.
"""

from __future__ import annotations

from collections.abc import Mapping

VARIABLE_CASO = "SILICE_CASO"
VARIABLE_MODO_ENTREGA = "SILICE_MODO_ENTREGA"

#: Última versión que acepta los nombres anteriores.
ULTIMA_VERSION_CON_ALIAS = "0.6.0"

#: Nombre nuevo -> nombre anterior aceptado como alias hasta `ULTIMA_VERSION_CON_ALIAS`.
ALIAS_ANTERIORES: dict[str, str] = {
    VARIABLE_CASO: "ARENIA_CASO",
    VARIABLE_MODO_ENTREGA: "ARENIA_MODO_ENTREGA",
}


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
