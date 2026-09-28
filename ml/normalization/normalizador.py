"""Normalizacion semantica de descripciones de partida (UC-03, Sesion I2).

Dada una descripcion en texto libre, propone las partidas del catalogo mas parecidas por similitud
del coseno entre vectores de `sentence-transformers` (modelo multilingue
`paraphrase-multilingual-MiniLM-L12-v2`, el que fija el PLAN). No requiere datos etiquetados ni
entrenamiento: es similitud semantica directa.

Arquitectura (CLAUDE.md §2, `tests/unit/test_arquitectura.py`): `ml/` no conoce la base de datos ni
importa de `core` nada fuera de `core.contracts` -- este modulo, de hecho, no necesita ni los
contratos: recibe el catalogo como pares (codigo, descripcion) planos y la capa de composicion
(`ui/`, `api/`) le pasa lo que consulta `core.catalog`.

El puntaje es un `float`: es una similitud adimensional en [-1, 1], no una cantidad de obra ni un
monto, asi que la regla `Decimal` de CLAUDE.md §2.3 no lo alcanza (los vectores del modelo son
`float32` de origen). Se presenta redondeado solo en la capa de presentacion.

La primera construccion descarga el modelo si no esta en la cache local de Hugging Face
(precondicion del UC-03: «el modelo de similitud esta disponible localmente», docs/ERS.md); las
siguientes lo reutilizan en memoria (`_cargar_modelo` esta cacheado por proceso).

La propuesta es una ayuda, no una condicion (UC-01 3a): `proponedor` y `propuestas_para` son el
criterio unico de que fallas del modelo dejan un item «sin propuestas» y cuales son un defecto
que se propaga (INV-081). La API y `ui/` los comparten en vez de atrapar cada una lo suyo.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

#: El modelo que fija el PLAN (Sesion I2): multilingue, entrenado para parafrasis.
MODELO_POR_DEFECTO = "paraphrase-multilingual-MiniLM-L12-v2"

#: Umbral declarado de similitud (RF-15): por debajo no se propone nada y el llamador ofrece
#: crear la partida desde cero (UC-03, flujo 2a). Calibrado con la prueba de aceptacion RF-17
#: sobre la linea base parafraseada (tests/unit/test_normalizacion.py).
UMBRAL_POR_DEFECTO = 0.5

#: RF-15 pide las tres mas similares.
PROPUESTAS_POR_DEFECTO = 3

#: Las fallas de UC-03 que dejan un item sin propuestas en vez de abortar: extra `ml` ausente
#: (`ImportError`), modelo ausente o sin red (`OSError`), identificador invalido (`ValueError`;
#: `HFValidationError` de Hugging Face es su subclase) y pesos corruptos (`RuntimeError` de
#: `torch.load`). Cualquier otra excepcion es un defecto y se propaga.
FALLAS_DE_LA_PROPUESTA: tuple[type[Exception], ...] = (
    ImportError,
    OSError,
    ValueError,
    RuntimeError,
)

__all__ = [
    "FALLAS_DE_LA_PROPUESTA",
    "MODELO_POR_DEFECTO",
    "PROPUESTAS_POR_DEFECTO",
    "UMBRAL_POR_DEFECTO",
    "NormalizadorPartidas",
    "PartidaSimilar",
    "Propuesta",
    "TieneDescripcion",
    "proponedor",
    "propuestas_para",
]

_registro = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def _cargar_modelo(nombre: str):
    """Un `SentenceTransformer` por nombre y por proceso: cargarlo cuesta segundos y memoria."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(nombre)


@dataclass(frozen=True)
class PartidaSimilar:
    """Una propuesta de reutilizacion: la partida del catalogo y el puntaje que la justifica.

    El puntaje queda registrado como justificacion de la reutilizacion (UC-03, postcondicion).
    """

    codigo: str
    descripcion: str
    puntaje: float


class NormalizadorPartidas:
    """Indice semantico del catalogo de partidas.

    Vectoriza las descripciones una sola vez al construirse (normalizadas a modulo 1, de modo que
    la similitud del coseno es el producto punto) y responde consultas con `similares`.
    """

    def __init__(
        self,
        partidas: Mapping[str, str],
        modelo: str = MODELO_POR_DEFECTO,
        umbral: float = UMBRAL_POR_DEFECTO,
    ) -> None:
        """:param partidas: catalogo como {codigo: descripcion}; puede estar vacio (flujo 2b).
        :param modelo: nombre del modelo de sentence-transformers.
        :param umbral: similitud minima para proponer (RF-15).
        """
        self._partidas = dict(partidas)
        self._codigos = list(self._partidas)
        self._umbral = umbral
        self._modelo = _cargar_modelo(modelo)
        self._vectores = (
            self._modelo.encode(
                [self._partidas[codigo] for codigo in self._codigos],
                normalize_embeddings=True,
            )
            if self._codigos
            else None
        )

    def similares(
        self, descripcion: str, cuantos: int = PROPUESTAS_POR_DEFECTO
    ) -> list[PartidaSimilar]:
        """Las `cuantos` partidas mas parecidas, de mayor a menor puntaje, todas sobre el umbral.

        Lista vacia si el catalogo esta vacio (UC-03, flujo 2b) o si ningun candidato alcanza el
        umbral (flujo 2a): el llamador ofrece entonces crear la partida desde cero.
        """
        if self._vectores is None:
            return []
        consulta = self._modelo.encode([descripcion], normalize_embeddings=True)[0]
        puntajes = self._vectores @ consulta
        mejores = puntajes.argsort()[::-1][:cuantos]
        return [
            PartidaSimilar(
                codigo=self._codigos[indice],
                descripcion=self._partidas[self._codigos[indice]],
                puntaje=float(puntajes[indice]),
            )
            for indice in mejores
            if float(puntajes[indice]) >= self._umbral
        ]


class TieneDescripcion(Protocol):
    """Lo unico que `propuestas_para` necesita de un pendiente: un `ItemComputo`, en la practica."""

    @property
    def descripcion(self) -> str: ...


@dataclass(frozen=True, slots=True)
class Propuesta:
    """Las partidas similares propuestas para una descripcion, o por que no hay ninguna.

    `falla` es `None` si el modelo respondio (aunque no propusiera nada: UC-03, flujos 2a y 2b) y
    `"Tipo: mensaje"` si una de `FALLAS_DE_LA_PROPUESTA` le impidio proponer.
    """

    similares: tuple[PartidaSimilar, ...]
    falla: str | None = None


def proponedor(partidas: Mapping[str, str]) -> Callable[[str], Propuesta]:
    """El criterio unico de UC-03 (INV-081): construye el normalizador **una** vez y lo reutiliza
    en cada consulta.

    Ante una de `FALLAS_DE_LA_PROPUESTA`, al construir o al consultar, devuelve una `Propuesta`
    vacia con su falla y lo registra con `logging.warning` y su tipo, para que un fallo del modelo
    no pase por un simple «sin propuestas». La falla al consultar deja sin propuestas solo a esa
    descripcion. Cualquier otra excepcion se propaga.
    """
    try:
        normalizador = NormalizadorPartidas(dict(partidas))
    except FALLAS_DE_LA_PROPUESTA as error:
        falla = _falla(error)
        _registro.warning("UC-03 sin propuestas: el normalizador no se pudo construir (%s)", falla)
        return lambda _descripcion: Propuesta((), falla)

    def proponer(descripcion: str) -> Propuesta:
        try:
            return Propuesta(tuple(normalizador.similares(descripcion)))
        except FALLAS_DE_LA_PROPUESTA as error:
            falla = _falla(error)
            _registro.warning(
                "UC-03 sin propuestas para %r: similares fallo (%s)", descripcion, falla
            )
            return Propuesta((), falla)

    return proponer


def propuestas_para[P: TieneDescripcion](
    partidas: Mapping[str, str], pendientes: Sequence[P]
) -> tuple[tuple[P, Propuesta], ...]:
    """UC-01 3a con UC-03: cada pendiente con la propuesta para su descripcion, en su orden.

    Un solo `proponedor` por llamada, y ninguno sin pendientes: cargar el modelo cuesta segundos y
    la primera vez puede descargarlo. Es el unico emparejamiento de pendientes con propuestas: la
    API y `ui/` lo comparten (INV-081).
    """
    if not pendientes:
        return ()
    proponer = proponedor(partidas)
    return tuple((pendiente, proponer(pendiente.descripcion)) for pendiente in pendientes)


def _falla(error: Exception) -> str:
    """`"Tipo: mensaje"`, con el nombre de la falla **declarada** que la atrapó, no el de su
    subclase: sin el extra, la importación lanza `ModuleNotFoundError` y la falla es `ImportError`,
    el prefijo con que quien presenta la propuesta distingue «sin el extra» de un modelo roto."""
    declarada = next(falla for falla in FALLAS_DE_LA_PROPUESTA if isinstance(error, falla))
    return f"{declarada.__name__}: {error}"
