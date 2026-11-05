"""Las partidas de una versión del contrato, como las devuelven Control y Reajuste (AC2).

Alimentan los campos «Partida» con autocompletado de la interfaz: se ofrece lo contratado y no
el catálogo entero. Solo texto (código, descripción y unidad tal como el contrato las nombra);
ninguna cifra viaja aquí.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from aplicacion.control import PartidaDelContrato

__all__ = ["PartidaDelContratoRespuesta", "PartidasDelContratoRespuesta", "partidas_a_respuesta"]


class PartidaDelContratoRespuesta(BaseModel):
    codigo: str
    descripcion: str
    unidad: str


class PartidasDelContratoRespuesta(BaseModel):
    version: str = Field(description="El código de la versión del contrato; vacío si no hay")
    aviso: str = Field(default="", description="Texto fijo que explica una lista vacía")
    partidas: list[PartidaDelContratoRespuesta] = Field(description="Por código, una sola vez")


def partidas_a_respuesta(
    version: str, partidas: list[PartidaDelContrato], aviso: str = ""
) -> PartidasDelContratoRespuesta:
    return PartidasDelContratoRespuesta(
        version=version,
        aviso=aviso,
        partidas=[
            PartidaDelContratoRespuesta(codigo=p.codigo, descripcion=p.descripcion, unidad=p.unidad)
            for p in partidas
        ],
    )
