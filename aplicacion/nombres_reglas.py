"""Catálogo único de nombres llanos de reglas de verificación (Lote K, punto 6).

Reúne en un solo sitio los nombres legibles de las reglas del núcleo (`R1`–`R7`, `R11`–`R14`),
del espacio y planos (`R8`–`R10`, `R15`–`R17`), del libro de la empresa (`L1`–`L11`, `F1`), del
libro con un APU por hoja (`AH1`–`AH12`) y de la especialidad vial (`VR`, `VR1`–`VR8`).

Las reglas del núcleo se leen de `core.verification` y aquí se restituyen las tildes que `core/`
omite (sin tocar `core/`). Las del libro se leen directamente de `adapters.hoja_empresa.reglas`.
`aplicacion/` no puede importar `fusion/` (`tests/unit/test_arquitectura.py`), así que `F1`, `L10`,
`L11` y `AH1`–`AH12` reflejan sus títulos vigentes aquí.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from adapters.hoja_empresa.reglas import REGLAS_LIBRO
from core.verification.precios import PrecioFueraDeRango, PrecioVencido
from core.verification.reglas import REGLAS
from core.verification.valuaciones import FuenteYFechasDeValuacion, ValuacionDentroDelPresupuesto

__all__ = ["NOMBRES_DE_REGLAS", "nombre_de_regla"]

#: Los nombres de `core.verification.reglas.REGLAS` con sus tildes, y nada más: ni una palabra
#: distinta (la auditoría antes de medicion-v1 halló R3, R5 y R7 con nombres que el núcleo no usa;
#: `tests/unit/test_nombres_reglas.py` compara letra por letra sin tildes).
_TILDES_NUCLEO: dict[str, str] = {
    "R1": "Trazabilidad geométrica",
    "R2": "Cierre de la curva de inversión",
    "R5": "Balance volumétrico",
    "R6": "Criterio de depreciación",
    "R7": "Conciliación presupuesto-plan",
    "R13": "Valuación dentro del presupuesto",
    "R14": "Fuente y fechas de la valuación",
}

_EXTRAS: dict[str, str] = {
    # Espacio y planos (`adapters/espacio/`)
    "R8": "Origen de la medida",
    "R9": "Coherencia espacial",
    "R10": "Límites de la especialidad",
    "R15": "Coherencia geométrica del plano",
    "R16": "Contraste entre dos fuentes",
    "R17": "Conexión de cada punto",
    # Fusión (`fusion/proceso.py`)
    "F1": "P.U. recalculado",
    "L10": "Documento sin modelo (PDF simple)",
    "L11": "Libro ↔ PDF entregado",
    # Libro con un APU por hoja (`fusion/apu_por_hoja.py`)
    "AH1": "Precio unitario del APU contra el recalculado",
    "AH2": "Bono por renglón no evaluable",
    "AH3": "Financiamiento no evaluable",
    "AH4": "Impuesto dentro del APU",
    "AH5": "Precio unitario del presupuesto contra su APU",
    "AH6": "Cantidad del presupuesto contra su APU",
    "AH7": "Renglón del presupuesto sin APU o APU sin renglón",
    "AH8": "Unidad traducida por el perfil",
    "AH9": "Banda de distancia de transporte",
    "AH10": "Número de renglón repetido en dos hojas",
    "AH11": "Hoja del presupuesto que parece de otra obra",
    "AH12": "Hojas fuera del prefijo del perfil",
    # Especialidad vial (`adapters/vial/reglas.py`)
    "VR": "Reglas viales",
    "VR1": "Toneladas de carpeta asfáltica",
    "VR2": "Porcentaje de asfalto en la mezcla",
    "VR3": "Ligante residual de imprimación y adherencia",
    "VR4": "Transporte de mezcla asfáltica",
    "VR5": "Rendimiento de pintura de demarcación",
    "VR6": "Progresivas solapadas o con huecos",
    "VR7": "Unidad o código incompatible con el tramo",
    "VR8": "Partida vial duplicada con otro origen",
}

_NOMBRES: dict[str, str] = {
    **{regla.codigo: regla.nombre for regla in REGLAS},
    PrecioFueraDeRango.codigo: PrecioFueraDeRango.nombre,
    PrecioVencido.codigo: PrecioVencido.nombre,
    ValuacionDentroDelPresupuesto.codigo: ValuacionDentroDelPresupuesto.nombre,
    FuenteYFechasDeValuacion.codigo: FuenteYFechasDeValuacion.nombre,
    **dict(REGLAS_LIBRO),
    **_TILDES_NUCLEO,
    **_EXTRAS,
}

#: Código de regla -> nombre llano en español. Solo lectura.
NOMBRES_DE_REGLAS: Mapping[str, str] = MappingProxyType(_NOMBRES)


def nombre_de_regla(codigo: str) -> str:
    """Nombre legible en español de la regla `codigo`, o cadena vacía si no está en el catálogo."""
    return _NOMBRES.get(codigo, "")
