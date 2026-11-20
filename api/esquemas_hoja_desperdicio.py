"""Esquemas del desperdicio en la pestaña APU de la Hoja (F5 vial, punto 1; acta DS-48g).

Aparte de `api/esquemas_hoja.py`, que ya pasa del tope de líneas (`MODULOS_GRANDES`): allí se
importan para `DetalleApuRespuesta`. Las cifras viajan como texto con coma decimal, como siempre.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DesperdicioLineaRespuesta(BaseModel):
    """La neta y el porcentaje de desperdicio de la fila `fila` (desde 1) de Materiales, «0,50 +
    4 %» (F5 vial, punto 1); la cantidad de esa fila ya los incluye. `neta` y `porcentaje`, con
    coma decimal, siembran los campos de la Hoja, que los edita (2026-11-13)."""

    fila: int
    texto: str
    neta: str
    porcentaje: str


class DesgloseGuardadoRespuesta(BaseModel):
    """Quién guardó el desglose del desperdicio que la pestaña muestra de la base y cuándo (acta
    DS-48g, opción A). `responsable` (`Nombre <login>`) es nulo si no consta: lo guardado antes de
    anotarlo, o con la clave de API, sin cuenta."""

    responsable: str | None
    fecha_hora: datetime
