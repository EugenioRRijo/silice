"""`aplicacion.obras`: la ficha de la obra sobre una base en memoria (MOD-3a)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from aplicacion.obras import FichaObra, fichas, guardar_ficha
from aplicacion.tablas_obra import crear_esquema_obra


@pytest.fixture
def sesion() -> Iterator[Session]:
    motor = create_engine("sqlite://")
    crear_esquema_obra(motor)
    with Session(motor) as abierta:
        yield abierta
    motor.dispose()


def test_sin_filas_no_hay_fichas(sesion: Session) -> None:
    assert fichas(sesion) == {}


def test_guardar_y_leer(sesion: Session) -> None:
    guardar_ficha(sesion, 4, FichaObra("Contratista Demo, C.A.", "Maracay"))
    guardar_ficha(sesion, 5, FichaObra("", "Valencia"))
    assert fichas(sesion) == {
        4: FichaObra("Contratista Demo, C.A.", "Maracay"),
        5: FichaObra("", "Valencia"),
    }


def test_guardar_otra_vez_reemplaza(sesion: Session) -> None:
    guardar_ficha(sesion, 4, FichaObra("A", "B"))
    guardar_ficha(sesion, 4, FichaObra("C", "D"))
    assert fichas(sesion) == {4: FichaObra("C", "D")}


def test_guardar_no_confirma(sesion: Session) -> None:
    guardar_ficha(sesion, 4, FichaObra("A", "B"))
    sesion.rollback()
    assert fichas(sesion) == {}
