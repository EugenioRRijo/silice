"""Sembrador determinista de errores (S4 §9.5, medicion controlada del auditor).

A las REFERENCIAS de evaluacion aplica una mutacion de cada tipo E1-E8 con semilla fija, para medir
la deteccion con un n fijo por tipo, independiente de lo que haga el modelo. Mismas entradas, mismos
mutantes. Cada mutante se elabora y audita igual que una corrida. Una mutacion que no aplica a una
tarea (E1 sin partidas, E8 sin sembrados) se salta: los `n` mutantes se reparten por turno entre las
tareas donde SI aplica (protocolo: «hasta dos por tarea» se declara como «n por tipo»). Los mutantes
repetidos se descartan (ver `generar`): el n efectivo puede ser menor que `n`.

* E1 cambia el codigo de una partida por otro del catalogo con unidad equivalente;
* E2 cambia su unidad por una incompatible;
* E3 mueve un punto 0,05 m en x o en y, en un sentido que lo deja DENTRO de su ambiente (empareja,
  difiere y no es ademas E4); si ningun sentido lo deja dentro, el mutante se descarta;
* E4 saca un punto 0,05 m por su muro (empareja y queda fuera de todo ambiente);
* E5 quita la fuente de un punto (o su circuito, si lo tiene);
* E6 quita un punto y su recorrido;
* E7 duplica un punto y su recorrido;
* E8 copia el valor sembrado de la ficha en su campo (ambiente, fuente, punto o partida).

Un mutante identico a la referencia (p. ej. un sembrado cuyo valor ya es el de la referencia) no es
un error: se descarta (`mutar` devuelve `None`).
"""

from __future__ import annotations

import random
from collections.abc import Iterator, Mapping, Sequence
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
            espacio, items = _sembrar(espacio, items, s)
        except ValueError:  # p. ej. un ambiente de ancho cero no se puede ni construir
            return None
    else:
        if not puntos:
            return None
        punto = azar.choice(puntos)
        if tipo == "E3":
            nueva = _desplazado_dentro(punto, espacio, azar)
            if nueva is None:
                return None
            nuevo = replace(punto, posicion=nueva)
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
    if espacio == referencia.espacio and tuple(items) == tuple(referencia.items):
        return None  # identico a la referencia: no hay error que medir (M3)
    return Mutante(tipo, tarea, indice, espacio, tuple(items))


def _desplazado_dentro(punto, espacio: Espacio, azar: random.Random) -> Coord | None:
    """El punto movido `DESPLAZAMIENTO` en x o en y, en un sentido que lo deja dentro de su
    ambiente (I2: el mutante E3 no debe ser ademas E4). El azar elige entre los sentidos validos;
    `None` si ninguno lo deja dentro."""
    ambiente = next((a for a in espacio.ambientes if a.id == punto.ambiente_id), None)
    if ambiente is None:
        return None
    c = punto.posicion
    candidatas = [
        Coord(c.x + dx, c.y + dy, c.z)
        for dx, dy in (
            (DESPLAZAMIENTO, 0),
            (-DESPLAZAMIENTO, 0),
            (0, DESPLAZAMIENTO),
            (0, -DESPLAZAMIENTO),
        )
    ]
    # estrictamente dentro (tolerancia 0): ni siquiera la de §6.1 lo saca por un borde
    validas = [n for n in candidatas if ambiente.contiene(n, Decimal(0))]
    return azar.choice(validas) if validas else None


def _con_coordenada(c: Coord, campo: str, valor: Decimal) -> Coord:
    return Coord(
        valor if campo == "x" else c.x,
        valor if campo == "y" else c.y,
        valor if campo == "z" else c.z,
    )


def _sembrar(espacio: Espacio, items: list[ItemComputo], s) -> tuple[Espacio, list[ItemComputo]]:
    """El valor sembrado `s` copiado en su elemento de la referencia (ambiente, fuente, punto o
    partida). Otra clase: `NotImplementedError`, no un mutante silenciosamente igual (M3)."""
    valor = s.valor
    if s.clase == "punto":
        puntos = tuple(
            replace(p, posicion=_con_coordenada(p.posicion, s.campo, valor))
            if p.id == s.id_referencia
            else p
            for p in espacio.puntos
        )
        return replace(espacio, puntos=puntos), items
    if s.clase == "fuente":
        fuentes = tuple(
            replace(f, posicion=_con_coordenada(f.posicion, s.campo, valor))
            if f.id == s.id_referencia
            else f
            for f in espacio.fuentes
        )
        return replace(espacio, fuentes=fuentes), items
    if s.clase == "ambiente":
        ambientes = tuple(
            replace(a, **{s.campo: valor}) if a.id == s.id_referencia else a
            for a in espacio.ambientes
        )
        return replace(espacio, ambientes=ambientes), items
    if s.clase == "partida":
        if s.campo != "cantidad":
            raise NotImplementedError(f"sembrado de partida en {s.campo!r}: solo `cantidad`")
        return espacio, [
            replace(i, cantidad=valor) if i.origen_id == s.id_referencia else i for i in items
        ]
    raise NotImplementedError(f"sembrado de la clase {s.clase!r}: no se sabe mutarla")


#: indices seguidos sin un mutante nuevo tras los cuales una tarea se da por agotada (el azar de
#: `mutar` elige entre pocas opciones: con 200 intentos sin novedad el espacio ya se vio todo)
PACIENCIA = 200


def _contenido(m: Mutante) -> str:
    """Lo que hace distinto a un mutante: su espacio y sus partidas, nunca su indice."""
    return repr((m.espacio, m.items))


def generar(
    tipo: str,
    referencias: Mapping[str, Referencia],
    semilla: int,
    n: int,
    catalogo: Sequence[tuple[str, str]] = (),
) -> list[Mutante]:
    """Hasta `n` mutantes DISTINTOS del `tipo`, repartidos por turno entre las tareas (por id).

    El auditor es determinista: dos mutantes iguales no son dos ensayos independientes, asi que se
    avanza el indice hasta tener un mutante de contenido nuevo (espacio e items). Una tarea que deja
    de dar mutantes nuevos (o a la que la mutacion no aplica) sale del turno. Si el espacio de
    mutantes distintos se agota antes de `n`, el resultado trae MENOS: su longitud es el n efectivo
    del tipo (Wilson se calcula con ese n, no con 24).
    """
    siguientes = {
        t: _distintos(tipo, t, referencias[t], semilla, catalogo) for t in sorted(referencias)
    }
    mutantes: list[Mutante] = []
    turno = list(siguientes)
    while turno and len(mutantes) < n:
        for tarea in list(turno):
            if len(mutantes) >= n:
                break
            mutante = next(siguientes[tarea], None)
            if mutante is None:
                turno.remove(tarea)
            else:
                mutantes.append(mutante)
    return mutantes


def _distintos(
    tipo: str,
    tarea: str,
    referencia: Referencia,
    semilla: int,
    catalogo: Sequence[tuple[str, str]],
) -> Iterator[Mutante]:
    vistos: set[str] = set()
    sin_novedad = 0
    indice = 0
    while sin_novedad < PACIENCIA:
        mutante = mutar(tipo, tarea, referencia, semilla, indice, catalogo)
        indice += 1
        clave = _contenido(mutante) if mutante is not None else None
        if clave is None or clave in vistos:
            sin_novedad += 1
            continue
        vistos.add(clave)
        sin_novedad = 0
        yield mutante
