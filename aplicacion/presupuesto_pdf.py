"""El presupuesto de la Hoja en PDF (RF-213): esqueleto para ver el rojo."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from aplicacion.hoja_vista import FilaDePresupuesto


class PartidaSinApu(LookupError):
    """La partida pedida no tiene un APU valorado en el borrador."""


@dataclass(frozen=True, slots=True)
class Encabezado:
    titulo: str
    obra: str
    version: str
    fecha: str
    emitido: str
    moneda: str
    notas: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Renglon:
    numero: str
    partida: str
    descripcion: str
    unidad: str
    cantidad: str
    precio_unitario: str
    total: str


@dataclass(frozen=True, slots=True)
class Grupo:
    titulo: str
    renglones: tuple[Renglon, ...]
    subtotal: str | None


@dataclass(frozen=True, slots=True)
class LineaDeCierre:
    concepto: str
    monto: str


@dataclass(frozen=True, slots=True)
class TablaDeApu:
    rotulo: str
    columnas: tuple[str, ...]
    filas: tuple[tuple[str, ...], ...]
    subtotal: str


@dataclass(frozen=True, slots=True)
class ApuDelPdf:
    codigo: str
    descripcion: str
    unidad: str
    rendimiento: str
    parametros: str
    tablas: tuple[TablaDeApu, ...]
    cierre: tuple[LineaDeCierre, ...]


@dataclass(frozen=True, slots=True)
class DocumentoPdf:
    encabezado: Encabezado
    grupos: tuple[Grupo, ...]
    totales: tuple[LineaDeCierre, ...]
    notas_finales: tuple[str, ...]
    apus: tuple[ApuDelPdf, ...]


Agrupador = Callable[
    [Sequence[FilaDePresupuesto]], Sequence[tuple[str, Sequence[FilaDePresupuesto]]]
]


def sin_agrupar(filas):
    raise NotImplementedError


def documento_de_la_hoja(vivo, hoy, *, partida=None, agrupar=sin_agrupar) -> DocumentoPdf:
    raise NotImplementedError


def pdf_en_bytes(documento: DocumentoPdf) -> bytes:
    raise NotImplementedError


def nombre_del_pdf(codigo, *, partida=None) -> str:
    raise NotImplementedError
