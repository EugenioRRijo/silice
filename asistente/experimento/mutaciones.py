"""Sembrador determinista de errores (S4 §9.5, medicion controlada del auditor).

A las REFERENCIAS de evaluacion aplica una mutacion de cada tipo E1-E8 con semilla fija, para medir
la deteccion con un n fijo por tipo, independiente de lo que haga el modelo. Mismas entradas, mismos
mutantes. Cada mutante se elabora y audita igual que una corrida. Una mutacion que no aplica a una
tarea (E1 sin partidas, E8 sin sembrados) se salta: los `n` mutantes se reparten por turno entre las
tareas donde SI aplica (protocolo: «hasta dos por tarea» se declara como «n por tipo»).

* E1 cambia el codigo de una partida por otro del catalogo con unidad equivalente;
* E2 cambia su unidad por una incompatible;
* E3 mueve un punto 0,05 m en x (empareja y difiere);
* E4 saca un punto 0,05 m por su muro (empareja y queda fuera de todo ambiente);
* E5 quita la fuente de un punto (o su circuito, si lo tiene);
* E6 quita un punto y su recorrido;
* E7 duplica un punto y su recorrido;
* E8 copia el valor sembrado de la ficha en su campo.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from adapters.espacio import Coord, Espacio, ModoRecorrido, Recorrido
from asistente.experimento.modelo import Referencia
from core.contracts.item_computo import ItemComputo
from core.contracts.unidades import unidades_equivalentes

DESPLAZAMIENTO = Decimal("0.05")
UNIDADES_INCOMPATIBLES = ("kg", "dia", "m2", "m3", "m", "pieza", "punto")


@dataclass(frozen=True, slots=True)
class Mutante:
    tipo: str
    tarea: str
    indice: int
    espacio: Espacio
    items: tuple[ItemComputo, ...]


def _azar(semilla: int, tipo: str, tarea: str, indice: int) -> random.Random:
    return random.Random(f"{semilla}:{tipo}:{tarea}:{indice}")


def _sin_punto(espacio: Espacio, punto_id: str) -> Espacio:
    return replace(
        espacio,
        puntos=tuple(p for p in espacio.puntos if p.id != punto_id),
        recorridos=tuple(r for r in espacio.recorridos if r.punto_id != punto_id),
    )


def _muro(punto, ambiente) -> tuple[str, int]:
    """Eje (x o y) y sentido en que el punto sale del ambiente por el muro en que esta."""
    c = punto.posicion
    if c.y == ambiente.y0:
        return "y", -1
    if c.y == ambiente.y0 + ambiente.ancho:
        return "y", 1
    if c.x == ambiente.x0:
        return "x", -1
    if c.x == ambiente.x0 + ambiente.largo:
        return "x", 1
    return "", 0


def mutar(
    tipo: str,
    tarea: str,
    referencia: Referencia,
    semilla: int,
    indice: int,
    catalogo: Sequence[tuple[str, str]] = (),
) -> Mutante | None:
    """El mutante `indice` del `tipo` sobre la referencia, o `None` si no aplica a la tarea.

    `catalogo` = (codigo, unidad) de las partidas del catalogo, para E1.
    """
    azar = _azar(semilla, tipo, tarea, indice)
    espacio, items = referencia.espacio, list(referencia.items)
    puntos = sorted(espacio.puntos, key=lambda p: p.id)
    if tipo in ("E1", "E2"):
        if not items:
            return None
        i = azar.randrange(len(items))
        item = items[i]
        if tipo == "E1":
            otros = sorted(
                c
                for c, u in catalogo
                if c != item.codigo_partida and unidades_equivalentes(u, item.unidad)
            )
            if not otros:
                return None
            items[i] = replace(item, codigo_partida=azar.choice(otros))
        else:
            unidades = [
                u for u in UNIDADES_INCOMPATIBLES if not unidades_equivalentes(u, item.unidad)
            ]
            items[i] = replace(item, unidad=azar.choice(unidades))
    elif tipo == "E8":
        if not referencia.sembrados:
            return None
        s = referencia.sembrados[azar.randrange(len(referencia.sembrados))]
        try:
            espacio = _sembrar(espacio, s)
        except ValueError:  # p. ej. un ambiente de ancho cero no se puede ni construir
            return None
    else:
        if not puntos:
            return None
        punto = azar.choice(puntos)
        if tipo == "E3":
            c = punto.posicion
            nuevo = replace(punto, posicion=Coord(c.x + DESPLAZAMIENTO, c.y, c.z))
            espacio = replace(
                espacio, puntos=tuple(nuevo if p.id == punto.id else p for p in espacio.puntos)
            )
        elif tipo == "E4":
            ambiente = next(a for a in espacio.ambientes if a.id == punto.ambiente_id)
            eje, sentido = _muro(punto, ambiente)
            if not eje:
                return None
            c = punto.posicion
            delta = DESPLAZAMIENTO * sentido
            nueva = Coord(
                c.x + (delta if eje == "x" else 0), c.y + (delta if eje == "y" else 0), c.z
            )
            nuevo = replace(punto, posicion=nueva)
            espacio = replace(
                espacio, puntos=tuple(nuevo if p.id == punto.id else p for p in espacio.puntos)
            )
        elif tipo == "E5":
            if punto.circuito_id is not None:
                nuevo = replace(punto, circuito_id=None)
            elif punto.fuente_id is not None:
                nuevo = replace(punto, fuente_id=None)
            else:
                return None
            espacio = replace(
                espacio, puntos=tuple(nuevo if p.id == punto.id else p for p in espacio.puntos)
            )
        elif tipo == "E6":
            espacio = _sin_punto(espacio, punto.id)
        elif tipo == "E7":
            copia = replace(punto, id=f"{punto.id}-DUP")
            extra = Recorrido(id=f"R-{copia.id}", modo=ModoRecorrido.PROPUESTO, punto_id=copia.id)
            espacio = replace(
                espacio, puntos=(*espacio.puntos, copia), recorridos=(*espacio.recorridos, extra)
            )
        else:
            raise ValueError(f"tipo de error desconocido: {tipo!r}")
    return Mutante(tipo, tarea, indice, espacio, tuple(items))


def _sembrar(espacio: Espacio, s) -> Espacio:
    valor = s.valor
    if s.clase == "punto":
        puntos = []
        for p in espacio.puntos:
            if p.id == s.id_referencia:
                c = p.posicion
                nueva = Coord(
                    valor if s.campo == "x" else c.x,
                    valor if s.campo == "y" else c.y,
                    valor if s.campo == "z" else c.z,
                )
                p = replace(p, posicion=nueva)
            puntos.append(p)
        return replace(espacio, puntos=tuple(puntos))
    ambientes = tuple(
        replace(a, **{s.campo: valor}) if a.id == s.id_referencia else a for a in espacio.ambientes
    )
    return replace(espacio, ambientes=ambientes)


def generar(
    tipo: str,
    referencias: Mapping[str, Referencia],
    semilla: int,
    n: int,
    catalogo: Sequence[tuple[str, str]] = (),
) -> list[Mutante]:
    """`n` mutantes del `tipo`, repartidos por turno entre las tareas (por id) donde aplica."""
    tareas = sorted(referencias)
    aplicables = [t for t in tareas if mutar(tipo, t, referencias[t], semilla, 0, catalogo)]
    if not aplicables:
        return []
    mutantes: list[Mutante] = []
    for i in range(n):
        tarea = aplicables[i % len(aplicables)]
        mutante = mutar(tipo, tarea, referencias[tarea], semilla, i // len(aplicables), catalogo)
        if mutante is not None:
            mutantes.append(mutante)
    return mutantes
