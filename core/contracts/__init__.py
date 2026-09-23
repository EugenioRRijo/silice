"""Contratos de interfaz del sistema (CLAUDE.md §5). Estables durante todo el proyecto."""

from core.contracts.adaptador import AdaptadorDominio
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    ParametrosCosto,
    Rendimiento,
    ResultadoAPU,
    TipoRendimiento,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto, PuntoCurva
from core.contracts.unidades import normalizar_unidad, unidades_equivalentes
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "AdaptadorDominio",
    "ComposicionAPU",
    "Dominio",
    "Hallazgo",
    "ItemComputo",
    "LineaEquipo",
    "LineaManoObra",
    "LineaMaterial",
    "ModalidadManoObra",
    "OrigenTipo",
    "ParametrosCosto",
    "PartidaPresupuestada",
    "Presupuesto",
    "PuntoCurva",
    "ReglaVerificacion",
    "Rendimiento",
    "ResultadoAPU",
    "Severidad",
    "TipoRendimiento",
    "normalizar_unidad",
    "unidades_equivalentes",
]
