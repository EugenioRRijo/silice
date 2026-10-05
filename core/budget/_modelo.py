"""Ayudantes de lectura sobre las filas de un presupuesto, compartidos por los módulos de
`core.budget` (persistencia, instantánea, edición, cotización, actualización).

Viven aparte para que `instantanea` y `persistencia` no se importen mutuamente: ambos dependen de
este módulo y de `core.models`, nada más.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from core import models
from core.contracts.apu import ParametrosCosto


def _buscar(session: Session, proyecto_nombre: str, codigo: str) -> models.Presupuesto:
    modelo = session.scalars(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == proyecto_nombre, models.Presupuesto.codigo == codigo)
    ).one_or_none()
    if modelo is None:
        raise KeyError(f"no hay ningún presupuesto {codigo!r} en el proyecto {proyecto_nombre!r}")
    return modelo


def _parametros_de(modelo: models.Presupuesto) -> ParametrosCosto:
    """Los `ParametrosCosto` congelados en la fila del presupuesto.

    El contrato `Presupuesto` no los lleva (insuficiencia registrada en la bitácora de I0.5): la
    fila sí, y de ahí salen.
    """
    return ParametrosCosto(
        fcas=modelo.fcas,
        bono_alimentacion=modelo.bono_alimentacion,
        administracion=modelo.administracion,
        utilidad=modelo.utilidad,
    )


def _sesion_de(modelo: models.Presupuesto) -> Session:
    """La sesión a la que pertenece la fila; `ValueError` claro si está suelta."""
    sesion = object_session(modelo)
    if sesion is None:
        raise ValueError(
            f"el presupuesto {modelo.codigo!r} no está asociado a una sesion: "
            "agréguelo a una Session antes de leer sus composiciones"
        )
    return sesion
