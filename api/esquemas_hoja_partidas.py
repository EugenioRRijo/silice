"""La respuesta de agregar una partida a la Hoja (`POST /v1/hoja/borradores/{id}/partidas`).

Vive aparte de `api/esquemas_hoja.py`, que está en su tope de líneas (MODULOS_GRANDES de
`tests/unit/test_arquitectura.py`), desde que trae el `aviso` de una partida que queda pendiente
(prueba en vivo y árbitro de la rama, 2026-11-18).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from api.esquemas_hoja import ResumenHojaRespuesta


class PartidaAgregadaRespuesta(BaseModel):
    """El borrador ya recalculado: su `rev` nuevo, el resumen y la clave del renglón nuevo."""

    rev: int
    resumen: ResumenHojaRespuesta
    clave: str
    aviso: str | None = Field(
        default=None,
        description=(
            "Si la partida quedó pendiente con la lista de la versión: qué insumos faltan, en qué "
            "lista están y qué hacer; null si se valoró."
        ),
    )
