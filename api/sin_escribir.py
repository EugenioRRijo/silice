"""Una sesión de la base del caso que no puede escribir (rediseño F4, Tarea 2b).

Por qué existe: quien revisa abre su propio borrador de la Hoja para ver las vistas en solo
lectura (`POST /v1/hoja/borradores`, que pasa a `LEER_PROYECTO`). Abrir una versión sin
instantánea la escribe en la base (UC-15e: composiciones, plan y un registro de cambio a nombre de
quien abre, que confirma `aplicacion.hoja.abrir_version`). Esa función es la copia congelada del
experimento y no se toca, así que la guardia va aquí: mientras dura `sin_escribir(sesion)`, todo
lo que la sesión intentaría escribir lanza `EscrituraNegada` **antes** de llegar a la base, sin
carreras con otra petición. Hoy solo la usa esa ruta.

Cubre lo que pasa por la sesión: el volcado de la unidad de trabajo (`before_flush`, objetos
nuevos, borrados o cambiados) y las sentencias que se ejecutan con ella (`do_orm_execute`). Una
sentencia de SQLAlchemy pasa solo si es una lectura (`is_select`, también con `WITH`); un texto SQL
pasa solo si empieza por `SELECT` o `EXPLAIN`, o es un `PRAGMA` sin `=` (consultar, no asignar).
Todo lo demás se niega, también `WITH … INSERT` escrito como texto (menor 1 del árbitro). No cubre
lo que se mande por fuera de la sesión (`connection().exec_driver_sql`), que `abrir_version` no usa.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session
from sqlalchemy.sql.elements import TextClause

#: Lo que puede empezar un texto SQL que solo lee (un `PRAGMA` aparte: solo sin asignación ni
#: paréntesis, porque `PRAGMA x(7)` también asigna).
_LECTURAS = ("SELECT", "EXPLAIN")


class EscrituraNegada(Exception):  # noqa: N818 (el nombre dice lo que pasó, como `PermisoDenegado`)
    """La sesión iba a escribir en la base y no le estaba permitido."""


def _volcaria(sesion: Session, _contexto, _instancias) -> None:
    if sesion.new or sesion.deleted or any(sesion.is_modified(o) for o in sesion.dirty):
        raise EscrituraNegada


def _texto_que_lee(texto: str) -> bool:
    limpio = texto.strip().upper()
    if limpio.startswith("PRAGMA"):
        return "=" not in limpio and "(" not in limpio
    return limpio.startswith(_LECTURAS)


def _ejecutaria(estado: ORMExecuteState) -> None:
    sentencia = estado.statement
    lee = _texto_que_lee(sentencia.text) if isinstance(sentencia, TextClause) else estado.is_select
    if not lee:
        raise EscrituraNegada


@contextmanager
def sin_escribir(sesion: Session) -> Iterator[Session]:
    """La misma sesión, pero sin poder escribir mientras dura el bloque. Quien atrapa
    `EscrituraNegada` deshace la sesión (`rollback`): lo pendiente no llegó a la base."""
    event.listen(sesion, "before_flush", _volcaria)
    event.listen(sesion, "do_orm_execute", _ejecutaria)
    try:
        yield sesion
    finally:
        event.remove(sesion, "do_orm_execute", _ejecutaria)
        event.remove(sesion, "before_flush", _volcaria)
