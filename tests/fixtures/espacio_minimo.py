"""Espacios pequeños para las pruebas de R15 y R16 (S3-5): cada fila declara solo lo que prueba.

Todo en metros y `Decimal`; los ambientes arrancan en (0, 0) salvo que se diga otra cosa. Los
orígenes de medida no se registran: R15 y R16 no los leen (los marca R8).
"""

from __future__ import annotations

from decimal import Decimal

from adapters.espacio import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    Punto,
    SuperficiePunto,
    TipoFuente,
    TipoPunto,
)

D = Decimal


def ambiente(id_: str, x0="0", y0="0", largo="4", ancho="3", alto="2.5") -> Ambiente:
    return Ambiente(id_, f"Ambiente {id_}", D(x0), D(y0), D(largo), D(ancho), D(alto), "O1")


def punto_de_datos(id_: str, x, y="1", z="0.3", fuente: str | None = None, amb="A") -> Punto:
    return Punto(
        id=id_, nombre=f"Punto {id_}", especialidad=Especialidad.DATOS, tipo=TipoPunto.DATOS,
        ambiente_id=amb, superficie=SuperficiePunto.PARED, posicion=Coord(D(x), D(y), D(z)),
        origen_id="O1", fuente_id=fuente,
    )


def toma(id_: str, x, y="1", z="0.3", amb="A") -> Punto:
    return Punto(
        id=id_, nombre=f"Toma {id_}", especialidad=Especialidad.ELECTRICIDAD,
        tipo=TipoPunto.TOMACORRIENTE, ambiente_id=amb, superficie=SuperficiePunto.PARED,
        posicion=Coord(D(x), D(y), D(z)), origen_id="O1",
    )


def rack(id_: str = "R1", x="0", y="0", z="0", amb="A") -> Fuente:
    return Fuente(
        id=id_, especialidad=Especialidad.DATOS, tipo=TipoFuente.RACK, ambiente_id=amb,
        posicion=Coord(D(x), D(y), D(z)), origen_id="O1",
    )


def espacio(ambientes=(), puntos=(), fuentes=()) -> Espacio:
    """Un espacio sin orígenes registrados (R15 y R16 no los leen)."""
    return Espacio(ambientes=tuple(ambientes), puntos=tuple(puntos), fuentes=tuple(fuentes))
