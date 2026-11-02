"""La equivalencia de un precio del corte convertido, como la devuelve la API (Tarea D2).

Un precio declarado en otra moneda que la obra se convierte con la tasa del BCV de su fecha
(`aplicacion/precios_declarados.py`). Cada cifra viaja como **texto exacto** con punto decimal; la
pantalla solo la da formato (coma decimal, punto de miles) y arma la línea «31,50 USD × 36,50
Bs/USD (BCV del 20/10/2026) = 1.149,75 Bs»: no calcula.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from aplicacion.precios_declarados import Equivalencia

__all__ = ["EquivalenciaRespuesta", "equivalencia_a_respuesta"]


class EquivalenciaRespuesta(BaseModel):
    precio_original: str = Field(description="El precio tal como se declaró, exacto")
    moneda_original: str
    tasa: str = Field(description="Bs por USD, exacta")
    fecha_tasa: str = Field(description="aaaa-mm-dd: la fecha valor de la tasa usada")
    fuente_tasa: str = Field(description="La referencia interna de la tasa, para el rastro")
    fuente_legible: str = Field(description="«BCV, publicación del dd/mm/aaaa», para mostrar")
    convertido: str = Field(description="El resultado en la moneda de la obra, exacto")
    moneda: str = Field(description="La moneda del resultado (la de la obra)")
    operacion: str = Field(description="«×» si se multiplicó por la tasa (USD a Bs); «÷» si no")


def equivalencia_a_respuesta(equivalencia: Equivalencia) -> EquivalenciaRespuesta:
    return EquivalenciaRespuesta(
        precio_original=format(equivalencia.precio_original, "f"),
        moneda_original=equivalencia.moneda_original,
        tasa=format(equivalencia.tasa, "f"),
        fecha_tasa=equivalencia.fecha_tasa.isoformat(),
        fuente_tasa=equivalencia.fuente_tasa,
        fuente_legible=equivalencia.fuente_legible,
        convertido=format(equivalencia.convertido, "f"),
        moneda=equivalencia.moneda,
        operacion=equivalencia.operacion,
    )
