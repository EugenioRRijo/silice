"""Entorno de Alembic de la base de la instalación (RF-96): vacío hasta S3-1."""

from migraciones.comun import ejecutar_entorno
from migraciones.metadatos import METADATAS_INSTALACION

ejecutar_entorno(METADATAS_INSTALACION)
