"""Entregar el paquete auditado, sin Streamlit (spec S3 §8.2, UC-22; RF-85).

Esta primera entrega del módulo (S3-3, tarea 18) trae solo lo que la cadena de huellas necesita
para cubrir el espacio de la hoja: el proveedor de anexos y la sesión que lo lleva. El resto de la
orquestación (anexos del paquete, informe del emisor, firma, registro de la entrega) llega con la
tarea 16, sin cambiar estas dos firmas.

`anexos_de_cadena` es el proveedor que `guardar_presupuesto(..., anexos_de=...)` y
`verificar_cadena` usan para que la cadena cubra el espacio de la versión; `con_anexos_de_cadena`
lo fija en la sesión de toda pantalla que guarda versiones con su espacio, para que ningún
llamador del embudo tenga que acordarse de pasarlo.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from adapters.espacio import cargar_espacio
from adapters.espacio.serie import espacio_a_objeto
from core import models
from core.budget import cadena, canonico

__all__ = ["NOMBRE_ANEXO_ESPACIO", "anexos_de_cadena", "con_anexos_de_cadena"]

NOMBRE_ANEXO_ESPACIO = "anexos/espacio.json"


def anexos_de_cadena(session: Session, version: models.Presupuesto) -> Mapping[str, bytes]:
    """Los anexos que la cadena cubre: solo el espacio, y solo si la versión lo tiene."""
    espacio = cargar_espacio(session, version.id)
    if espacio.vacio:
        return {}
    return {NOMBRE_ANEXO_ESPACIO: canonico.json_canonico(espacio_a_objeto(espacio))}


def con_anexos_de_cadena(session: Session) -> Session:
    """La sesión de una pantalla que guarda versiones con su espacio: la cadena lo cubre."""
    return cadena.anexos_por_omision(session, anexos_de_cadena)
