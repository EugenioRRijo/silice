"""La lista explícita de `MetaData` de cada destino (maestro §4.2; RF-96, RNF-20).

`METADATAS_CASO` crece con `paquete` (S3) y `asistente` (S4); `METADATAS_INSTALACION` la llena
S3-1 con `seguridad.modelo`. Toda `MetaData` con tablas del repositorio está en una de las
dos: lo comprueba `tests/integration/test_migraciones.py`.
"""

from __future__ import annotations

from sqlalchemy import MetaData

from adapters.espacio.persistencia import METADATA_ESPACIO
from aplicacion.tablas_aprobacion import METADATA_APROBACION
from aplicacion.tablas_carpeta import METADATA_CARPETA
from aplicacion.tablas_causas import METADATA_CAUSAS
from aplicacion.tablas_corte import METADATA_CORTE
from aplicacion.tablas_eleccion import METADATA_ELECCION
from aplicacion.tablas_importaciones import METADATA_IMPORTACIONES
from aplicacion.tablas_indice_aprobacion import METADATA_INDICE_APROBACION
from aplicacion.tablas_medicion import METADATA_MEDICION
from aplicacion.tablas_mercado import METADATA_MERCADO
from aplicacion.tablas_modulos import METADATA_MODULOS
from aplicacion.tablas_obra import METADATA_OBRA
from aplicacion.tablas_procura import METADATA_PROCURA
from aplicacion.tablas_vial import METADATA_VIAL
from asistente.registro import METADATA_IA
from core.models import Base
from fusion.historial_modelo import METADATA_HISTORIAL
from paquete.modelo import METADATA_PAQUETE
from produccion.modelo import METADATA_PRODUCCION
from seguridad.modelo import Base as BaseSeguridad

METADATAS_CASO: tuple[MetaData, ...] = (
    Base.metadata,
    METADATA_ESPACIO,
    METADATA_IA,
    METADATA_PAQUETE,
    METADATA_CARPETA,
    METADATA_OBRA,
    METADATA_MERCADO,
    METADATA_APROBACION,
    METADATA_MEDICION,
    METADATA_CAUSAS,
    METADATA_PROCURA,
    METADATA_CORTE,
    METADATA_VIAL,
    METADATA_IMPORTACIONES,
)
METADATAS_INSTALACION: tuple[MetaData, ...] = (
    BaseSeguridad.metadata,
    METADATA_PRODUCCION,
    METADATA_HISTORIAL,
    METADATA_ELECCION,
    METADATA_INDICE_APROBACION,
    METADATA_MODULOS,
)
