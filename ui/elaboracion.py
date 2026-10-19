"""Orquestacion de la elaboracion desde la interfaz clasica (INV-043, fase C3).

La logica sin Streamlit vive en `aplicacion/elaboracion.py` (RM-1, ola 2 de la sesion 2b) y se
reexporta aqui con sus nombres de siempre: las paginas, los scripts y las pruebas la siguen
llamando como atributos de `ui.elaboracion`. `Guardado` y `guardar_composicion` viven en
`aplicacion/composicion.py` (ola 3, Componer una partida) y tambien se reexportan aqui.

Es el unico modulo de `ui/` sin pagina que escribe filas en la base (regla A-2 del plan de C3):
`guardar_composicion` y `declarar_rendimiento` (UC-01 3b, INV-088) escriben, pero no confirman; el
`commit` es de la pagina.
"""

from __future__ import annotations

from aplicacion.composicion import Guardado as Guardado
from aplicacion.composicion import guardar_composicion as guardar_composicion
from aplicacion.elaboracion import (
    COLUMNAS_CANTIDADES,
    COLUMNAS_PLAN,
    PendienteConPropuestas,
    RendimientoPorDeclarar,
    aceptar_propuesta,
    declarar_rendimiento,
    elaborar_desde_catalogo,
    filas_del_plan_por_defecto,
    filas_desde_plan,
    items_desde_filas,
    libro_excel,
    nombre_de_archivo,
    plan_de,
    plan_desde_filas,
    propuestas_de_pendientes,
    rendimiento_por_declarar,
    rendimientos_por_declarar,
)

__all__ = [
    "Guardado",
    "guardar_composicion",
    "COLUMNAS_CANTIDADES",
    "COLUMNAS_PLAN",
    "PendienteConPropuestas",
    "RendimientoPorDeclarar",
    "aceptar_propuesta",
    "declarar_rendimiento",
    "elaborar_desde_catalogo",
    "filas_del_plan_por_defecto",
    "filas_desde_plan",
    "items_desde_filas",
    "libro_excel",
    "nombre_de_archivo",
    "plan_de",
    "plan_desde_filas",
    "propuestas_de_pendientes",
    "rendimiento_por_declarar",
    "rendimientos_por_declarar",
]
