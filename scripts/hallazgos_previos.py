"""Hallazgos que el libro base ya tenía: cómo se descuentan (actas del 2026-11-25).

Una sola regla para la cifra oficial de `medir_inyeccion.py` y para `medir_auditoria_libro.py
calcular --clave`: una falla sembrada no se acredita a lo que el libro sin sembrar ya señalaba.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Collection, Sequence
from dataclasses import replace

from aplicacion.causas_raiz import agrupar, patron
from scripts.medir_auditoria_libro import _celda, _no_aplica

#: Reglas que juntan en UN hallazgo todas las celdas de una hoja o de una sección (leído en las
#: reglas congeladas, sin cambiarlas): L5 (`_l5`, fórmulas con #REF! y que leen otro libro, por
#: hoja; nombres y vínculos rotos; `reglas_calculo`, celdas que dan error al calcular, por hoja) y
#: L7 (`_l7`, fórmulas con medidas escritas, por sección de MEDICIONES). Una celda sembrada más
#: cambia la tupla entera de un hallazgo así; por eso estas se descuentan celda por celda.
REGLAS_AGRUPADAS = frozenset({"L5", "L7"})
#: El L1 de AUX (`_l1_aux`) junta, por APU, las filas fijas y el escombro que lee la hoja AUX; los
#: demás L1 comparan una celda leída con la correcta. Se reconoce por su efecto, que es fijo.
EFECTO_L1_AUX = "Efecto: PROCURA (lista de compras y escombro) no corresponde al presupuesto."


def agrupa_por_hoja(h) -> bool:
    """Si el hallazgo junta las celdas de una hoja o sección (se descuenta por celda)."""
    return h.regla in REGLAS_AGRUPADAS or (h.regla == "L1" and EFECTO_L1_AUX in h.descripcion)


def _grupo(h) -> str:
    return "L1 de AUX" if h.regla == "L1" else h.regla


def _clave_entera(h) -> tuple[str, tuple[str, ...]]:
    """Regla y celdas de origen normalizadas (comillas, `$`, mayúsculas) y ordenadas."""
    return h.regla, tuple(sorted(_celda(str(c)) for c in h.origen_ids))


def _previos_sin_celdas(base: Sequence, auditados: Sequence) -> set[int]:
    """Posiciones de los hallazgos sin celdas de `auditados` que ya estaban en el libro base: se
    emparejan primero por regla y descripción exacta y después por regla y `patron` de la
    descripción (una cifra que cambió), nunca por el orden en que llegan."""
    exactas = Counter(
        (h.regla, h.descripcion) for h in base if not h.origen_ids and not _no_aplica(h)
    )
    sin_celdas = [i for i, h in enumerate(auditados) if not h.origen_ids and not _no_aplica(h)]
    previos: set[int] = set()
    for i in sin_celdas:
        clave = (auditados[i].regla, auditados[i].descripcion)
        if exactas[clave] > 0:
            exactas[clave] -= 1
            previos.add(i)
    por_patron: Counter[tuple[str, str]] = Counter()
    for (regla, descripcion), n in exactas.items():
        por_patron[(regla, patron(descripcion))] += n
    for i in sin_celdas:
        clave = (auditados[i].regla, patron(auditados[i].descripcion))
        if i not in previos and por_patron[clave] > 0:
            por_patron[clave] -= 1
            previos.add(i)
    return previos


def _celdas_nuevas(base: Sequence, auditados: Sequence) -> list[tuple[str, ...] | None]:
    """Por cada hallazgo de `auditados`, las celdas que trae nuevas, o `None` si no trae nada
    nuevo o es un aviso «no aplicable»:

    - si agrupa por hoja o sección (`agrupa_por_hoja`), solo sus celdas que ningún hallazgo
      previo agrupado de la misma regla citaba: una celda sembrada más no rescata las que ya
      estaban;
    - si no, todas o ninguna: se descuenta solo si coincide entero (regla y mismas celdas, como
      multiconjunto) con uno previo. Así una celda que un previo citaba solo como referencia (el
      destino de un L3, la celda correcta de un L1) no esconde una falla sembrada después en ella;
    - sin celdas, por la descripción (`_previos_sin_celdas`)."""
    base = [h for h in base if not _no_aplica(h)]
    marcables = [None if _no_aplica(h) else h for h in auditados]
    citadas: dict[str, set[str]] = defaultdict(set)
    enteras: Counter[tuple[str, tuple[str, ...]]] = Counter()
    for h in base:
        if h.origen_ids and agrupa_por_hoja(h):
            citadas[_grupo(h)].update(_celda(str(c)) for c in h.origen_ids)
        elif h.origen_ids:
            enteras[_clave_entera(h)] += 1
    sin_celdas_previos = _previos_sin_celdas(base, auditados)
    nuevas: list[tuple[str, ...] | None] = []
    for i, h in enumerate(marcables):
        if h is None:
            nuevas.append(None)
        elif not h.origen_ids:
            nuevas.append(None if i in sin_celdas_previos else ())
        elif agrupa_por_hoja(h):
            propias = tuple(c for c in h.origen_ids if _celda(str(c)) not in citadas[_grupo(h)])
            nuevas.append(propias or None)
        elif enteras[_clave_entera(h)] > 0:
            enteras[_clave_entera(h)] -= 1
            nuevas.append(None)
        else:
            nuevas.append(tuple(h.origen_ids))
    return nuevas


def hallazgos_nuevos(base: Sequence, auditados: Sequence) -> list:
    """Los hallazgos de `auditados` que traen algo que el libro base no daba, cada uno con solo
    sus celdas nuevas (`_celdas_nuevas`; con celdas no se mira la descripción, que puede solo
    cambiar una cifra). Es la regla de la cifra oficial (`medir_inyeccion`) y la de
    `calcular --clave`."""
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
