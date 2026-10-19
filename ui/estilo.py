"""Reexportacion de `aplicacion.estilo` (RM-1, sesion 2b).

La logica se movio a la capa de aplicacion para que la API la use sin importar `ui/`. Este modulo
conserva los nombres de siempre para las paginas de Streamlit y las pruebas; no define nada propio
(lo vigila `tests/unit/test_arquitectura.py`).
"""

from __future__ import annotations

from aplicacion.estilo import (
    COLOR_ATENCION,
    COLOR_BIEN,
    COLOR_PRIMARIO,
    COLOR_TENUE,
    COLORES_RUBRO,
    COLORES_SERIE,
    NO_DISPONIBLE,
    dinero,
    indice,
    porcentaje,
)

__all__ = [
    "COLORES_RUBRO",
    "COLORES_SERIE",
    "COLOR_ATENCION",
    "COLOR_BIEN",
    "COLOR_PRIMARIO",
    "COLOR_TENUE",
    "NO_DISPONIBLE",
    "dinero",
    "indice",
    "porcentaje",
]
