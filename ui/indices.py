"""Reexportación de `aplicacion.indices` (RM-1, plan de la sesión 2b).

UC‑17 1‑3 (adaptador -> informe previo -> núcleo) vive en `aplicacion/indices.py` para que la API
y la pantalla clásica la compartan sin que `api/` importe `ui/`. Este módulo conserva los nombres
que usan la página y las pruebas; no define nada ni importa Streamlit.
"""

from aplicacion.indices import MENSAJE_SIN_XLRD as MENSAJE_SIN_XLRD
from aplicacion.indices import ROTULOS_TIPO as ROTULOS_TIPO
from aplicacion.indices import TIPOS as TIPOS
from aplicacion.indices import confirmar as confirmar
from aplicacion.indices import definiciones_desde_filas as definiciones_desde_filas
from aplicacion.indices import filas_del_informe as filas_del_informe
from aplicacion.indices import leer as leer
from aplicacion.indices import resumen_de_series as resumen_de_series
