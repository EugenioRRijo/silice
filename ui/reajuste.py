"""Reexportación de `aplicacion.reajuste` (RM-1, plan de la sesión 2b).

La lógica de UC-18 (de los textos a la cláusula, cálculo, guardado y Excel) se movió a
`aplicacion/reajuste.py` para que la API y la interfaz clásica la compartan sin que `api/` importe
`ui/`. Este módulo conserva los nombres que usan la página, los scripts y las pruebas; no define
nada.
"""

from aplicacion.reajuste import (
    COLUMNAS_EJECUTADO,
    COLUMNAS_REAJUSTE,
    FUENTE_DEL_CALCULO,
    NO_DISPONIBLE,
    ROTULOS,
    calcular,
    clausula_desde_textos,
    excel_en_bytes,
    filas_lado_a_lado,
    guardar,
    guardar_con_valuaciones,
    parciales_por_reemplazar,
    periodos_desde_filas,
    periodos_desde_valuaciones,
    tabla_ejecutado,
    tabla_reajuste,
)

__all__ = [
    "COLUMNAS_EJECUTADO",
    "COLUMNAS_REAJUSTE",
    "FUENTE_DEL_CALCULO",
    "NO_DISPONIBLE",
    "ROTULOS",
    "calcular",
    "clausula_desde_textos",
    "excel_en_bytes",
    "filas_lado_a_lado",
    "guardar",
    "guardar_con_valuaciones",
    "parciales_por_reemplazar",
    "periodos_desde_filas",
    "periodos_desde_valuaciones",
    "tabla_ejecutado",
    "tabla_reajuste",
]
