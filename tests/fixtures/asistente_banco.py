"""El catalogo del experimento: las partidas de OF-001 y de TI-001 como las ve el asistente."""

from __future__ import annotations

from asistente.catalogo import CatalogoDeLaBase, PartidaVista
from core.contracts.dominio import Dominio
from tests.fixtures import caso_of001, caso_ti001


def partidas() -> list[PartidaVista]:
    civiles = [
        PartidaVista(c.codigo_partida, c.descripcion, c.unidad, Dominio.CIVIL)
        for c in caso_of001.COMPOSICIONES.values()
    ]
    telecom = [
        PartidaVista(c.codigo_partida, c.descripcion, c.unidad, Dominio.TELECOM)
        for c in caso_ti001.COMPOSICIONES.values()
    ]
    return civiles + telecom


def catalogo_del_experimento() -> CatalogoDeLaBase:
    return CatalogoDeLaBase(partidas())


def codigos_y_unidades() -> list[tuple[str, str]]:
    return [(p.codigo, p.unidad) for p in partidas()]
