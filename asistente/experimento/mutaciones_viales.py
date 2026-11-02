"""Sembrador determinista de errores de captura en tramos viales (plan vial, Tarea 11).

Parte de los tramos de una vía correcta y siembra, con semilla fija, un error de cada tipo EV1-EV6
en UN solo campo, para medir cuántos detecta el auditor con un n fijo por tipo. Mismas entradas,
mismos mutantes (como `mutaciones.py`, que no se toca: este archivo es nuevo y no se congela).

* EV1 espesor de una capa multiplicado por 10 (0,05 m leído como 0,50 m);
* EV2 densidad leída sin la coma (2,35 t/m3 queda 235);
* EV3 dosis de un riego multiplicada por 10 (0,40 l/m2 queda 4,00);
* EV4 unidad de UNA partida vial del presupuesto coherente cambiada por otra incompatible (m3 pasa
  a m2). Es el único tipo que muta el presupuesto y no los tramos; sin `presupuesto` no se siembra;
* EV5 dos dígitos contiguos transpuestos en espesor, densidad, dosis, ancho o distancia a la planta
  (0,25 queda 0,52);
* EV6 progresiva final del tramo con el decimal corrido (1,2 km queda 12 km).

Cada mutante cambia exactamente un campo. Un candidato que el modelo rechaza (el `Tramo` se valida
al construirse) o que deja el valor igual se descarta; los mutantes repetidos también. Por eso el n
efectivo de un tipo puede ser menor que `por_tipo`.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from adapters.vial.constantes import PARTIDAS_VIALES
from adapters.vial.modelo import Tramo
from core.contracts.presupuesto import Presupuesto
from core.contracts.unidades import unidades_equivalentes

TIPOS_VIALES = (
    "EV1_espesor_x10",
    "EV2_densidad_coma",
    "EV3_dosis",
    "EV4_unidad",
    "EV5_digitos",
    "EV6_progresiva",
)

_CAMPO_DE_CAPA = {
    "EV1_espesor_x10": "espesor_m",
    "EV2_densidad_coma": "densidad_t_m3",
    "EV3_dosis": "dosis_l_m2",
}
_CAMPOS_DE_CAPA_EV5 = ("espesor_m", "densidad_t_m3", "dosis_l_m2")
_CAMPOS_DE_TRAMO_EV5 = ("ancho_m", "distancia_planta_km")

# (indice de tramo, indice de capa o None, campo, posicion del par de digitos o None)
_Candidato = tuple[int, int | None, str, int | None]


@dataclass(frozen=True)
class MutanteVial:
    tipo: str
    tramos: tuple[Tramo, ...]
    descripcion: str
    #: Presupuesto alterado (solo EV4); `None` si el mutante audita el presupuesto coherente.
    presupuesto: Presupuesto | None = None


def _coma(valor: Decimal) -> str:
    return format(valor, "f").replace(".", ",")


def _valor(tramo: Tramo, capa: int | None, campo: str) -> Decimal | None:
    return getattr(tramo if capa is None else tramo.capas[capa], campo)


def _pares_de_digitos(valor: Decimal) -> list[int]:
    """Posiciones i del texto del valor donde hay dos dígitos contiguos y distintos."""
    texto = format(valor, "f")
    return [
        i
        for i in range(len(texto) - 1)
        if texto[i].isdigit() and texto[i + 1].isdigit() and texto[i] != texto[i + 1]
    ]


def _candidatos(tipo: str, tramos: Sequence[Tramo]) -> list[_Candidato]:
    salida: list[_Candidato] = []
    for t, tramo in enumerate(tramos):
        if tipo == "EV6_progresiva":
            salida.append((t, None, "progresiva_fin_km", None))
        elif tipo == "EV5_digitos":
            for campo in _CAMPOS_DE_TRAMO_EV5:
                valor = _valor(tramo, None, campo)
                if valor is not None:
                    salida += [(t, None, campo, i) for i in _pares_de_digitos(valor)]
        for c in range(len(tramo.capas)):
            if tipo in _CAMPO_DE_CAPA:
                if _valor(tramo, c, _CAMPO_DE_CAPA[tipo]) is not None:
                    salida.append((t, c, _CAMPO_DE_CAPA[tipo], None))
            elif tipo == "EV5_digitos":
                for campo in _CAMPOS_DE_CAPA_EV5:
                    valor = _valor(tramo, c, campo)
                    if valor is not None:
                        salida += [(t, c, campo, i) for i in _pares_de_digitos(valor)]
    return salida


def _nuevo_valor(tipo: str, valor: Decimal, par: int | None) -> Decimal:
    if tipo in ("EV1_espesor_x10", "EV3_dosis", "EV6_progresiva"):
        return valor * 10
    if tipo == "EV2_densidad_coma":
        exponente = valor.as_tuple().exponent
        # Sin la coma: los mismos dígitos como entero (2,35 -> 235).
        return valor.scaleb(-exponente) if isinstance(exponente, int) and exponente < 0 else valor
    texto = list(format(valor, "f"))
    assert par is not None
    texto[par], texto[par + 1] = texto[par + 1], texto[par]
    return Decimal("".join(texto))


def _mutar(
    tipo: str, tramos: Sequence[Tramo], candidato: _Candidato
) -> tuple[tuple[Tramo, ...], str] | None:
    t, c, campo, par = candidato
    tramo = tramos[t]
    valor = _valor(tramo, c, campo)
    assert valor is not None
    nuevo = _nuevo_valor(tipo, valor, par)
    if nuevo == valor:
        return None
    try:
        if c is None:
            tramo_nuevo = replace(tramo, **{campo: nuevo})
            lugar = f"tramo {tramo.id}"
        else:
            capa = replace(tramo.capas[c], **{campo: nuevo})
            capas = (*tramo.capas[:c], capa, *tramo.capas[c + 1 :])
            tramo_nuevo = replace(tramo, capas=capas)
            lugar = f"tramo {tramo.id}, capa {c + 1} ({capa.tipo})"
    except (ValueError, TypeError):
        return None
    mutados = (*tramos[:t], tramo_nuevo, *tramos[t + 1 :])
    return mutados, f"{tipo}: {campo} de {lugar}: {_coma(valor)} pasa a {_coma(nuevo)}"


UNIDADES_INCOMPATIBLES = ("m", "m2", "m3", "t", "l", "kg", "dia", "pieza")


def _mutantes_de_unidad(
    tramos: tuple[Tramo, ...], presupuesto: Presupuesto, semilla: int, por_tipo: int
) -> list[MutanteVial]:
    """EV4: la unidad de una partida vial del presupuesto, por otra; tramos intactos."""
    codigos = {codigo for codigo, _, _ in PARTIDAS_VIALES.values()}
    indices = [i for i, p in enumerate(presupuesto.partidas) if p.item.codigo_partida in codigos]
    azar = random.Random(f"{semilla}:EV4_unidad")
    azar.shuffle(indices)
    salida: list[MutanteVial] = []
    for i in indices[:por_tipo]:
        partida = presupuesto.partidas[i]
        opciones = [
            u for u in UNIDADES_INCOMPATIBLES if not unidades_equivalentes(u, partida.item.unidad)
        ]
        nueva = azar.choice(opciones)
        item = replace(partida.item, unidad=nueva)
        partidas = (
            *presupuesto.partidas[:i],
            replace(partida, item=item),
            *presupuesto.partidas[i + 1 :],
        )
        descripcion = (
            f"EV4_unidad: unidad de la partida {item.codigo_partida} ({item.origen_id}): "
            f"{partida.item.unidad} pasa a {nueva}"
        )
        salida.append(
            MutanteVial("EV4_unidad", tramos, descripcion, replace(presupuesto, partidas=partidas))
        )
    return salida


def sembrar_vial(
    tramos: Sequence[Tramo],
    *,
    semilla: int,
    por_tipo: int,
    presupuesto: Presupuesto | None = None,
) -> list[MutanteVial]:
    """Hasta `por_tipo` mutantes de cada tipo de `TIPOS_VIALES`, en orden de tipo, sin repetidos.

    `presupuesto` es el coherente, armado desde `tramos`: EV4 muta una unidad de él. Sin él, EV4 no
    se siembra (no hay partida que alterar) y no aparece en la lista.
    """
    originales = tuple(tramos)
    salida: list[MutanteVial] = []
    for tipo in TIPOS_VIALES:
        if tipo == "EV4_unidad":
            if presupuesto is not None:
                salida += _mutantes_de_unidad(originales, presupuesto, semilla, por_tipo)
            continue
        azar = random.Random(f"{semilla}:{tipo}")
        candidatos = _candidatos(tipo, originales)
        azar.shuffle(candidatos)
        vistos: set[tuple[Tramo, ...]] = set()
        for candidato in candidatos:
            if len(vistos) >= por_tipo:
                break
            mutado = _mutar(tipo, originales, candidato)
            if mutado is None or mutado[0] in vistos:
                continue
            vistos.add(mutado[0])
            salida.append(MutanteVial(tipo, mutado[0], mutado[1]))
    return salida


def matriz_de_deteccion(
    mutantes: Sequence[MutanteVial], auditar: Callable[[MutanteVial], bool]
) -> dict[str, tuple[int, int]]:
    """(detectados, total) por tipo. `auditar(mutante)` dice si algo lo detecta; quien llama arma el
    auditor: usa `mutante.presupuesto` si existe y, si no, el coherente de los tramos originales."""
    matriz = {tipo: (0, 0) for tipo in TIPOS_VIALES}
    for mutante in mutantes:
        detectados, total = matriz[mutante.tipo]
        matriz[mutante.tipo] = (detectados + (1 if auditar(mutante) else 0), total + 1)
    return matriz
