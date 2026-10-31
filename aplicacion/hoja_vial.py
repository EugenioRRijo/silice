"""Llevar los tramos viales al presupuesto: al borrador de la Hoja de la obra (plan vial, Tarea 8b).

Las cantidades de los tramos de una versión (`aplicacion.vial.tramos_de_version`, derivadas con
`adapters.vial.derivar_tramos`) entran en el borrador de la Hoja como renglones con su origen de
tramo («tramo:T1:capa:3») y su origen REGLA, nunca como «a-mano:n». No se guarda versión: los
renglones quedan como altas del borrador, que se guarda desde la Hoja.

- **La versión que se ve es la que se lleva.** Quien llama nombra la versión cuyos tramos tiene a
  la vista. El borrador es el de `elaboracion.version_del_borrador_de_la_obra` (el vivo de esa
  ficha y obra o, sin él, uno nuevo sobre la vigente); si es de otra versión,
  `BorradorDeOtraVersion` (409) con las dos versiones y qué hacer, y no se lleva nada.
- **Llevar otra vez sincroniza** (`sincronizar_renglones`): los renglones «tramo:» se reemplazan
  por la derivación de ahora en su mismo sitio; los demás no se tocan; la cantidad escrita sobre
  una clave que sigue se conserva y la de una que desaparece se descarta.
- **Partidas sin APU:** el 404 de `hoja_edicion.PartidaFueraDelCatalogo`, con todos los códigos.
- **Reglas:** llevar rearma las reglas viales del borrador (`reglas_extra`) con los tramos de ese
  momento y, para VR2, la fórmula de la receta vigente el día `hoy` de la mezcla propia de cada
  partida de mezcla (`vial.formulas_de_trabajo`, Tarea 16b).
- **Todo o nada**, con el cerrojo del borrador: si algo falla, el borrador abierto aquí se descarta
  y uno que ya existía vuelve a como estaba, con su `rev`.

Vive aparte de `aplicacion/vial.py` porque la Hoja importa aquel módulo (`reglas_viales`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from sqlalchemy.orm import Session

from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Tramo
from adapters.vial.reglas import ReglasViales
from aplicacion import elaboracion, hoja, hoja_borradores, hoja_edicion, vial
from core import models
from core.catalog import Catalogo
from core.contracts import ItemComputo, OrigenTipo
from core.contracts.verificacion import ReglaVerificacion

__all__ = [
    "PREFIJO_TRAMO",
    "BorradorDeOtraVersion",
    "SinTramos",
    "items_de_tramos",
    "llevar_tramos_a_la_hoja",
    "sincronizar_renglones",
]

#: Prefijo del `origen_id` de una cantidad derivada de un tramo («tramo:T1:capa:3»).
PREFIJO_TRAMO = "tramo:"


class SinTramos(LookupError):  # noqa: N818
    """La versión no tiene tramos que llevar al presupuesto (la API responde 409)."""


class BorradorDeOtraVersion(Exception):  # noqa: N818
    """El borrador de la Hoja de la obra es (o sería) de otra versión que la de los tramos que se
    quieren llevar (la API responde 409); el mensaje dice las dos y qué hacer."""


def items_de_tramos(tramos: Sequence[Tramo]) -> list[ItemComputo]:
    """Los renglones que los tramos llevan a la Hoja: las cantidades de `derivar_tramos`, tal cual
    (origen «tramo:…», origen REGLA, su regla y sus parámetros)."""
    return derivar_tramos(tramos)


def _de_tramo(item: ItemComputo) -> bool:
    return item.origen_id.startswith(PREFIJO_TRAMO)


def sincronizar_renglones(
    borrador: hoja.Borrador, items: Sequence[ItemComputo], reglas: Sequence[ReglaVerificacion]
) -> hoja.Borrador:
    """El borrador con los renglones de tramo reemplazados por `items` y las reglas viales por
    `reglas` (Tarea 8b, reglas 1, 2 y 4).

    - Los renglones cuyo `origen_id` empieza por «tramo:» salen; `items` entran en el sitio del
      primero de ellos (al final si no había ninguno), así llevar otra vez no reordena la Hoja.
      Los demás renglones, sus cantidades escritas y sus notas no se tocan.
    - La cantidad escrita sobre un renglón de tramo cuya clave (`codigo|origen_id`) sigue se
      conserva; la de una clave que desaparece se descarta, con su nota. Un renglón que volvió de
      una versión guardada con su cantidad escrita a mano llega en `items_base` como MANUAL con esa
      cantidad: se conserva como escrita sobre la derivada (así VR1 sigue avisando).
    - `reglas_extra`: las `ReglasViales` anteriores salen y entran `reglas`; R11 y R12 quedan.
    """
    base = borrador.items_base
    claves = hoja.claves_de_items(hoja.items_sin_escribir(borrador))[: len(base)]
    viejos = {clave: item for clave, item in zip(claves, base, strict=True) if _de_tramo(item)}
    resto = [item for item in base if not _de_tramo(item)]
    primero = next((n for n, item in enumerate(base) if _de_tramo(item)), len(base))
    sitio = sum(1 for item in base[:primero] if not _de_tramo(item))
    nueva_base = (*resto[:sitio], *items, *resto[sitio:])

    provisional = replace(borrador, items_base=nueva_base)
    nuevas_claves = hoja.claves_de_items(hoja.items_sin_escribir(provisional))[: len(nueva_base)]
    pares = zip(nuevas_claves, nueva_base, strict=True)
    nuevos = {clave: item for clave, item in pares if _de_tramo(item)}

    def sigue(clave: str) -> bool:
        return clave not in viejos or clave in nuevos

    cantidades = {clave: v for clave, v in borrador.cantidades.items() if sigue(clave)}
    for clave, item in nuevos.items():
        viejo = viejos.get(clave)
        if (
            clave not in cantidades
            and viejo is not None
            and viejo.origen_tipo is OrigenTipo.MANUAL
            and viejo.cantidad != item.cantidad
        ):
            cantidades[clave] = viejo.cantidad
    return replace(
        provisional,
        cantidades=cantidades,
        notas={clave: nota for clave, nota in borrador.notas.items() if sigue(clave)},
        reglas_extra=(
            *(r for r in borrador.reglas_extra if not isinstance(r, ReglasViales)),
            *reglas,
        ),
    )


def _otra_version(abierto: bool, del_borrador: str | None, vista: str) -> BorradorDeOtraVersion:
    """El 409 cuando el borrador de la obra no es de la versión que se ve, con lo que la Hoja deja
    hacer: guardar o descartar el borrador abierto, abrir otra versión, o elegir aquí la del
    borrador."""
    if abierto and del_borrador is None:
        return BorradorDeOtraVersion(
            f"La Hoja de la obra tiene abierto un borrador en blanco; está viendo los tramos de "
            f"{vista}. Guarde o descarte ese borrador en la Hoja y vuelva a llevar."
        )
    if abierto:
        return BorradorDeOtraVersion(
            f"La Hoja de la obra tiene abierto un borrador de {del_borrador}; está viendo los "
            f"tramos de {vista}. Guarde o descarte ese borrador en la Hoja, o elija "
            f"{del_borrador} aquí, y vuelva a llevar."
        )
    return BorradorDeOtraVersion(
        f"La Hoja de la obra se abrirá sobre la versión vigente, {del_borrador}; está viendo los "
        f"tramos de {vista}. Elija {del_borrador} aquí, o abra {vista} en la Hoja, y vuelva a "
        "llevar."
    )


def _sin_apu(sesion: Session, items: Sequence[ItemComputo]) -> list[str]:
    """Los códigos de `items` que no están en el catálogo de la carpeta, ordenados."""
    catalogo = Catalogo(sesion)
    faltan = []
    for codigo in sorted({item.codigo_partida for item in items}):
        try:
            catalogo.partida(codigo)
        except KeyError:
            faltan.append(codigo)
    return faltan


def llevar_tramos_a_la_hoja(
    sesion: Session,
    huella_ficha: str,
    url: str,
    proyecto: models.Proyecto,
    version: str,
    *,
    responsable: str,
    hoy: date,
) -> tuple[str, int]:
    """Lleva las cantidades de los tramos de la versión `version` (código) de la obra al borrador
    de su Hoja y devuelve el id del borrador y cuántos renglones de tramo tiene ahora. No guarda
    versión.

    Antes de abrir nada: `vial.VersionInexistente` si la versión no es de la obra;
    `BorradorDeOtraVersion` si el borrador de la obra es (o sería) de otra versión; `SinTramos` si
    la versión no tiene tramos (propios ni heredados); `hoja_edicion.PartidaFueraDelCatalogo` con
    **todos** los códigos que faltan. Después abre o toma el borrador
    (`elaboracion.borrador_de_la_obra`) y sincroniza (`sincronizar_renglones`) con las reglas
    viales de los tramos de ahora, por el núcleo de edición de la Hoja
    (`hoja_edicion.cambiar_borrador`). Todo o nada.

    Si los renglones no cambian, el `rev` no sube: solo se rearman las reglas (no son un cambio) y
    se invalida la vista calculada, para que la auditoría las use."""
    version_id = vial.version_de(sesion, proyecto.nombre, version)
    existente, del_borrador = elaboracion.version_del_borrador_de_la_obra(
        sesion, huella_ficha, url, proyecto.nombre
    )
    if del_borrador != version:
        raise _otra_version(existente is not None, del_borrador, version)
    tramos = vial.tramos_de_version(sesion, version_id)
    if not tramos:
        raise SinTramos(
            f"La versión {version} no tiene tramos: impórtelos en «Tramos de la vía» antes de "
            "llevarlos al presupuesto."
        )
    items = items_de_tramos(tramos)
    faltan = _sin_apu(sesion, items)
    if faltan:
        raise hoja_edicion.PartidaFueraDelCatalogo(*faltan)
    reglas = vial.reglas_viales(sesion, version_id, hoy=hoy)  # VR2: la receta vigente de hoy

    vivo, nuevo = elaboracion.borrador_de_la_obra(
        sesion, huella_ficha, url, proyecto, responsable=responsable, hoy=hoy
    )

    def construir(actual: hoja_borradores.BorradorVivo) -> hoja.Borrador | None:
        sincronizado = sincronizar_renglones(actual.borrador, items, reglas)
        if sincronizado == actual.borrador:  # `reglas_extra` no cuenta en la igualdad
            actual.borrador, actual.calculo = sincronizado, None
            return None
        return sincronizado

    with vivo.cerrojo:
        antes = (vivo.borrador, vivo.rev, vivo.calculo, vivo.tamano)
        try:
            if vivo.version != version:  # otra ventana abrió otro borrador entretanto
                raise hoja_borradores.RevDesactualizado(vivo.id)
            hoja_edicion.cambiar_borrador(sesion, huella_ficha, vivo.id, vivo.rev, construir)
        except BaseException:
            if nuevo:
                hoja_borradores.descartar(huella_ficha, vivo.id)
            else:
                vivo.borrador, vivo.rev, vivo.calculo, vivo.tamano = antes
            raise
    return vivo.id, len(items)
