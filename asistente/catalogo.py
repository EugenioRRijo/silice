"""La vista del catalogo que ve el asistente (S4 §6, §8.1): codigo, descripcion y unidad.

El asistente no importa `core.catalog`: recibe un `CatalogoVista`. `CatalogoDeLaBase` lo arma sobre
las partidas que ya leyo la interfaz (`ui.hoja`) y, para buscar, sobre `ml.normalization`. Ningun
metodo devuelve precios ni cantidades.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from core.contracts.dominio import Dominio


@dataclass(frozen=True, slots=True)
class PartidaVista:
    codigo: str
    descripcion: str
    unidad: str
    dominio: Dominio
    #: True si la partida viene de MaPreX: en modo nube solo viajan codigo y unidad (P7).
    de_maprex: bool = False
    puntaje: float | None = None
    #: Tipos de insumo de su composicion (`material`, `equipo`, `mano_obra`), sin cantidades.
    tipos_de_insumo: tuple[str, ...] = ()


class CatalogoVista(Protocol):
    def partida(self, codigo: str) -> PartidaVista | None: ...

    def buscar(self, texto: str, cuantos: int) -> tuple[list[PartidaVista], bool]:
        """Las partidas mas parecidas y si la busqueda fue semantica (False: por palabras)."""
        ...


Proponedor = Callable[[str], Sequence[tuple[str, float]]]


class CatalogoDeLaBase:
    """`partidas` ya leidas; `proponer(texto)` devuelve (codigo, puntaje) o `None` sin similitud."""

    def __init__(
        self,
        partidas: Iterable[PartidaVista],
        proponer: Proponedor | None = None,
    ) -> None:
        self._por_codigo = {p.codigo: p for p in partidas}
        self._proponer = proponer

    def partida(self, codigo: str) -> PartidaVista | None:
        return self._por_codigo.get(codigo)

    def buscar(self, texto: str, cuantos: int) -> tuple[list[PartidaVista], bool]:
        if self._proponer is not None:
            vistas = [
                _con_puntaje(self._por_codigo[codigo], puntaje)
                for codigo, puntaje in self._proponer(texto)
                if codigo in self._por_codigo
            ]
            if vistas:
                return vistas[:cuantos], True
        palabras = {w for w in texto.casefold().split() if len(w) > 2}
        puntuadas = sorted(
            (
                (sum(w in p.descripcion.casefold() for w in palabras), p.codigo)
                for p in self._por_codigo.values()
            ),
            reverse=True,
        )
        return [self._por_codigo[c] for n, c in puntuadas[:cuantos] if n > 0], False


def _con_puntaje(partida: PartidaVista, puntaje: float) -> PartidaVista:
    return PartidaVista(
        partida.codigo,
        partida.descripcion,
        partida.unidad,
        partida.dominio,
        partida.de_maprex,
        puntaje,
        partida.tipos_de_insumo,
    )
