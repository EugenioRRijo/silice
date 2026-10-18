"""Reexportación de `aplicacion.proyectos` (RM-1, sesión 2b).

La lógica de proyectos del caso abierto se movió a la capa de aplicación para que la API la use sin
importar `ui/`. Este módulo conserva los nombres de siempre para la barra superior, el tablero y
las pruebas; no define nada propio (lo vigila `tests/unit/test_arquitectura.py`).
"""

from __future__ import annotations

from aplicacion.proyectos import (
    MONEDAS_DEL_PROYECTO,
    RESPONSABLE_DE_LA_INTERFAZ,
    ProyectoInvalido,
    ResumenAuditoria,
    VersionVigente,
    crear_proyecto_nuevo,
    listar_proyectos,
    resumen_auditoria,
    version_vigente,
)

__all__ = [
    "MONEDAS_DEL_PROYECTO",
    "RESPONSABLE_DE_LA_INTERFAZ",
    "ProyectoInvalido",
    "ResumenAuditoria",
    "VersionVigente",
    "crear_proyecto_nuevo",
    "listar_proyectos",
    "resumen_auditoria",
    "version_vigente",
]
