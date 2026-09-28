"""Normalizacion semantica de partidas (UC-03, Sesion I2).

El paquete se importa sin el extra `ml`: `sentence-transformers` solo se importa al cargar el
modelo (`normalizador._cargar_modelo`), y su ausencia llega como `ImportError` dentro de
`proponedor`, que la trata como una de `FALLAS_DE_LA_PROPUESTA` (INV-081). Construir
`NormalizadorPartidas` directamente si requiere el extra.
"""

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
