"""Cada destino de migración declara su lista explícita de `MetaData` (maestro §4.2; RF-96)."""

from __future__ import annotations

from adapters.espacio import persistencia
from core.models import Base
from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION
from seguridad.modelo import Base as BaseSeguridad


def test_metadata_espacio_es_publica_y_es_la_de_las_tablas_esp() -> None:
    assert set(persistencia.METADATA_ESPACIO.tables) == {
        tabla.name for tabla in persistencia.TABLAS
    }
    assert all(tabla.metadata is persistencia.METADATA_ESPACIO for tabla in persistencia.TABLAS)


def test_el_caso_lleva_el_nucleo_y_el_espacio_y_la_instalacion_lleva_seguridad() -> None:
    assert len(METADATAS_CASO) == 2
    assert METADATAS_CASO[0] is Base.metadata
    assert METADATAS_CASO[1] is persistencia.METADATA_ESPACIO
    assert METADATAS_INSTALACION == (BaseSeguridad.metadata,)
