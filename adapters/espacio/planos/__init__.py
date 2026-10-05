"""Importacion de planos a la hoja de metrajes (spec del sprint final, §6.6; RF-50 y RF-51).

El plano crea filas en la hoja con su origen DXF o IFC y un informe de lo que no reconocio;
nunca salta la hoja ni la auditoria (DA-SF-6). Dos lectores: `planos.dxf.importar_dxf` y
`planos.ifc.importar_ifc`; ambos devuelven un `ResultadoImportacion` y la reimportacion es
`fusionar`.

Este `__init__` solo reexporta el informe: NO importa `dxf` ni `ifc`, para que importar
`adapters.espacio` (que carga la interfaz) no cargue `ezdxf` ni `ifcopenshell` (INV-024,
extras perezosos).
"""

from adapters.espacio.planos.informe import (
    EstadoImportacion,
    ItemInforme,
    ResultadoImportacion,
    TipoItem,
    cargar_alturas,
    declarar_circuito,
    declarar_circuitos,
    fusionar,
)

__all__ = [
    "EstadoImportacion",
    "ItemInforme",
    "ResultadoImportacion",
    "TipoItem",
    "cargar_alturas",
    "declarar_circuito",
    "declarar_circuitos",
    "fusionar",
]
