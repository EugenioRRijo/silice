"""Constantes y partidas de la especialidad vial, cada una con su fuente o «supuesto declarado».

`Constante` es una copia deliberada de la de `adapters/espacio/especialidades/__init__.py`: un
adaptador no importa de otro (NORMAS.md §2; `tests/unit/test_arquitectura.py`), así que lo que se
necesita igual se duplica y se declara aquí.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

#: Fuente de toda constante cuya fuente normativa no está verificada (misma etiqueta que espacio).
SUPUESTO_DECLARADO = "supuesto declarado"


@dataclass(frozen=True, slots=True)
class Constante:
    """Una constante de cálculo con su fuente. Nunca un número suelto en el código."""

    id: str
    nombre: str
    valor: Decimal | str
    fuente: str

    def __post_init__(self) -> None:
        if not self.fuente.strip():
            raise ValueError(f"la constante {self.id} exige fuente o «{SUPUESTO_DECLARADO}»")

    @property
    def supuesto_declarado(self) -> bool:
        return self.fuente == SUPUESTO_DECLARADO


#: Fracción pintada de una línea discontinua: 3 m de línea por cada 8 m (3 pintados y 5 sin
#: pintar). No se cotejó con un manual de señalización venezolano.
FRACCION_PINTADA_DISCONTINUA = Constante(
    "V-1",
    "Fracción pintada de la línea discontinua (3 m de línea por cada 8 m)",
    Decimal("0.375"),
    SUPUESTO_DECLARADO,
)

#: Los códigos tienen la forma de la norma de carreteras (letra «C» y nueve dígitos), pero sus
#: números son provisionales y correlativos: no se tomaron del texto de la norma (fuentes del plan
#: vial, §3). No es la COVENIN 2000-92, que es la de edificaciones.
FUENTE_CODIGOS_VIALES = Constante(
    "V-2",
    "Forma de los códigos de partida viales",
    "C-xxx.xxx.xxx",
    "COVENIN 2000-1:1987, Parte I Carreteras: código a cotejar con el texto de la norma",
)

#: clave -> (código, descripción, unidad). La unidad es la de la cantidad que deriva el tramo.
PARTIDAS_VIALES: dict[str, tuple[str, str, str]] = {
    "fresado": ("C-000.000.001", "Fresado de pavimento asfáltico", "m3"),
    "base_granular": ("C-000.000.002", "Base granular compactada", "m3"),
    "subbase_granular": ("C-000.000.003", "Sub-base granular compactada", "m3"),
    "imprimacion": ("C-000.000.004", "Riego de imprimación", "m2"),
    "imprimacion_ligante": ("C-000.000.005", "Ligante del riego de imprimación", "l"),
    "riego_adherencia": ("C-000.000.006", "Riego de adherencia", "m2"),
    "riego_adherencia_ligante": ("C-000.000.007", "Ligante del riego de adherencia", "l"),
    "carpeta": ("C-000.000.008", "Carpeta de concreto asfáltico", "m2"),
    "carpeta_mezcla": ("C-000.000.009", "Mezcla asfáltica de la carpeta", "t"),
    "bacheo": ("C-000.000.010", "Bacheo con mezcla asfáltica", "m3"),
    "bacheo_mezcla": ("C-000.000.011", "Mezcla asfáltica del bacheo", "t"),
    "demarcacion_continua": ("C-000.000.012", "Demarcación con línea continua", "m"),
    "demarcacion_discontinua": ("C-000.000.013", "Demarcación con línea discontinua", "m"),
    "transporte_mezcla": (
        "C-000.000.014",
        "Transporte de mezcla asfáltica desde la planta",
        "t·km",
    ),
}
