"""La tasa del cierre del mes (plan vial, Tarea 4b, respuesta de Eugenio a la pregunta 14).

Datos FICTICIOS. Oraculos a mano: con tasas el 03/11 (40), el 28/11 (42) y el 01/12 (45), la del
cierre de 2026-11 es la del 28/11, 42 (la ultima con fecha dentro del mes; la del 01/12 es de otro
mes). Con una sola tasa el 31/10, noviembre no tiene tasa del cierre aunque la busqueda general
(«la mas reciente hasta esa fecha») la devolveria.

Ronda 2 (arbitro): la busqueda general del nucleo rechaza una tasa a mas de 7 dias (S1-R2), pero la
del cierre es la ultima DENTRO del mes, aunque este lejos del ultimo dia: con una sola tasa el 03/11
(40), la de noviembre es esa, 27 dias antes del 30/11.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from aplicacion.tasa_del_dia import SinTasaDelDia, equivalencia_del_cierre, tasa_del_cierre
from tests.fixtures import costo_propio as cp

SIN_TASA_NOVIEMBRE = (
    "No hay tasa del BCV publicada en 2026-11 para convertir a Bs. Cárguela en Índices y vuelva a "
    "intentarlo."
)


@pytest.fixture
def caso(tmp_path: Path) -> Iterator[Session]:
    with cp.carpeta_del_caso(tmp_path) as sesion:
        yield sesion


def test_tasa_del_cierre_es_la_ultima_del_mes(caso) -> None:
    cp.tasas(caso, {date(2026, 11, 3): "40", date(2026, 11, 28): "42", date(2026, 12, 1): "45"})
    tasa = tasa_del_cierre(caso, "2026-11", "Bs")
    assert (tasa.valor, tasa.fecha) == (Decimal("42"), date(2026, 11, 28))


def test_el_ultimo_dia_del_mes_cuenta(caso) -> None:
    cp.tasas(caso, {date(2026, 11, 3): "40", date(2026, 11, 30): "43"})
    assert tasa_del_cierre(caso, "2026-11", "Bs").fecha == date(2026, 11, 30)


def test_diciembre_cierra_el_31(caso) -> None:
    cp.tasas(caso, {date(2026, 12, 31): "50", date(2027, 1, 1): "51"})
    assert tasa_del_cierre(caso, "2026-12", "USD").valor == Decimal("50")


def test_sin_tasa_en_el_mes_falla(caso) -> None:
    cp.tasas(caso, {date(2026, 10, 31): "39"})
    with pytest.raises(SinTasaDelDia) as error:
        tasa_del_cierre(caso, "2026-11", "Bs")
    assert str(error.value) == SIN_TASA_NOVIEMBRE


def test_sin_ninguna_tasa_falla_igual(caso) -> None:
    with pytest.raises(SinTasaDelDia) as error:
        tasa_del_cierre(caso, "2026-11", "Bs")
    assert str(error.value) == SIN_TASA_NOVIEMBRE


@pytest.mark.parametrize("periodo", ["2026-13", "2026-1", "noviembre", ""])
def test_periodo_invalido(caso, periodo: str) -> None:
    with pytest.raises(ValueError, match="AAAA-MM"):
        tasa_del_cierre(caso, periodo, "Bs")


def test_una_tasa_lejos_del_cierre_dentro_del_mes_sirve(caso) -> None:
    cp.tasas(caso, {date(2026, 11, 3): "40"})
    tasa = tasa_del_cierre(caso, "2026-11", "Bs")
    assert (tasa.valor, tasa.fecha) == (Decimal("40"), date(2026, 11, 3))


def test_la_primera_del_mes_sirve(caso) -> None:
    cp.tasas(caso, {date(2026, 10, 31): "39", date(2026, 11, 1): "41"})
    assert tasa_del_cierre(caso, "2026-11", "Bs").fecha == date(2026, 11, 1)


def test_la_del_mes_lejos_gana_a_una_del_mes_anterior(caso) -> None:
    """Con tasas el 31/10 (39) y el 03/11 (40): noviembre da la del 03/11; diciembre, sin ninguna
    propia, falla con el mensaje exacto aunque la del 03/11 sea la mas reciente."""
    cp.tasas(caso, {date(2026, 10, 31): "39", date(2026, 11, 3): "40"})
    tasa = tasa_del_cierre(caso, "2026-11", "Bs")
    assert (tasa.valor, tasa.fecha) == (Decimal("40"), date(2026, 11, 3))
    with pytest.raises(SinTasaDelDia) as error:
        tasa_del_cierre(caso, "2026-12", "Bs")
    assert str(error.value) == (
        "No hay tasa del BCV publicada en 2026-12 para convertir a Bs. Cárguela en Índices y "
        "vuelva a intentarlo."
    )


@pytest.mark.parametrize(
    ("periodo", "ultimo"),
    [
        ("2026-11", date(2026, 11, 30)),
        ("2026-12", date(2026, 12, 31)),
        ("2028-02", date(2028, 2, 29)),
    ],
)
def test_un_solo_ultimo_dia_del_mes(periodo: str, ultimo: date) -> None:
    from produccion.costos import ultimo_dia_del_mes

    assert ultimo_dia_del_mes(periodo) == ultimo


def test_equivalencia_del_cierre(caso) -> None:
    """600 USD con la tasa del cierre (42 del 28/11) son 25.200 Bs, con la cuenta reconstruible."""
    cp.tasas(caso, {date(2026, 11, 3): "40", date(2026, 11, 28): "42"})
    eq = equivalencia_del_cierre(caso, Decimal("600"), "USD", "Bs", "2026-11")
    assert eq.convertido == Decimal("25200")
    assert (eq.tasa, eq.fecha_tasa, eq.moneda_original, eq.moneda) == (
        Decimal("42"),
        date(2026, 11, 28),
        "USD",
        "Bs",
    )
