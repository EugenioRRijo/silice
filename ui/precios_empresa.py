"""UC-17 4-5: reexportacion de `aplicacion/precios_empresa.py` (RM-1). La pantalla de Streamlit
(`ui/paginas/precios_empresa.py`) sigue importando este modulo; la logica ya no vive aqui."""

from __future__ import annotations

from aplicacion.precios_empresa import COLUMNAS_HALLAZGOS as COLUMNAS_HALLAZGOS
from aplicacion.precios_empresa import NOMBRE_REFERENCIA as NOMBRE_REFERENCIA
from aplicacion.precios_empresa import ResumenEmpresa as ResumenEmpresa
from aplicacion.precios_empresa import cargar_referencia_maprex as cargar_referencia_maprex
from aplicacion.precios_empresa import crear_lista as crear_lista
from aplicacion.precios_empresa import hallazgos_de_lista as hallazgos_de_lista
from aplicacion.precios_empresa import listas_base as listas_base
from aplicacion.precios_empresa import listas_de_empresa as listas_de_empresa

__all__ = [
    "COLUMNAS_HALLAZGOS",
    "NOMBRE_REFERENCIA",
    "ResumenEmpresa",
    "cargar_referencia_maprex",
    "crear_lista",
    "hallazgos_de_lista",
    "listas_base",
    "listas_de_empresa",
]
