"""Recálculo del cómputo civil ante un cambio de dimensiones (UC‑04; INV‑073).

Pasos 1 a 3 de UC‑04 del lado del cómputo: el proyectista cambia un parámetro de un objeto
paramétrico (el ancho de la tanquilla `T-01`, la longitud de la zanja `Z-01`) y el sistema vuelve a
evaluar **las reglas que lo usan**, con la expresión y los parámetros que cada `ItemComputo` ya
lleva (RF‑18, RF‑19). Los flujos alternativos de `docs/ERS.md` (UC‑04):

- 1a. Un parámetro que no participa en ninguna regla de su objeto no produce recálculo: se informa
  en `Recalculo.sin_regla` y los ítems no cambian.
- 2a. Un objeto que viene de un modelo IFC no tiene reglas que reevaluar: `recalcular` lo rechaza y
  pide reimportar el modelo (UC‑01, paso 2); `emparejar` conserva la correspondencia de las
  partidas por `origen_id`, que es el GlobalId.
- 2b. Una regla que da una cantidad negativa o nula no la impone, y el rechazo es **atómico por
  objeto** (decisión de Eugenio en GC2, dictamen C2‑6): si alguna regla de un objeto (`origen_id`)
  da una cantidad inválida, todos los ítems del objeto conservan su versión anterior y todos quedan
  en `Recalculo.rechazados`. Así un objeto nunca mezcla dimensiones viejas y nuevas (con `a = 0.05`
  en `T-01` el concreto y el encofrado salen negativos y la excavación no: los tres conservan la
  anterior). El relleno se rebalancea con los valores que de verdad quedaron. El hallazgo de R5 que
  pide la ERS lo emite el núcleo al auditar, y **solo cuando el rechazado es el relleno**: el
  relleno conservado deja de cuadrar con su directiva de balance. Si el rechazado es otro objeto
  (la tanquilla con `n = 0`), conserva sus cantidades anteriores, el relleno se rebalancea con
  ellas y R5 cuadra: el rechazo se informa solo en `Recalculo.rechazados`.

El relleno no se edita: es un valor derivado de los totales. Un cambio dirigido a él se rechaza con
`ValueError`, como `diametro`, en vez de descartarse sin aviso al rebalancear.

El paso 5 (RF‑20, el diferencial) no está implementado: se declaró en limitaciones en C1.

Este módulo no toca `core/` (NORMAS.md §2 y §9): importa solo `core.contracts` y su propio paquete,
y evalúa con la copia civil del evaluador (una de las cinco de INV‑006, aceptada mientras no haya
aval del tutor).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from adapters.civil.evaluador import evaluar_regla
from adapters.civil.reglas import REGLA_RELLENO
from core.contracts import ItemComputo, OrigenTipo

__all__ = [
    "PARAMETROS_SOLO_EN_LA_FUENTE",
    "Emparejamiento",
    "Recalculo",
    "emparejar",
    "recalcular",
]

#: Parámetros de la fuente que ningún ítem lleva. `diametro` entra al cómputo solo por el factor de
#: sección que el adaptador tabular fija en la directiva de balance del relleno
#: (`REGLA_VOLUMEN_TUBERIA`): cambiarlo exige volver a extraer la fuente (UC‑01, paso 2).
PARAMETROS_SOLO_EN_LA_FUENTE = frozenset({"diametro"})

_CERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class Recalculo:
    """La versión recalculada del cómputo y lo que el recálculo informa (UC‑04).

    `sin_regla` lista `"origen:parametro"` de cada cambio que no participa en ninguna regla (1a).
    `rechazados` son los ítems anteriores que se conservaron porque una regla de su objeto dio una
    cantidad negativa o nula (2b, atómico por objeto); ya están también en `items`.
    """

    items: tuple[ItemComputo, ...]
    sin_regla: tuple[str, ...] = ()
    rechazados: tuple[ItemComputo, ...] = ()


@dataclass(frozen=True, slots=True)
class Emparejamiento:
    """Ítems de dos extracciones del mismo modelo, emparejados por `(origen_id, codigo_partida)`."""

    pares: tuple[tuple[ItemComputo, ItemComputo], ...]
    solo_anteriores: tuple[ItemComputo, ...]
    solo_nuevos: tuple[ItemComputo, ...]


def recalcular(
    anteriores: Sequence[ItemComputo],
    cambios: Mapping[str, Mapping[str, Decimal]],
    codigos: Mapping[str, str],
) -> Recalculo:
    """Reevalúa las reglas que usan los parámetros cambiados, objeto por objeto.

    :param anteriores: el cómputo vigente, tal como lo devolvió el adaptador.
    :param cambios: por objeto (`origen_id`), los parámetros nuevos, en `Decimal`.
    :param codigos: el mismo mapeo que recibe `AdaptadorCivilTabular`; si trae `relleno`, el
        relleno se recalcula con los totales nuevos.
    """
    efectivos, sin_regla = _separar(anteriores, cambios)
    if not efectivos:
        return Recalculo(items=tuple(anteriores), sin_regla=sin_regla)

    propuestos: list[tuple[ItemComputo, ItemComputo | None]] = []
    for item in anteriores:
        propios = {
            nombre: valor
            for nombre, valor in efectivos.get(item.origen_id, {}).items()
            if nombre in item.parametros
        }
        propuestos.append((item, _reevaluar(item, propios) if propios and item.regla else item))
    # UC‑04, flujo 2b: una cantidad inválida rechaza el objeto entero, no solo su ítem.
    invalidos = {item.origen_id for item, nuevo in propuestos if nuevo is None}
    rechazados = [item for item in anteriores if item.origen_id in invalidos]
    items = [
        item if nuevo is None or item.origen_id in invalidos else nuevo
        for item, nuevo in propuestos
    ]

    if "relleno" in codigos:
        items, del_relleno = _rebalancear_relleno(anteriores, items, codigos)
        rechazados.extend(del_relleno)
    return Recalculo(items=tuple(items), sin_regla=sin_regla, rechazados=tuple(rechazados))


def emparejar(anteriores: Sequence[ItemComputo], nuevos: Sequence[ItemComputo]) -> Emparejamiento:
    """UC‑04, flujo 2a: empareja la extracción anterior con la del modelo reimportado.

    La clave es `(origen_id, codigo_partida)`: en IFC el `origen_id` es el GlobalId del elemento, y
    el código distingue las partidas que un mismo objeto produce. Una clave repetida en cualquiera
    de las dos versiones haría ambiguo el emparejamiento: se rechaza.
    """
    indice_nuevos = _indice(nuevos, "nueva")
    _indice(anteriores, "anterior")
    pares = tuple(
        (anterior, indice_nuevos[_clave(anterior)])
        for anterior in anteriores
        if _clave(anterior) in indice_nuevos
    )
    emparejadas = {_clave(anterior) for anterior, _ in pares}
    return Emparejamiento(
        pares=pares,
        solo_anteriores=tuple(a for a in anteriores if _clave(a) not in emparejadas),
        solo_nuevos=tuple(n for n in nuevos if _clave(n) not in emparejadas),
    )


def _separar(
    anteriores: Sequence[ItemComputo], cambios: Mapping[str, Mapping[str, Decimal]]
) -> tuple[dict[str, dict[str, Decimal]], tuple[str, ...]]:
    """Los cambios que tocan alguna regla de su objeto, y los que no (flujo 1a)."""
    efectivos: dict[str, dict[str, Decimal]] = {}
    sin_regla: list[str] = []
    for origen_id, parametros in cambios.items():
        del_objeto = [item for item in anteriores if item.origen_id == origen_id]
        # Un origen que el cómputo no tiene es un error del llamador, no un flujo 1a.
        if not del_objeto:
            raise ValueError(f"ningun item del computo tiene el origen {origen_id!r}")
        # UC‑04, flujo 2a: un objeto IFC no tiene reglas que reevaluar.
        if any(item.origen_tipo is OrigenTipo.IFC for item in del_objeto):
            raise ValueError(
                f"el objeto {origen_id!r} viene de un modelo IFC, no de reglas: reimporte el "
                "modelo (UC-01, paso 2) y empareje las partidas con `emparejar` (UC-04, 2a)"
            )
        # El relleno se deriva de los totales: un cambio suyo se descartaría al rebalancear.
        if any(item.regla == REGLA_RELLENO for item in del_objeto):
            raise ValueError(
                f"el objeto {origen_id!r} es el relleno, un valor derivado de los totales: "
                "cambie las dimensiones de los objetos que lo determinan"
            )
        participan = {nombre for item in del_objeto if item.regla for nombre in item.parametros}
        for nombre, valor in parametros.items():
            # Un parámetro que solo vive en la fuente exige volver a extraerla.
            if nombre in PARAMETROS_SOLO_EN_LA_FUENTE:
                raise ValueError(
                    f"{nombre!r} no lo lleva ningun item: entra al computo por la fuente; "
                    "vuelva a extraerla (UC-01, paso 2)"
                )
            # UC‑04, flujo 1a: el parámetro no participa en ninguna regla de su objeto.
            if nombre not in participan:
                sin_regla.append(f"{origen_id}:{nombre}")
                continue
            efectivos.setdefault(origen_id, {})[nombre] = valor
    return efectivos, tuple(sin_regla)


def _reevaluar(item: ItemComputo, cambios: Mapping[str, Decimal]) -> ItemComputo | None:
    """El ítem con su regla reevaluada, o `None` si la cantidad no es positiva (flujo 2b)."""
    parametros = {**item.parametros, **cambios}
    cantidad = evaluar_regla(item.regla, parametros)
    if cantidad <= _CERO:
        return None
    return replace(item, cantidad=cantidad, parametros=parametros)


def _rebalancear_relleno(
    anteriores: Sequence[ItemComputo], items: list[ItemComputo], codigos: Mapping[str, str]
) -> tuple[list[ItemComputo], list[ItemComputo]]:
    """El relleno, que se deriva de totales y no de un objeto, recalculado con los ítems nuevos.

    La excavación y el concreto se vuelven a sumar. El volumen de tubería se escala con la longitud
    de tubería: el adaptador tabular admite un solo diámetro por balance (límite declarado en
    `AdaptadorCivilTabular`), así que ese volumen es proporcional a la tubería. Si la tubería no
    cambió, el volumen se conserva tal cual. Si la fuente no tenía tubería, no hay proporción que
    escalar (el factor de sección solo vive en la fuente) y se exige volver a extraerla. Un relleno
    que queda negativo o nulo se rechaza como cualquier otra cantidad (flujo 2b).

    La proporción `volumen × después / antes` se calcula con la precisión del contexto `Decimal`
    (28 dígitos). Cuando el cociente no es exacto puede diferir en el último dígito de lo que da
    volver a extraer la fuente (`factor × tubería`). Con la muestra es exacto, y la prueba lo afirma
    con igualdad.
    """
    tuberia_antes = _suma(anteriores, codigos["tuberia"])
    tuberia_despues = _suma(items, codigos["tuberia"])
    # Sin tubería previa no hay proporción que escalar: se exige volver a extraer la fuente.
    if tuberia_despues != tuberia_antes and not tuberia_antes:
        raise ValueError(
            "la fuente no tenia tuberia: el factor de seccion del relleno no se conoce; "
            "vuelva a extraerla (UC-01, paso 2)"
        )
    resultado: list[ItemComputo] = []
    rechazados: list[ItemComputo] = []
    for item in items:
        if item.codigo_partida != codigos["relleno"] or item.regla != REGLA_RELLENO:
            resultado.append(item)
            continue
        volumen = item.parametros["volumen_tuberia"]
        parametros = {
            "excavacion": _suma(items, codigos["excavacion"]),
            "concreto": _suma(items, codigos["concreto"]),
            "volumen_tuberia": (
                volumen
                if tuberia_despues == tuberia_antes
                else volumen * tuberia_despues / tuberia_antes
            ),
        }
        if parametros == dict(item.parametros):
            resultado.append(item)
            continue
        cantidad = evaluar_regla(REGLA_RELLENO, parametros)
        # UC‑04, flujo 2b: un relleno negativo o nulo conserva su valor anterior.
        if cantidad <= _CERO:
            rechazados.append(item)
            resultado.append(item)
            continue
        resultado.append(replace(item, cantidad=cantidad, parametros=parametros))
    return resultado, rechazados


def _suma(items: Sequence[ItemComputo], codigo: str) -> Decimal:
    return sum((item.cantidad for item in items if item.codigo_partida == codigo), _CERO)


def _clave(item: ItemComputo) -> tuple[str, str]:
    return (item.origen_id, item.codigo_partida)


def _indice(items: Sequence[ItemComputo], version: str) -> dict[tuple[str, str], ItemComputo]:
    indice: dict[tuple[str, str], ItemComputo] = {}
    for item in items:
        clave = _clave(item)
        # Una clave repetida haría ambiguo el emparejamiento.
        if clave in indice:
            raise ValueError(
                f"la version {version} repite el origen {clave[0]!r} para la partida "
                f"{clave[1]!r}: el emparejamiento seria ambiguo"
            )
        indice[clave] = item
    return indice
