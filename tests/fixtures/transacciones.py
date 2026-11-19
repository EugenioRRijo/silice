"""El oráculo de DS-57 y DS-58: qué transacciones abren las sesiones sobre una carpeta.

Con `SesionDeEscrituraDep` la primera consulta abre `BEGIN IMMEDIATE`. Si una ruta arma su respuesta
después del `commit`, sus consultas abren otra transacción inmediata, que espera a otro que escribe
y, pasado el `busy_timeout`, da 503 con lo suyo ya guardado. Los eventos `after_begin` y
`after_commit` de las sesiones lo hacen visible: tras el último `commit` sobre la carpeta no puede
haber otro `begin`, de esa sesión ni de otra.

Se guarda una referencia a cada sesión (no su `id`, que se reutiliza cuando una muere) y cuentan
todas las que empiezan sobre la carpeta, también las que nunca confirman.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.orm import Session


class Transacciones:
    """Los `begin` y `commit` sobre la carpeta, en orden, con la sesión que los hizo."""

    def __init__(self) -> None:
        self.eventos: list[tuple[Session, str]] = []

    def _de_la_carpeta(self, sesion: Session) -> bool:
        return any(otra is sesion for otra, _ in self.eventos)

    @property
    def confirmo(self) -> bool:
        return any(nombre == "commit" for _, nombre in self.eventos)

    def tras_el_ultimo_commit(self) -> list[str]:
        """Lo que pasó sobre la carpeta después de su último `commit` (vacío si nada)."""
        nombres = [nombre for _, nombre in self.eventos]
        ultimo = max(i for i, nombre in enumerate(nombres) if nombre == "commit")
        return nombres[ultimo + 1 :]

    def __repr__(self) -> str:
        sesiones: list[Session] = []
        for sesion, _ in self.eventos:
            if not any(s is sesion for s in sesiones):
                sesiones.append(sesion)
        return repr(
            [(next(i for i, s in enumerate(sesiones) if s is x), n) for x, n in self.eventos]
        )


@contextmanager
def transacciones_del_caso(caso: Path) -> Iterator[Transacciones]:
    """Las transacciones de todas las sesiones sobre `caso` mientras dura el bloque."""
    registro = Transacciones()

    def al_empezar(sesion, _transaccion, conexion) -> None:
        if Path(conexion.engine.url.database).resolve() == caso.resolve():
            registro.eventos.append((sesion, "begin"))

    def al_confirmar(sesion) -> None:
        if registro._de_la_carpeta(sesion):
            registro.eventos.append((sesion, "commit"))

    event.listen(Session, "after_begin", al_empezar)
    event.listen(Session, "after_commit", al_confirmar)
    try:
        yield registro
    finally:
        event.remove(Session, "after_begin", al_empezar)
        event.remove(Session, "after_commit", al_confirmar)
