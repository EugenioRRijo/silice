"""Orquestacion de la elaboracion desde la interfaz clasica (INV-043, fase C3).

La logica sin Streamlit vive en `aplicacion/elaboracion.py` (RM-1, ola 2 de la sesion 2b) y se
reexporta aqui con sus nombres de siempre: las paginas, los scripts y las pruebas la siguen
llamando como atributos de `ui.elaboracion`. Quedan en este modulo `Guardado` y
`guardar_composicion`, que la ola 3 (Componer una partida) lleva a `aplicacion/`.

Es el unico modulo de `ui/` sin pagina que escribe filas en la base (regla A-2 del plan de C3):
`guardar_composicion` y `declarar_rendimiento` (UC-01 3b, INV-088) escriben, pero no confirman; el
`commit` es de la pagina.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aplicacion.composicion import desglose, motivo_para_no_reemplazar
from aplicacion.elaboracion import (
    COLUMNAS_CANTIDADES,
    COLUMNAS_PLAN,
    PendienteConPropuestas,
    RendimientoPorDeclarar,
    aceptar_propuesta,
    declarar_rendimiento,
    elaborar_desde_catalogo,
    filas_del_plan_por_defecto,
    filas_desde_plan,
    items_desde_filas,
    libro_excel,
    plan_de,
    plan_desde_filas,
    propuestas_de_pendientes,
    rendimientos_por_declarar,
)
from core.catalog import Catalogo
from core.contracts import ComposicionAPU, Dominio, ResultadoAPU

__all__ = [
    "Guardado",
    "guardar_composicion",
    "COLUMNAS_CANTIDADES",
    "COLUMNAS_PLAN",
    "PendienteConPropuestas",
    "RendimientoPorDeclarar",
    "aceptar_propuesta",
    "declarar_rendimiento",
    "elaborar_desde_catalogo",
    "filas_del_plan_por_defecto",
    "filas_desde_plan",
    "items_desde_filas",
    "libro_excel",
    "plan_de",
    "plan_desde_filas",
    "propuestas_de_pendientes",
    "rendimientos_por_declarar",
]


@dataclass(frozen=True, slots=True)
class Guardado:
    """Lo que dejo `guardar_composicion`: el desglose guardado o el motivo para no guardar."""

    resultado: ResultadoAPU | None = None
    motivo: str | None = None

    def __post_init__(self) -> None:
        if (self.resultado is None) == (self.motivo is None):
            raise ValueError("un Guardado lleva exactamente uno de los dos: resultado o motivo")


def guardar_composicion(
    catalogo: Catalogo,
    composicion: ComposicionAPU,
    dominio: Dominio,
    fecha: date,
    condiciones: str,
) -> Guardado:
    """Persiste la composicion: UC-10 si la partida no existe, UC-11 si ya existe.

    Sobre una partida existente, `motivo_para_no_reemplazar` decide antes de escribir: una
    composicion sin lineas borraria el desglose, y una cabecera distinta se descartaria en silencio
    (`reemplazar_composicion` solo sustituye lineas y rendimiento). En ese caso devuelve el motivo
    y no escribe nada. **No confirma**: el `commit` lo decide la pagina.
    """
    lista = catalogo.lista_vigente(fecha)
    try:
        partida = catalogo.partida(composicion.codigo_partida)
    except KeyError:
        catalogo.cargar_composicion(composicion, lista, dominio, fecha, condiciones)
    else:
        motivo = motivo_para_no_reemplazar(partida.descripcion, partida.unidad, composicion)
        if motivo is not None:
            return Guardado(motivo=motivo)
        catalogo.reemplazar_composicion(composicion, lista, dominio, fecha, condiciones)
    return Guardado(resultado=desglose(composicion))
