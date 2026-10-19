"""Reexportacion de `aplicacion.tablero` (RM-1, sesion 2b).

La logica se movio a la capa de aplicacion para que la API la use sin importar `ui/`. Este modulo
conserva los nombres de siempre para las paginas de Streamlit y las pruebas; no define nada propio
(lo vigila `tests/unit/test_arquitectura.py`).
"""

from __future__ import annotations

from aplicacion.tablero import (
    CERO,
    PARTIDAS_EN_PARETO,
    DatosControl,
    DatosTablero,
    Tarjeta,
    avance_fisico,
    filas_comparativo,
    filas_de_curvas,
    filas_de_desglose,
    filas_pareto,
    leer_control,
    leer_tablero,
    tarjetas_de_control,
    tarjetas_del_presupuesto,
)

__all__ = [
    "CERO",
    "DatosControl",
    "DatosTablero",
    "PARTIDAS_EN_PARETO",
    "Tarjeta",
    "avance_fisico",
    "filas_comparativo",
    "filas_de_curvas",
    "filas_de_desglose",
    "filas_pareto",
    "leer_control",
    "leer_tablero",
    "tarjetas_de_control",
    "tarjetas_del_presupuesto",
]
