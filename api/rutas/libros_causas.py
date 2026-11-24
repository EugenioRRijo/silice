"""Hallazgos agrupados por causa raíz en la respuesta de `/v1/libros/auditoria`.

Se separa de `api/rutas/libros.py` para que ese módulo no pase el tope de líneas
(`tests/unit/test_arquitectura.py`). La lógica de agrupar vive en `aplicacion/causas_raiz.py`.
"""

from __future__ import annotations

from pydantic import BaseModel

from aplicacion.causas_raiz import agrupar
from aplicacion.nombres_reglas import nombre_de_regla

__all__ = ["CausaRaizRespuesta", "causas_de_tabla"]


class CausaRaizRespuesta(BaseModel):
    """Hallazgos con la misma regla y la misma causa (`aplicacion/causas_raiz.py`): una fórmula
    copiada con una fila fija es una causa con un caso por partida. `indices` son las posiciones
    de sus casos en `hallazgos`; `descripcion` es la del primero y `severidad`, la más grave."""

    codigo: str
    nombre_regla: str = ""
    severidad: str
    descripcion: str
    ocurrencias: int
    indices: list[int]


def causas_de_tabla(tabla) -> tuple[list[CausaRaizRespuesta], list[int]]:
    causas, no_aplicables = agrupar([(h.codigo, h.severidad, h.descripcion) for h in tabla])
    return [
        CausaRaizRespuesta(
            codigo=c.codigo,
            nombre_regla=nombre_de_regla(c.codigo),
            severidad=c.severidad,
            descripcion=c.descripcion,
            ocurrencias=len(c.indices),
            indices=list(c.indices),
        )
        for c in causas
    ], no_aplicables
