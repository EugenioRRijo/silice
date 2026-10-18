"""Partidas similares (UC-03, RF-15 y RF-16) sin interfaz: la propuesta y su desglose como texto.

Es la logica de `ui/paginas/similares.py` que la API tambien necesita (RM-1). `ml/` no conoce la
base de datos (NORMAS.md §2): aqui se consulta `core.catalog` y se le pasan pares (codigo,
descripcion) planos. Los montos y cantidades salen ya formateados (`formatear_decimal` con
`DECIMALES_PRESENTACION`); quien consume no calcula.

`sugerir_partidas_similares` vive aqui y `ui.composicion` la reexporta (la usan tambien la
composicion a mano y el asistente).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from core.catalog import Catalogo, CatalogoIncompleto
from core.contracts.apu import ComposicionAPU
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from operacion import config

if TYPE_CHECKING:
    from ml.normalization import Propuesta

MENSAJE_SIN_EXTRA_ML = (
    "Las propuestas de partidas similares necesitan el extra 'similitud' (sentence-transformers): "
    "instala con 'uv sync --extra similitud' y vuelve a intentar."
)
MENSAJE_SIN_MODULO = (
    "El módulo de similitud de partidas no está instalado en este equipo. Ejecute el instalador "
    "completo (Silice-<versión>-completo.exe) para agregarlo; sus datos se conservan."
)
MENSAJE_SIN_UMBRAL = (
    "Ninguna partida del catalogo supera el umbral de similitud: la partida se crearia desde cero."
)
MENSAJE_SIN_DESCRIPCION = "Escriba una descripción para buscar partidas similares."


#: Quien propone: recibe el catalogo como pares (codigo, descripcion) y la descripcion tecleada.
Proponedor = Callable[[Mapping[str, str], str], "Propuesta"]


def sugerir_partidas_similares(partidas: Mapping[str, str], descripcion: str) -> Propuesta:
    """UNICO punto de enlace con el proponedor real (criterio unico de INV-081).

    TODO(S2-B / tesis-8f): cuando `sugerir_partidas_similares` pase de `ui/composicion.py` a
    `aplicacion/composicion.py`, reemplazar el cuerpo por
    `from aplicacion.composicion import sugerir_partidas_similares as real` y delegar. Mientras,
    se llama directo a `ml.normalization.proponedor`, que es lo que esa funcion hace (sin importar
    `ui/`). `ml` falta como extra -> `proponedor` devuelve una `Propuesta` con su `falla`.
    """
    import ml.normalization

    if not descripcion.strip() or not partidas:
        return ml.normalization.Propuesta(())
    return ml.normalization.proponedor(partidas)(descripcion)


@dataclass(frozen=True, slots=True)
class LineaMaterialTexto:
    descripcion: str
    unidad: str
    cantidad: str
    precio: str


@dataclass(frozen=True, slots=True)
class LineaEquipoTexto:
    descripcion: str
    cantidad: str
    precio: str
    depreciacion: str


@dataclass(frozen=True, slots=True)
class LineaManoObraTexto:
    descripcion: str
    cantidad: str
    sueldo: str


@dataclass(frozen=True, slots=True)
class ComposicionTexto:
    unidad: str
    rendimiento: str
    materiales: tuple[LineaMaterialTexto, ...]
    equipos: tuple[LineaEquipoTexto, ...]
    mano_obra: tuple[LineaManoObraTexto, ...]


@dataclass(frozen=True, slots=True)
class PropuestaTexto:
    codigo: str
    descripcion: str
    puntaje: str
    puntaje_corto: str
    composicion: ComposicionTexto | None
    aviso: str | None


@dataclass(frozen=True, slots=True)
class ResultadoSimilares:
    """`falla` y `mensaje` son textos para la persona; ambos `None` si hay propuestas."""

    propuestas: tuple[PropuestaTexto, ...] = field(default_factory=tuple)
    falla: str | None = None
    mensaje: str | None = None


def mensaje_sin_modulo() -> str:
    # `es_producto` llega con la T5 (S5-1); mientras no exista, el equipo es de desarrollo.
    es_producto = getattr(config, "es_producto", lambda: False)
    return MENSAJE_SIN_MODULO if es_producto() else MENSAJE_SIN_EXTRA_ML


def _numero(valor) -> str:
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def _en_texto(composicion: ComposicionAPU) -> ComposicionTexto:
    return ComposicionTexto(
        unidad=composicion.unidad,
        rendimiento=_numero(composicion.rendimiento),
        materiales=tuple(
            LineaMaterialTexto(
                linea.descripcion, linea.unidad, _numero(linea.cantidad), _numero(linea.precio)
            )
            for linea in composicion.materiales
        ),
        equipos=tuple(
            LineaEquipoTexto(
                linea.descripcion,
                _numero(linea.cantidad),
                _numero(linea.precio),
                str(linea.depreciacion),
            )
            for linea in composicion.equipos
        ),
        mano_obra=tuple(
            LineaManoObraTexto(linea.descripcion, _numero(linea.cantidad), _numero(linea.sueldo))
            for linea in composicion.mano_obra
        ),
    )


def proponer_similares(
    sesion: Session, descripcion: str, proponedor: Proponedor | None = None
) -> ResultadoSimilares:
    """Las partidas parecidas a `descripcion` con su desglose, o por que no las hay.

    `ValueError` si la descripcion esta en blanco. Un desglose con insumos sin precio vigente
    (flujo 4a) deja `aviso` y `composicion=None` en esa propuesta; las demas siguen.
    """
    if not descripcion.strip():
        raise ValueError(MENSAJE_SIN_DESCRIPCION)
    catalogo = Catalogo(sesion)
    partidas = {p.codigo: p.descripcion for p in catalogo.partidas()}
    propuesta = (proponedor or sugerir_partidas_similares)(partidas, descripcion)
    if propuesta.falla is not None:
        # Precondicion del UC-03: el modelo debe estar disponible localmente. Sin el extra, el
        # aviso de instalarlo; con otra falla declarada, el error del modelo: un mensaje.
        if propuesta.falla.startswith("ImportError"):
            return ResultadoSimilares(falla=mensaje_sin_modulo())
        return ResultadoSimilares(
            falla=f"El modelo de similitud no esta disponible: {propuesta.falla}"
        )
    if not propuesta.similares:
        # Flujos 2a y 2b del UC-03: nada sobre el umbral (o catalogo vacio) -> desde cero.
        return ResultadoSimilares(mensaje=MENSAJE_SIN_UMBRAL)
    resultado: list[PropuestaTexto] = []
    for similar in propuesta.similares:
        try:
            composicion = _en_texto(catalogo.composicion(similar.codigo))
            aviso = None
        except CatalogoIncompleto as error:
            # Flujo 4a del UC-03: insumos sin precio en la lista vigente.
            composicion = None
            aviso = f"Desglose incompleto en la lista vigente: {error}"
        resultado.append(
            PropuestaTexto(
                similar.codigo,
                similar.descripcion,
                f"{similar.puntaje:.4f}",
                f"{similar.puntaje:.2f}",
                composicion,
                aviso,
            )
        )
    return ResultadoSimilares(propuestas=tuple(resultado))
