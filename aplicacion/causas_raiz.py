"""Hallazgos agrupados por causa raíz y avisos de regla no aplicable.

Una fórmula copiada con una fila fija produce un hallazgo por cada partida que la repite: la
causa es una sola y se corrige una vez. La causa de un hallazgo es su regla más la primera
cláusula de su descripción (qué lee y de dónde), sin lo que cambia de un caso a otro: celdas,
números y el valor encontrado. Lo que sigue al primer «;» o al «Efecto:» son detalles del caso.

Los avisos de una regla que no tuvo nada que revisar (R2 y R7 cuando el libro no trae curva de
inversión ni plan de trabajo, UC-05 flujo 2a) no son errores del libro: van aparte.

Lo usan la pantalla de auditoría (`api/rutas/libros.py`) y la herramienta local de medición del
TEG (`scripts/medir_auditoria_libro.py`). No toca el núcleo: agrupa lo que el núcleo ya informó.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

#: El texto con que el núcleo declara una regla sin nada que revisar
#: (`core/verification/reglas.py`, `NO_APLICABLE`).
NO_APLICABLE = "no aplicable"

_ORDEN = {"INFO": 1, "ADVERTENCIA": 2, "ERROR": 3, "CRITICO": 4}
_CELDA = re.compile(r"\b[A-Z]{1,3}\$?\d+\b")
# Una cifra, también con espacio de miles (normal, duro o fino: `9 999,90`), es un solo «#».
_NUMERO = re.compile(r"\d+(?:[   ]\d{3})*(?:[.,]\d+)*")
_VALOR = re.compile(r"\(valor (?:«[^»]*»|[^)]*)\)")


@dataclass(frozen=True, slots=True)
class Causa:
    codigo: str
    severidad: str  # la más grave de sus casos
    descripcion: str  # la de su primer caso
    indices: tuple[int, ...]  # posiciones de sus casos en la lista de hallazgos


def es_no_aplicable(severidad: str, descripcion: str) -> bool:
    return severidad == "INFO" and NO_APLICABLE in descripcion


def patron(descripcion: str) -> str:
    """La causa de un hallazgo: su primera cláusula sin celdas, números ni valor encontrado."""
    causa = descripcion.split("Efecto:")[0].split(";")[0]
    causa = _VALOR.sub("(valor #)", causa)
    return " ".join(_NUMERO.sub("#", _CELDA.sub("#", causa)).split())


def agrupar(filas: Sequence[tuple[str, str, str]]) -> tuple[list[Causa], list[int]]:
    """De `(codigo, severidad, descripcion)` por hallazgo: las causas, en el orden en que aparece
    su primer caso, y las posiciones de los avisos de regla no aplicable."""
    grupos: dict[tuple[str, str], list[int]] = {}
    no_aplicables: list[int] = []
    for i, (codigo, severidad, descripcion) in enumerate(filas):
        if es_no_aplicable(severidad, descripcion):
            no_aplicables.append(i)
        else:
            grupos.setdefault((codigo, patron(descripcion)), []).append(i)
    causas = [
        Causa(
            codigo=filas[indices[0]][0],
            severidad=max((filas[i][1] for i in indices), key=lambda s: _ORDEN.get(s, 0)),
            descripcion=filas[indices[0]][2],
            indices=tuple(indices),
        )
        for indices in grupos.values()
    ]
    return causas, no_aplicables
