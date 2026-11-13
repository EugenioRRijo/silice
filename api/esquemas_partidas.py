"""Las partidas de una versión del contrato, como las devuelven Control y Reajuste (AC2).

Alimentan los campos «Partida» con autocompletado de la interfaz: se ofrece lo contratado y no
el catálogo entero. Solo texto (código, descripción y unidad tal como el contrato las nombra);
ninguna cifra viaja aquí.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from aplicacion.control import PartidasDeUnaVersion

__all__ = [
    "PartidaDelContratoRespuesta",
    "PartidasDelContratoRespuesta",
    "RenglonDelContratoRespuesta",
    "RenglonesDelContratoRespuesta",
    "partidas_a_respuesta",
    "renglones_a_respuesta",
]


class PartidaDelContratoRespuesta(BaseModel):
    codigo: str
    descripcion: str
    unidad: str


class PartidasDelContratoRespuesta(BaseModel):
    version: str = Field(description="El código de la versión del contrato; vacío si no hay")
    aviso: str = Field(default="", description="Texto fijo que explica una lista vacía")
    partidas: list[PartidaDelContratoRespuesta] = Field(description="Por código, una sola vez")
    truncada: bool = Field(
        default=False,
        description=(
            "La lista se recortó al tope: que una partida no esté en ella no dice que no esté en "
            "el contrato (la interfaz no la rechaza y deja que decida el servidor)"
        ),
    )


def partidas_a_respuesta(
    halladas: PartidasDeUnaVersion | None, aviso: str = ""
) -> PartidasDelContratoRespuesta:
    """`halladas` en `None`: no hay versión con que guiar; la lista va vacía con su `aviso`."""
    if halladas is None:
        return PartidasDelContratoRespuesta(version="", aviso=aviso, partidas=[])
    return PartidasDelContratoRespuesta(
        version=halladas.version,
        aviso=aviso,
        partidas=[
            PartidaDelContratoRespuesta(codigo=p.codigo, descripcion=p.descripcion, unidad=p.unidad)
            for p in halladas.partidas
        ],
        truncada=halladas.truncada,
    )


class RenglonDelContratoRespuesta(PartidaDelContratoRespuesta):
    """Un renglón del presupuesto (Control, ola 2 del 2026-11-13): un código repetido en dos
    renglones se ofrece dos veces; la valuación sigue siendo por código."""

    renglon: int = Field(description="El número del renglón en el presupuesto, desde 1")
    renglones: int = Field(description="Cuántos renglones tiene ese código en el presupuesto")


class RenglonesDelContratoRespuesta(PartidasDelContratoRespuesta):
    partidas: list[RenglonDelContratoRespuesta] = Field(  # type: ignore[assignment]
        description="Una por renglón del presupuesto, en su orden"
    )


def renglones_a_respuesta(
    halladas: PartidasDeUnaVersion | None, aviso: str = ""
) -> RenglonesDelContratoRespuesta:
    """Como `partidas_a_respuesta`, con el número de cada renglón (`renglones_de_la_version`)."""
    if halladas is None:
        return RenglonesDelContratoRespuesta(version="", aviso=aviso, partidas=[])
    return RenglonesDelContratoRespuesta(
        version=halladas.version,
        aviso=aviso,
        partidas=[
            RenglonDelContratoRespuesta(
                codigo=p.codigo,
                descripcion=p.descripcion,
                unidad=p.unidad,
                renglon=p.renglon or 0,
                renglones=p.renglones or 0,
            )
            for p in halladas.partidas
        ],
        truncada=halladas.truncada,
    )
