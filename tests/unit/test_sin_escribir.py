"""La guardia `api.sin_escribir` (rediseño F4, Tarea 2b; menor 1 del árbitro).

Mientras dura `sin_escribir(sesion)`, todo lo que la sesión intentaría escribir lanza
`EscrituraNegada` antes de llegar a la base, venga del volcado de la unidad de trabajo, de una
sentencia Core o de un texto SQL; las lecturas pasan. Al salir del bloque la sesión vuelve a
escribir. Oráculos a mano: el número de filas, contado con un `SELECT` propio.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, insert, select, text
from sqlalchemy.orm import Session, registry

from api.sin_escribir import EscrituraNegada, sin_escribir

METADATOS = MetaData()
FILAS = Table("filas", METADATOS, Column("id", Integer, primary_key=True))


class Fila:
    """Una fila mapeada, para el camino del volcado (`session.add`)."""


registry(metadata=METADATOS).map_imperatively(Fila, FILAS)


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    METADATOS.create_all(motor)
    with Session(motor) as abierta:
        abierta.execute(insert(FILAS).values(id=1))
        abierta.commit()
        yield abierta
    motor.dispose()


def _cuantas(sesion: Session) -> int:
    return len(sesion.execute(text("SELECT id FROM filas")).all())


ESCRITURAS = {
    "insert Core": lambda s: s.execute(insert(FILAS).values(id=2)),
    "INSERT con text": lambda s: s.execute(text("INSERT INTO filas (id) VALUES (2)")),
    "WITH…INSERT": lambda s: s.execute(
        text("WITH x AS (SELECT 2 AS id) INSERT INTO filas (id) SELECT id FROM x")
    ),
    "PRAGMA con asignación": lambda s: s.execute(text("PRAGMA user_version = 7")),
    "PRAGMA con asignación, sin espacios": lambda s: s.execute(text("pragma user_version=7")),
    "DELETE con text": lambda s: s.execute(text("DELETE FROM filas")),
}


@pytest.mark.parametrize("escribir", ESCRITURAS.values(), ids=ESCRITURAS.keys())
def test_toda_escritura_por_la_sesion_se_niega(sesion: Session, escribir) -> None:
    with sin_escribir(sesion), pytest.raises(EscrituraNegada):
        escribir(sesion)
    sesion.rollback()
    assert _cuantas(sesion) == 1
    assert sesion.execute(text("PRAGMA user_version")).scalar() == 0


def test_el_volcado_de_un_objeto_nuevo_se_niega(sesion: Session) -> None:
    with sin_escribir(sesion), pytest.raises(EscrituraNegada):
        sesion.add(Fila())
        sesion.flush()
    sesion.rollback()
    assert _cuantas(sesion) == 1


def test_las_lecturas_pasan(sesion: Session) -> None:
    with sin_escribir(sesion):
        assert sesion.execute(select(FILAS.c.id)).scalars().all() == [1]
        assert sesion.execute(select(FILAS.c.id).cte("x").select()).scalars().all() == [1]
        assert sesion.execute(text("SELECT id FROM filas")).scalars().all() == [1]
        assert sesion.execute(text("PRAGMA user_version")).scalar() == 0
        assert sesion.execute(text("EXPLAIN SELECT id FROM filas")).all() != []


def test_al_salir_la_sesion_vuelve_a_escribir(sesion: Session) -> None:
    with sin_escribir(sesion), pytest.raises(EscrituraNegada):
        sesion.execute(insert(FILAS).values(id=2))
    sesion.rollback()
    sesion.execute(insert(FILAS).values(id=2))
    sesion.add(Fila())
    sesion.commit()
    assert _cuantas(sesion) == 3
