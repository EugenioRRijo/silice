"""La lista explícita de `MetaData` de cada destino (maestro §4.2; RF-96, RNF-20).

`METADATAS_CASO` crece con `paquete` (S3) y `asistente` (S4); `METADATAS_INSTALACION` la llena
S3-1 con `seguridad.modelo`. Toda `MetaData` con tablas del repositorio está en una de las
dos: lo comprueba `tests/integration/test_migraciones.py`.
"""

from __future__ import annotations

from sqlalchemy import MetaData

from adapters.espacio.persistencia import METADATA_ESPACIO
from asistente.registro import METADATA_IA
from core.models import Base
from paquete.modelo import METADATA_PAQUETE
from produccion.modelo import METADATA_PRODUCCION
from seguridad.modelo import Base as BaseSeguridad

METADATAS_CASO: tuple[MetaData, ...] = (
    Base.metadata,
    METADATA_ESPACIO,
    METADATA_IA,
    METADATA_PAQUETE,
)
METADATAS_INSTALACION: tuple[MetaData, ...] = (BaseSeguridad.metadata, METADATA_PRODUCCION)
