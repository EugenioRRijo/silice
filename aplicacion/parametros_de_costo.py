"""Los parámetros de costo de una versión guardada, en un solo lugar.

Una versión congela sus factores (FCAS, bono de alimentación, administración y utilidad) en sus
columnas de `presupuesto`; aquí se vuelven `ParametrosCosto` para recalcular un APU con ellos. Lo
usan la Hoja (`aplicacion.hoja.abrir_version`) y el piso del estudio de mercado
(`aplicacion.mercado`), que antes lo rearmaba a mano.
"""

from __future__ import annotations

from core import models
from core.contracts import ParametrosCosto

__all__ = ["parametros_de_version"]


def parametros_de_version(modelo: models.Presupuesto) -> ParametrosCosto:
    """Los factores de costo congelados en la versión `modelo`."""
    return ParametrosCosto(
        fcas=modelo.fcas,
        bono_alimentacion=modelo.bono_alimentacion,
        administracion=modelo.administracion,
        utilidad=modelo.utilidad,
    )
