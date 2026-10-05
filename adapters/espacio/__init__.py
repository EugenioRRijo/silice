"""Espacio: la hoja de metrajes como fuente de cantidades (spec del sprint final, §5 y §6).

No implementa `AdaptadorDominio`: su fuente es una hoja en base de datos y emite varias
especialidades con `derivar(espacio, especialidad)`. Persistencia propia `esp_*` por versión.
"""

from adapters.espacio.derivacion import ESPECIALIDADES, derivar
from adapters.espacio.modelo import (
    LLAVE_DE_PASO,
    TOLERANCIA,
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    ModoRecorrido,
    Punto,
    Recorrido,
    SobrescrituraSegmento,
    SuperficiePunto,
    SuperficieTramo,
    TipoFuente,
    TipoPunto,
    Tramo,
)
from adapters.espacio.origen import REFERENCIA_OBLIGATORIA, OrigenMedida, TipoOrigen, clave_esp
from adapters.espacio.persistencia import cargar_espacio, crear_esquema_espacio, guardar_espacio

__all__ = [
    "LLAVE_DE_PASO",
    "TOLERANCIA",
    "clave_esp",
    "ESPECIALIDADES",
    "REFERENCIA_OBLIGATORIA",
    "Ambiente",
    "Circuito",
    "Coord",
    "Especialidad",
    "Espacio",
    "Fuente",
    "ModoRecorrido",
    "OrigenMedida",
    "Punto",
    "Recorrido",
    "SobrescrituraSegmento",
    "SuperficiePunto",
    "SuperficieTramo",
    "TipoFuente",
    "TipoOrigen",
    "TipoPunto",
    "Tramo",
    "cargar_espacio",
    "crear_esquema_espacio",
    "derivar",
    "guardar_espacio",
]
