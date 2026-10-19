"""RF-100 (S3-6): reexportacion de `aplicacion/atipicos.py` (RM-1, T4 de la migracion final).

Las dos pantallas de Streamlit (`ui/paginas/hoja.py`, pestaña Precios, y
`ui/paginas/precios_empresa.py`) siguen importando este modulo; la logica ya no vive aqui. Lo unico
propio es `avisos`, que escapa el texto ajeno para el Markdown de Streamlit (RV-14): la API manda
los mismos avisos sin escapar.
"""

from __future__ import annotations

from aplicacion import atipicos as _aplicacion
from aplicacion.atipicos import AVISO_SIN_ML as AVISO_SIN_ML
from aplicacion.atipicos import MENSAJE_NADA_ATIPICO as MENSAJE_NADA_ATIPICO
from aplicacion.atipicos import ROTULO_BOTON as ROTULO_BOTON
from aplicacion.atipicos import BusquedaAtipicos as BusquedaAtipicos
from aplicacion.atipicos import atipicos_de_insumos as atipicos_de_insumos
from aplicacion.atipicos import atipicos_del_insumo as atipicos_del_insumo
from aplicacion.atipicos import codigos_de_la_lista as codigos_de_la_lista
from aplicacion.atipicos import hallazgos_de_la_serie as hallazgos_de_la_serie
from aplicacion.atipicos import puntos_del_insumo as puntos_del_insumo
from ui.texto_seguro import texto_seguro

__all__ = [
    "AVISO_SIN_ML",
    "MENSAJE_NADA_ATIPICO",
    "ROTULO_BOTON",
    "BusquedaAtipicos",
    "atipicos_de_insumos",
    "atipicos_del_insumo",
    "avisos",
    "codigos_de_la_lista",
    "hallazgos_de_la_serie",
    "puntos_del_insumo",
]


def avisos(busqueda: BusquedaAtipicos | None) -> list[tuple[str, str]]:
    """Lo que las pantallas muestran de una búsqueda, como `(nivel, texto)` con el nivel de
    Streamlit (`info`, `success` o `warning`) y el texto ya escapado (RV-14). Nunca `error`."""
    return _aplicacion.avisos(busqueda, texto_seguro)
