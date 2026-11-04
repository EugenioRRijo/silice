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
- **Partidas que la Hoja no puede valorar:** `PartidasSinValorar` (409). La Hoja arma el APU de
  cada partida nueva desde el catálogo con la lista de la versión abierta y a la fecha del borrador
  (`hoja_edicion.cambiar_borrador` → `hoja_edicion.completar` → `hoja.completar_composiciones`) y,
  si no puede, la deja PENDIENTE sin decir por qué. Llevar corre esa misma función (no una copia)
  antes de cambiar nada, y dice qué partidas, qué insumos faltan en qué lista y qué rendimiento
  falta a esa fecha (pasada de navegador del 31/10/2026: APU compuestos en Componer en otra fecha
  dejaban pendientes los 20 renglones de la vía en DEMO-001).
- **Reglas:** llevar rearma las reglas viales del borrador (`reglas_extra`) con los tramos de ese
  momento y, para VR2, la fórmula de la receta vigente el día `hoy` de la mezcla propia de cada
  partida de mezcla (`vial.formulas_de_trabajo`, Tarea 16b).
- **Todo o nada**, con el cerrojo del borrador: si algo falla, el borrador abierto aquí se descarta
  y uno que ya existía vuelve a como estaba, con su `rev`.

Vive aparte de `aplicacion/vial.py` porque la Hoja importa aquel módulo (`reglas_viales`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Tramo
from adapters.vial.reglas import ReglasViales
from aplicacion import elaboracion, hoja, hoja_borradores, hoja_edicion, vial
from aplicacion.listas_para_armar import lista_para_armar
from core import models
from core.catalog import Catalogo, CatalogoIncompleto
from core.contracts import ItemComputo, OrigenTipo, TipoRendimiento
from core.contracts.verificacion import ReglaVerificacion

__all__ = [
    "PREFIJO_TRAMO",
    "BorradorDeOtraVersion",
    "PartidasSinValorar",
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


class PartidasSinValorar(Exception):  # noqa: N818
    """Alguna partida de los tramos está en el catálogo, pero la Hoja no puede armar su APU con la
    lista de la versión y a su fecha: quedaría PENDIENTE (la API responde 409). El mensaje dice
    qué partidas, qué insumos faltan en qué lista, qué rendimiento falta y qué hacer."""


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
            "El Presupuesto de la obra tiene abierto un borrador en blanco; está viendo los "
            f"tramos de {vista}. Guarde o descarte ese borrador en el Presupuesto y vuelva a "
            "llevar."
        )
    if abierto:
        return BorradorDeOtraVersion(
            f"El Presupuesto de la obra tiene abierto un borrador de {del_borrador}; está viendo "
            f"los tramos de {vista}. Guarde o descarte ese borrador en el Presupuesto, o elija "
            f"{del_borrador} aquí, y vuelva a llevar."
        )
    return BorradorDeOtraVersion(
        f"El Presupuesto de la obra se abrirá sobre la versión vigente, {del_borrador}; está "
        f"viendo los tramos de {vista}. Elija {del_borrador} aquí, o abra {vista} en el "
        "Presupuesto, y vuelva a llevar."
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


#: Cuántos insumos sin precio se nombran por partida (el resto solo se cuenta).
INSUMOS_POR_PARTIDA = 3


@dataclass(frozen=True, slots=True)
class _SinValorar:
    """Por qué la Hoja no puede armar el APU de una partida con su lista y a su fecha."""

    codigo: str
    sin_rendimiento: bool
    sin_precio: tuple[str, ...]  # las descripciones de los insumos sin precio en la lista
    insumos_sin_precio: tuple[int, ...]
    otro: str | None  # el motivo del catálogo cuando no es ninguno de los dos


def _por_que(sesion: Session, codigo: str, lista: models.ListaPrecios, fecha: date) -> _SinValorar:
    """Por qué la Hoja no armó la partida `codigo` (solo para redactar el mensaje; quien decide es
    `hoja_edicion.completar`): rendimiento estimado al `fecha` o antes, y los insumos de su APU
    sin precio en `lista`; si no es nada de eso, el motivo del catálogo."""
    partida = sesion.scalars(select(models.Partida).where(models.Partida.codigo == codigo)).one()
    con_rendimiento = any(
        r.tipo == TipoRendimiento.ESTIMADO.value and r.fecha <= fecha for r in partida.rendimientos
    )
    con_precio = set(
        sesion.scalars(
            select(models.PrecioInsumo.insumo_id).where(models.PrecioInsumo.lista_id == lista.id)
        )
    )
    faltan = [linea.insumo for linea in partida.composicion if linea.insumo_id not in con_precio]
    otro = (
        None
        if faltan or not con_rendimiento
        else _motivo_del_catalogo(sesion, codigo, lista, fecha)
    )
    return _SinValorar(
        codigo,
        not con_rendimiento,
        tuple(dict.fromkeys(insumo.descripcion for insumo in faltan)),
        tuple(insumo.id for insumo in faltan),
        otro,
    )


def _motivo_del_catalogo(
    sesion: Session, codigo: str, lista: models.ListaPrecios, fecha: date
) -> str:
    try:
        Catalogo(sesion).composicion(codigo, fecha=fecha, lista=lista)
    except (KeyError, ValueError, CatalogoIncompleto) as error:
        return str(error)
    return "la Hoja no pudo armar su APU con esa lista"


def _listas_con_precio(sesion: Session, insumos: set[int], fuera: int) -> list[str]:
    """Las listas (salvo `fuera`) con precio de alguno de esos insumos, la más nueva primero: donde
    los dejó Componer."""
    if not insumos:
        return []
    filas = sesion.execute(
        select(models.ListaPrecios.nombre)
        .join(models.PrecioInsumo, models.PrecioInsumo.lista_id == models.ListaPrecios.id)
        .where(models.PrecioInsumo.insumo_id.in_(insumos), models.ListaPrecios.id != fuera)
        .group_by(models.ListaPrecios.id, models.ListaPrecios.nombre)
        .order_by(models.ListaPrecios.fecha_vigencia.desc(), models.ListaPrecios.id.desc())
    )
    return [nombre for (nombre,) in filas]


def _citadas(textos: Sequence[str]) -> str:
    return ", ".join(f"«{texto}»" for texto in textos)


def _insumos(descripciones: Sequence[str]) -> str:
    resto = len(descripciones) - INSUMOS_POR_PARTIDA
    nombradas = _citadas(descripciones[:INSUMOS_POR_PARTIDA])
    return nombradas if resto <= 0 else f"{nombradas} y {resto} más"


def _mensaje_sin_valorar(
    faltas: Sequence[_SinValorar],
    lista: models.ListaPrecios,
    version: str,
    fecha: date,
    otras_listas: Sequence[str],
    *,
    componer_sirve: bool,
) -> str:
    """El 409 de `PartidasSinValorar`: qué partidas, por qué y qué hacer, en un solo párrafo.
    `componer_sirve`: guardar en Componer con la fecha del borrador deja los precios en `lista`
    (es la lista para armar de esa misma fecha, `listas_para_armar.lista_de_hoy`)."""
    dia = f"{fecha:%d/%m/%Y}"
    cuantas = (
        "1 partida quedaría pendiente"
        if len(faltas) == 1
        else f"{len(faltas)} partidas quedarían pendientes"
    )
    sin_precio = [f for f in faltas if f.sin_precio]
    como = ", sin precio," if sin_precio else ""
    partes = [
        f"No se llevó nada: {cuantas} en el Presupuesto{como} porque el Presupuesto arma cada APU "
        f"con la lista «{lista.nombre}» de la versión {version}, al {dia}, y con ella no se pueden "
        "valorar."
    ]
    if sin_precio:
        detalle = "; ".join(f"«{f.codigo}» ({_insumos(f.sin_precio)})" for f in sin_precio)
        partes.append(f"Insumos sin precio en «{lista.nombre}»: {detalle}.")
        if otras_listas:
            partes.append(f"Esos precios están en {_citadas(otras_listas)}.")
    sin_rendimiento = [f.codigo for f in faltas if f.sin_rendimiento]
    if sin_rendimiento:
        partes.append(f"Sin rendimiento registrado al {dia} o antes: {_citadas(sin_rendimiento)}.")
    otros = [f for f in faltas if f.otro is not None]
    if otros:
        partes.append("; ".join(f"«{f.codigo}»: {f.otro}" for f in otros) + ".")
    de_nuevo = (
        "si la partida ya existía, cambie también las condiciones del rendimiento para que se "
        "registre de nuevo"
    )
    if componer_sirve:
        partes.append(
            f"Qué hacer: en Componer, guarde esas partidas con fecha {dia}: sus precios quedan en "
            f"«{lista.nombre}» y su rendimiento a esa fecha ({de_nuevo}). Luego vuelva a llevar."
        )
    else:
        pasos = [f"cargue esos precios en «{lista.nombre}»"] if sin_precio else []
        if sin_rendimiento:
            pasos.append(
                f"en Componer, guarde esas partidas con fecha {dia} o anterior ({de_nuevo})"
            )
        partes.append(f"Qué hacer: {'; '.join(pasos)}. Luego vuelva a llevar.")
    return " ".join(partes)


def _valorado(
    sesion: Session,
    vivo: hoja_borradores.BorradorVivo,
    borrador: hoja.Borrador,
    items: Sequence[ItemComputo],
    version: str,
) -> hoja.Borrador:
    """`borrador` con el APU de cada partida de `items` que aún no compone, o
    `PartidasSinValorar` si la Hoja dejaría PENDIENTE alguna.

    Quien decide es la Hoja misma: `hoja_edicion.completar` (la lista de `lista_para_completar`,
    la fecha del borrador, `hoja.completar_composiciones`), lo mismo que corre
    `hoja_edicion.cambiar_borrador`; una partida de `items` que no sale compuesta quedaría
    pendiente. `_por_que` solo redacta el motivo. Si todas salen, se devuelve ese borrador
    completo: así llevar otra vez compone una partida que había quedado pendiente aunque los
    renglones no cambien."""
    nuevas = sorted({item.codigo_partida for item in items} - set(borrador.composiciones))
    if not nuevas:
        return borrador
    completo = hoja_edicion.completar(sesion, vivo, borrador)
    faltan = [codigo for codigo in nuevas if codigo not in completo.composiciones]
    if not faltan:
        return completo
    lista, _valoracion = hoja_edicion.lista_para_completar(sesion, vivo, borrador.fecha)
    faltas = [_por_que(sesion, codigo, lista, borrador.fecha) for codigo in faltan]
    insumos = {insumo for falta in faltas for insumo in falta.insumos_sin_precio}
    otras = _listas_con_precio(sesion, insumos, lista.id)
    raise PartidasSinValorar(
        _mensaje_sin_valorar(
            faltas,
            lista,
            version,
            borrador.fecha,
            otras,
            componer_sirve=_componer_escribe_en(sesion, lista, borrador.fecha),
        )
    )


def _componer_escribe_en(sesion: Session, lista: models.ListaPrecios, fecha: date) -> bool:
    """Si Componer, guardando con `fecha`, deja sus precios en `lista`: cuando es la lista para
    armar a esa fecha y rige desde ese mismo día (`listas_para_armar.lista_de_hoy`). Solo lee."""
    try:
        para_armar = lista_para_armar(sesion, fecha)
    except ValueError:  # SinListaParaArmar
        return False
    return para_armar.id == lista.id and lista.fecha_vigencia == fecha


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
    (`elaboracion.borrador_de_la_obra`), exige que la Hoja pueda valorar cada partida con la lista
    del borrador y a su fecha (`PartidasSinValorar` si no; `_valorado`) y sincroniza
    (`sincronizar_renglones`) con las reglas viales de los tramos de ahora, por el núcleo de
    edición de la Hoja (`hoja_edicion.cambiar_borrador`). Todo o nada: si algo falla, el borrador
    abierto aquí se descarta y el que ya estaba queda como estaba.

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
        sincronizado = _valorado(sesion, actual, sincronizado, items, version)
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
