"""El oráculo de DS-57 y DS-58: qué transacciones abre cada sesión sobre una carpeta.

Con `SesionDeEscrituraDep` la primera consulta abre `BEGIN IMMEDIATE`. Si una ruta arma su respuesta
después del `commit`, sus consultas abren otra transacción inmediata, que espera a otro que escribe
y, pasado el `busy_timeout`, da 503 con lo suyo ya guardado. Los eventos `after_begin` y
`after_commit` de la sesión lo hacen visible: tras el último `commit` no puede haber otro `begin`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.orm import Session


@contextmanager
def transacciones_del_caso(caso: Path) -> Iterator[dict[int, list[str]]]:
    """Por sesión sobre `caso`, la secuencia de sus `begin` y `commit` mientras dura el bloque."""
    por_sesion: dict[int, list[str]] = {}

    def al_empezar(sesion, _transaccion, conexion) -> None:
        if Path(conexion.engine.url.database).resolve() == caso.resolve():
            por_sesion.setdefault(id(sesion), []).append("begin")

    def al_confirmar(sesion) -> None:
        if id(sesion) in por_sesion:
            por_sesion[id(sesion)].append("commit")

    event.listen(Session, "after_begin", al_empezar)
    event.listen(Session, "after_commit", al_confirmar)
    try:
        yield por_sesion
    finally:
        event.remove(Session, "after_begin", al_empezar)
        event.remove(Session, "after_commit", al_confirmar)


def lo_ultimo_de_cada_una(por_sesion: dict[int, list[str]]) -> list[str]:
    """Lo último que hizo cada sesión que confirmó sobre el caso: `"commit"` si armó la respuesta
    antes de confirmar, `"begin"` si volvió a consultar después."""
    return [eventos[-1] for eventos in por_sesion.values() if "commit" in eventos]
