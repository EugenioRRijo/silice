"""Hallazgos que el libro base ya tenía: el descuento por celda (actas del 2026-11-25).

Una sola regla para la cifra oficial de `medir_inyeccion.py` y para `medir_auditoria_libro.py
calcular --clave`: una falla sembrada no se acredita a lo que el libro sin sembrar ya señalaba.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Collection, Sequence
from dataclasses import replace

from aplicacion.causas_raiz import agrupar
from scripts.medir_auditoria_libro import _celda, _no_aplica


def _celdas_nuevas(base: Sequence, auditados: Sequence) -> list[tuple[str, ...] | None]:
    """Por cada hallazgo de `auditados`, las celdas de origen que ningún hallazgo previo de la
    misma regla citaba (normalizadas con `_celda`), o `None` si no trae nada nuevo o es un aviso
    «no aplicable». Se descuenta por celda, no por la tupla completa: un hallazgo agrupado por hoja
    (L5, L7, L1 de AUX) que suma una celda no rescata las que ya estaban. Un hallazgo sin celdas se
    descuenta uno por uno contra los previos de su regla sin celdas."""
    citadas: dict[str, set[str]] = defaultdict(set)
    sin_celdas: Counter[str] = Counter()
    for h in base:
        if _no_aplica(h):
            continue
        citadas[h.regla].update(_celda(str(c)) for c in h.origen_ids)
        if not h.origen_ids:
            sin_celdas[h.regla] += 1
    nuevas: list[tuple[str, ...] | None] = []
    for h in auditados:
        if _no_aplica(h):
            nuevas.append(None)
        elif not h.origen_ids:
            previo = sin_celdas[h.regla] > 0
            sin_celdas[h.regla] -= previo
            nuevas.append(None if previo else ())
        else:
            propias = tuple(c for c in h.origen_ids if _celda(str(c)) not in citadas[h.regla])
            nuevas.append(propias or None)
    return nuevas


def hallazgos_nuevos(base: Sequence, auditados: Sequence) -> list:
    """Los hallazgos de `auditados` que traen algo que el libro base no daba, cada uno con solo
    sus celdas nuevas (`_celdas_nuevas`; no se mira la descripción, que puede solo cambiar una
    cifra). Es la regla de la cifra oficial (`medir_inyeccion`) y la de `calcular --clave`."""
    return [
        replace(h, origen_ids=c)
        for h, c in zip(auditados, _celdas_nuevas(base, auditados), strict=True)
        if c is not None
    ]


def sin_previos(base: Sequence, auditados: Sequence) -> tuple[list, int, frozenset[int]]:
    """`auditados` con solo las celdas nuevas de cada hallazgo (los previos quedan sin celdas; la
    regla, la severidad y la descripción no cambian, así que las filas de la planilla se agrupan y
    se numeran igual), cuántos hallazgos marcables no traían nada nuevo y las posiciones de los
    que sí. Así una falla sembrada no se acredita a lo que el libro ya tenía."""
    nuevas = _celdas_nuevas(base, auditados)
    recortados = [
        h if _no_aplica(h) else replace(h, origen_ids=c or ())
        for h, c in zip(auditados, nuevas, strict=True)
    ]
    marcables = sum(1 for h in auditados if not _no_aplica(h))
    con_nuevos = frozenset(i for i, c in enumerate(nuevas) if c is not None)
    return recortados, marcables - len(con_nuevos), con_nuevos


def _miembros(hallazgos: Sequence, sin_agrupar: bool) -> list[tuple[int, ...]]:
    """Las posiciones de los hallazgos de cada fila de la planilla, en el orden de su N°: la misma
    numeración de `filas_de_hallazgos` y `causas_de_hallazgos`."""
    if sin_agrupar:
        return [(i,) for i, h in enumerate(hallazgos) if not _no_aplica(h)]
    causas, _ = agrupar([(h.regla, h.severidad.name, h.descripcion) for h in hallazgos])
    return [c.indices for c in causas]


def filas_con_nuevos(
    hallazgos: Sequence, nuevos: Collection[int], *, sin_agrupar: bool
) -> set[int]:
    """Los N° de las filas de la planilla que traen al menos un hallazgo nuevo."""
    return {
        numero
        for numero, miembros in enumerate(_miembros(hallazgos, sin_agrupar), start=1)
        if any(i in nuevos for i in miembros)
    }
