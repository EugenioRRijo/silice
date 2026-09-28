"""Modelos SQLAlchemy según docs/modelo_datos.md. Sesión I0.4.

Se importa **siempre cualificado** (`from core import models` → `models.Presupuesto`): siete nombres
coinciden con tipos de `core.contracts` y mezclarlos sin cualificar los haría indistinguibles.
"""

from core.models.base import Base
from core.models.entidades import (
    PREFIJO_CODIGO_INSUMO,
    CambioPrecio,
    ComposicionAPU,
    DescarteVersion,
    Ejecucion,
    Hallazgo,
    IncidenciaCambio,
    Insumo,
    ItemComputo,
    ListaPrecios,
    Partida,
    PartidaPresupuestada,
    PrecioInsumo,
    Presupuesto,
    Proyecto,
    PuntoCurva,
    Rendimiento,
    TipoInsumo,
)
from core.models.tipos import DecimalExacto

__all__ = [
    "PREFIJO_CODIGO_INSUMO",
    "Base",
    "CambioPrecio",
    "ComposicionAPU",
    "DecimalExacto",
    "DescarteVersion",
    "Ejecucion",
    "Hallazgo",
    "IncidenciaCambio",
    "Insumo",
    "ItemComputo",
    "ListaPrecios",
    "Partida",
    "PartidaPresupuestada",
    "PrecioInsumo",
    "Presupuesto",
    "Proyecto",
    "PuntoCurva",
    "Rendimiento",
    "TipoInsumo",
]
