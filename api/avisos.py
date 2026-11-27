"""Los avisos por evento desde una ruta que ya confirmó su carpeta (C11b).

Precios de la empresa confirma la carpeta y después avisa en `instalacion.db`: las dos bases no
tienen transacción común, así que el aviso va en una transacción corta y propia de la instalación
(`BEGIN IMMEDIATE`), como el reflejo del índice de aprobaciones (DS-69). Avisar nunca cambia la
respuesta: lo guardado ya está guardado y un fallo aquí solo se registra. Las reglas de quién recibe
qué viven en `aplicacion/avisos_por_evento.py`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from operacion.instalacion import sesion_de_instalacion

_registro = logging.getLogger(__name__)


def avisar(hacer: Callable[[Session], object]) -> None:
    """Corre `hacer(instalacion)` en una transacción propia y la confirma; un fallo se registra."""
    try:
        with sesion_de_instalacion(escritura=True) as instalacion:
            hacer(instalacion)
            instalacion.commit()
    except Exception:  # noqa: BLE001 (la carpeta ya confirmó: avisar no la desdice)
        _registro.warning("No se pudieron guardar los avisos por evento.", exc_info=True)
