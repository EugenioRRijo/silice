"""Normalizacion semantica de partidas (UC-03, Sesion I2). Requiere el extra `ml`."""

from ml.normalization.normalizador import (
    FALLAS_DE_LA_PROPUESTA,
    MODELO_POR_DEFECTO,
    PROPUESTAS_POR_DEFECTO,
    UMBRAL_POR_DEFECTO,
    NormalizadorPartidas,
    PartidaSimilar,
    Propuesta,
    TieneDescripcion,
    proponedor,
    propuestas_para,
)

__all__ = [
    "FALLAS_DE_LA_PROPUESTA",
    "MODELO_POR_DEFECTO",
    "PROPUESTAS_POR_DEFECTO",
    "UMBRAL_POR_DEFECTO",
    "NormalizadorPartidas",
    "PartidaSimilar",
    "Propuesta",
    "TieneDescripcion",
    "proponedor",
    "propuestas_para",
]
