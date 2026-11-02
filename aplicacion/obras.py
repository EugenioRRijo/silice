"""La ficha de la obra (MOD-3a): cliente y ubicación, en la tabla `ficha_obra` del caso.

Estas funciones solo leen o escriben filas (`flush`, nunca `commit`): la transacción es de quien
llama (en la API, la misma que crea el proyecto, para que sea todo o nada).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.tablas_obra import FichaDeObra


@dataclass(frozen=True)
class FichaObra:
    cliente: str
    ubicacion: str


SIN_FICHA = FichaObra("", "")


def guardar_ficha(sesion: Session, proyecto_id: int, ficha: FichaObra) -> None:
    """Guarda (o reemplaza) la ficha de la obra `proyecto_id`; no confirma."""
    fila = sesion.get(FichaDeObra, proyecto_id)
    if fila is None:
        sesion.add(
            FichaDeObra(proyecto_id=proyecto_id, cliente=ficha.cliente, ubicacion=ficha.ubicacion)
        )
    else:
        fila.cliente = ficha.cliente
        fila.ubicacion = ficha.ubicacion
    sesion.flush()


def fichas(sesion: Session) -> dict[int, FichaObra]:
    """Las fichas guardadas por `proyecto_id`; una obra sin fila equivale a `FichaObra("", "")`."""
    return {
        fila.proyecto_id: FichaObra(fila.cliente, fila.ubicacion)
        for fila in sesion.scalars(select(FichaDeObra))
    }
