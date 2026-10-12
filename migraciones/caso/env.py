"""Entorno de Alembic de la base del caso (RF-96): `core.models` y `METADATA_ESPACIO`."""

from migraciones.comun import ejecutar_entorno
from migraciones.metadatos import METADATAS_CASO

ejecutar_entorno(METADATAS_CASO)
