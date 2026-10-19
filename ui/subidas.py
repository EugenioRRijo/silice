"""Guardado seguro de las subidas de Streamlit: reexportación de `aplicacion.subidas` (RM-1).

La regla del nombre seguro (A-1, INV-123, RNF-12) vive en la capa de aplicación para que la
recepción de un paquete (`aplicacion.revision`) la use sin importar `ui/`; este módulo conserva el
nombre que usan las pantallas con subida y sus pruebas.
"""

from __future__ import annotations

from aplicacion.subidas import LONGITUD_MAXIMA, Subida, guardar_subida, nombre_seguro

__all__ = ["LONGITUD_MAXIMA", "Subida", "guardar_subida", "nombre_seguro"]
