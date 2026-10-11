"""Equivalencia de la optimizacion de `geometria.orden_de_cadena` y `derivar_electricidad` (SF2).

`orden_de_cadena` precalcula el alto de cada ambiente y la posicion y alto de cada punto una sola
vez por llamada; `derivar_electricidad` calcula los tramos de cada circuito una sola vez. El
resultado debe ser identico al de la version anterior (aqui copiada tal cual como referencia) en
espacios aleatorios con semilla fija y en OF-001.
"""

from __future__ import annotations

import random
from dataclasses import replace
from decimal import Decimal

import pytest

from adapters.espacio import (
    Circuito,
    Coord,
    Espacio,
    Especialidad,
    Punto,
    SuperficiePunto,
    TipoPunto,
)
from adapters.espacio.especialidades.electricidad import derivar_electricidad
from adapters.espacio.geometria import (
    _costo_paso,
    _fuente_de_circuito,
    longitud_tramos,
    orden_de_cadena,
    tramos_de_circuito,
)
from tests.fixtures.espacio_of001 import espacio_of001

D = Decimal


def _alto_anterior(espacio: Espacio, ambiente_id: str) -> D:
    return next(a.alto for a in espacio.ambientes if a.id == ambiente_id)


def _orden_anterior(espacio: Espacio, circuito: Circuito) -> tuple[str, ...]:
    """Copia de `orden_de_cadena` antes de la optimizacion (busqueda lineal del alto por punto)."""
    puntos = {p.id: p for p in espacio.puntos}
    orden = [i for i in circuito.orden if i in puntos]
    faltan = {p.id for p in espacio.puntos if p.circuito_id == circuito.id} - set(orden)
    fuente = _fuente_de_circuito(espacio, circuito)
    if fuente is None:
        return tuple(orden + sorted(faltan))
    if orden:
        ultimo = puntos[orden[-1]]
        actual, alto = ultimo.posicion, _alto_anterior(espacio, ultimo.ambiente_id)
    else:
        actual, alto = fuente.posicion, _alto_anterior(espacio, fuente.ambiente_id)
    while faltan:
        elegido = min(
            faltan,
            key=lambda i: (
                _costo_paso(
                    actual, alto, puntos[i].posicion, _alto_anterior(espacio, puntos[i].ambiente_id)
                ),
                i,
            ),
        )
        faltan.remove(elegido)
        orden.append(elegido)
        actual = puntos[elegido].posicion
        alto = _alto_anterior(espacio, puntos[elegido].ambiente_id)
    return tuple(orden)


def _espacio_aleatorio(semilla: int, n: int) -> Espacio:
    """OF-001 con `n` puntos electricos aleatorios en dos circuitos y altos de ambiente variados."""
    r = random.Random(semilla)
    base = espacio_of001()
    ambientes = tuple(
        replace(a, alto=r.choice([D("2.5"), D("3"), D("2.7")])) for a in base.ambientes
    )
    destinos = [a for a in ambientes if a.id in ("ZA", "ZB", "REC-01")]
    puntos = [p for p in base.puntos if p.especialidad is not Especialidad.ELECTRICIDAD]
    nuevos = []
    for i in range(n):
        a = r.choice(destinos)
        x = a.x0 + (D(r.randint(0, 8)) / 2) % a.largo
        y = a.y0 + (D(r.randint(0, 8)) / 2) % a.ancho
        nuevos.append(
            Punto(
                id=f"E{i:03d}",
                nombre=f"e{i}",
                especialidad=Especialidad.ELECTRICIDAD,
                tipo=r.choice([TipoPunto.TOMACORRIENTE, TipoPunto.ILUMINACION]),
                ambiente_id=a.id,
                superficie=SuperficiePunto.PARED,
                posicion=Coord(x, y, D(r.choice(["0", "0.3", "1"]))),
                fuente_id=None,
                circuito_id=r.choice(["C1", "C2"]),
                especificaciones={"diametro": r.choice(['3/4"', '1/2"'])},
                origen_id="O1",
            )
        )
    c1 = [p.id for p in nuevos if p.circuito_id == "C1"]
    r.shuffle(c1)
    circuitos = (
        Circuito("C1", "T1", 1, (1, 1, 1), "12 AWG", 999, tuple(c1[: r.randint(0, len(c1))])),
        Circuito("C2", "T1", 2, (1, 1, 1), "14 AWG", 999, ()),
    )
    return replace(
        base, ambientes=ambientes, puntos=tuple(puntos + nuevos), circuitos=circuitos, recorridos=()
    )


ESPACIOS = [(s, n) for s in range(25) for n in (0, 1, 5, 12, 30)]


@pytest.mark.parametrize(("semilla", "n"), ESPACIOS)
def test_orden_de_cadena_es_igual_al_de_la_version_anterior(semilla: int, n: int) -> None:
    espacio = _espacio_aleatorio(semilla, n)
    for c in espacio.circuitos:
        assert orden_de_cadena(espacio, c) == _orden_anterior(espacio, c)


def test_orden_de_cadena_de_of001_es_igual_al_de_la_version_anterior() -> None:
    espacio = espacio_of001()
    for c in espacio.circuitos:
        assert orden_de_cadena(espacio, c) == _orden_anterior(espacio, c)


@pytest.mark.parametrize(("semilla", "n"), ESPACIOS[::5])
def test_el_conductor_sale_de_los_tramos_de_cada_circuito(semilla: int, n: int) -> None:
    """Los tramos calculados una sola vez dan el mismo conductor que calcularlos por circuito."""
    espacio = _espacio_aleatorio(semilla, n)
    esperado: dict[str, D] = {}
    for c in espacio.circuitos:
        tramos = tramos_de_circuito(espacio, c)
        if tramos:
            calibre = f"EL-COND-{c.calibre.upper().replace(' ', '-')}"
            metros = longitud_tramos(tramos) * sum(c.conductores)
            esperado[calibre] = esperado.get(calibre, D(0)) + metros
    items = {i.codigo_partida: i for i in derivar_electricidad(espacio)}
    conductores = {k: v for k, v in items.items() if k.startswith("EL-COND-")}
    assert set(conductores) == set(esperado)
    for codigo, metros in esperado.items():
        assert conductores[codigo].cantidad == metros * D("1.10"), codigo
