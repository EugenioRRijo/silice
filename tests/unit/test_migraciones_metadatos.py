"""Cada destino de migración declara su lista explícita de `MetaData` (maestro §4.2; RF-96)."""

from __future__ import annotations

from adapters.espacio import persistencia
from aplicacion.tablas_eleccion import METADATA_ELECCION
from core.models import Base
from fusion.historial_modelo import METADATA_HISTORIAL
from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION
from produccion.modelo import METADATA_PRODUCCION
from seguridad.modelo import Base as BaseSeguridad


def test_metadata_espacio_es_publica_y_es_la_de_las_tablas_esp() -> None:
    assert set(persistencia.METADATA_ESPACIO.tables) == {
        tabla.name for tabla in persistencia.TABLAS
    }
    assert all(tabla.metadata is persistencia.METADATA_ESPACIO for tabla in persistencia.TABLAS)


def test_el_caso_lleva_el_nucleo_y_el_espacio_al_principio() -> None:
    assert METADATAS_CASO[0] is Base.metadata
    assert METADATAS_CASO[1] is persistencia.METADATA_ESPACIO


def test_el_caso_lleva_el_registro_del_asistente() -> None:
    from asistente.registro import METADATA_IA

    assert METADATA_IA in METADATAS_CASO


def test_la_instalacion_lleva_seguridad_la_arenera_el_historial_y_la_eleccion() -> None:
    assert METADATAS_INSTALACION == (
        BaseSeguridad.metadata,
        METADATA_PRODUCCION,
        METADATA_HISTORIAL,
        METADATA_ELECCION,
    )


def test_el_caso_lleva_la_moneda_de_la_carpeta() -> None:
    from aplicacion.tablas_carpeta import METADATA_CARPETA

    assert METADATA_CARPETA in METADATAS_CASO


def test_el_caso_lleva_el_estudio_de_mercado() -> None:
    from aplicacion.tablas_mercado import METADATA_MERCADO

    assert METADATA_MERCADO in METADATAS_CASO


def test_el_caso_lleva_el_rastro_de_aprobaciones() -> None:
    from aplicacion.tablas_aprobacion import METADATA_APROBACION

    assert METADATA_APROBACION in METADATAS_CASO
