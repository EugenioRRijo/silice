"""Hallazgos agrupados por causa raíz en la respuesta de `/v1/libros/auditoria`.

Se separa de `api/rutas/libros.py` para que ese módulo no pase el tope de líneas
(`tests/unit/test_arquitectura.py`). La lógica de agrupar vive en `aplicacion/causas_raiz.py`.
"""

from __future__ import annotations

from pydantic import BaseModel

from api.presentacion import exacto_o_nada
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
    #: La traza para juzgar sin abrir el código: todas las celdas de sus casos (sin repetir) y el
    #: valor que encontró la regla frente al que esperaba, del primer caso que los trae.
    celdas: list[str] = []
    observado: str | None = None
    esperado: str | None = None


def causas_de_tabla(tabla, informe=()) -> tuple[list[CausaRaizRespuesta], list[int]]:
    """`tabla` y `informe` (los `Hallazgo` del núcleo) van en el mismo orden
    (`fusion.proceso._tabla`)."""
    causas, no_aplicables = agrupar([(h.codigo, h.severidad, h.descripcion) for h in tabla])
    informe = list(informe)
    respuesta = []
    for c in causas:
        con_valores = [informe[i] for i in c.indices if i < len(informe)
                       and informe[i].valor_observado is not None]
        primero = con_valores[0] if con_valores else None
        respuesta.append(CausaRaizRespuesta(
            codigo=c.codigo,
            nombre_regla=nombre_de_regla(c.codigo),
            severidad=c.severidad,
            descripcion=c.descripcion,
            ocurrencias=len(c.indices),
            indices=list(c.indices),
            celdas=list(dict.fromkeys(tabla[i].celda for i in c.indices if tabla[i].celda)),
            observado=exacto_o_nada(primero.valor_observado) if primero else None,
            esperado=exacto_o_nada(primero.valor_esperado) if primero else None,
        ))
    return respuesta, no_aplicables
