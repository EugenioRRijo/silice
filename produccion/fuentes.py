"""Registro de constantes de `produccion/` con el estado de su fuente (PLAN_FUENTES_DATOS_CANTERA).

Ninguna constante de calculo puede estar `A_COTEJAR` o `SIN_FUENTE`; una prueba lo vigila. Densidad,
existencia inicial y minima son dato de la empresa y no tienen valor por defecto en el codigo.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EstadoDato(StrEnum):
    VERIFICADO = "verificado"
    DATO_DE_LA_EMPRESA = "dato de la empresa"
    A_COTEJAR = "a cotejar"
    CONSTRUIDO = "construido"
    A_MEDIR = "a medir"
    SIN_FUENTE = "sin fuente"


@dataclass(frozen=True, slots=True)
class Constante:
    nombre: str
    valor: str
    estado: EstadoDato
    fuente: str
    usada_en_calculo: bool


CONSTANTES: tuple[Constante, ...] = (
    Constante(
        "MAX_FILAS",
        "100000",
        EstadoDato.CONSTRUIDO,
        "RNF-25: tope de filas al leer un reporte ajeno",
        False,
    ),
    Constante(
        "MAX_COLUMNAS",
        "60",
        EstadoDato.CONSTRUIDO,
        "RNF-25: tope de columnas al leer un reporte ajeno",
        False,
    ),
    Constante(
        "FILAS_DE_ENCABEZADO",
        "30",
        EstadoDato.CONSTRUIDO,
        "filas iniciales donde se busca el encabezado del reporte",
        False,
    ),
    Constante(
        "TOLERANCIA_NETO_T",
        "0",
        EstadoDato.CONSTRUIDO,
        "la bascula entrega enteros en kg: el neto debe ser exactamente bruto - tara",
        True,
    ),
)
