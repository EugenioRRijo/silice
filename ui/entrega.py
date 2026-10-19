"""Entregar el paquete auditado: reexportación de `aplicacion.entrega` (RM-1, sesión 2b).

La lógica sin Streamlit vive en la capa de aplicación para que la API la use sin importar `ui/`;
este módulo conserva el nombre que usan la pantalla Entregar, la hoja, el marco y las pruebas.
"""

from __future__ import annotations

from aplicacion.entrega import (
    Entrega,
    EntregaRechazada,
    EstadoDeLaCadena,
    Resumen,
    anexo_de_ia,
    anexos_de_cadena,
    anexos_del_paquete,
    con_anexos_de_cadena,
    entregar,
    estado_de_la_cadena,
    nombre_de_archivo,
    resumen_de_entrega,
)

__all__ = [
    "Entrega",
    "EntregaRechazada",
    "EstadoDeLaCadena",
    "Resumen",
    "anexo_de_ia",
    "anexos_de_cadena",
    "anexos_del_paquete",
    "con_anexos_de_cadena",
    "entregar",
    "estado_de_la_cadena",
    "nombre_de_archivo",
    "resumen_de_entrega",
]
