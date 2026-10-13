"""Escritor del libro calcado (spec 1.5, F-D3 a F-D10).

Devuelve a la empresa su propio libro de Excel con el mismo aspecto (hojas, colores, fuentes,
anchos, combinadas, formatos y rótulos), forma uniforme por dentro (APU regenerados y enlazados por
nombres definidos), sin las causas de error del análisis de causas raíz (C1-C6), con valores
guardados iguales a los de Silice y tres hojas nuevas: AUDITORÍA, TRAZABILIDAD y ALERTAS USD-Bs.
"""

from adapters.hoja_empresa.escritor.devolucion import escribir_devolucion

__all__ = ["escribir_devolucion"]
