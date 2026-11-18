"""Por qué la Hoja no puede valorar una partida con la lista de la versión y qué hacer.

La Hoja arma el APU de cada partida nueva del borrador desde el catálogo, con la lista de la
versión abierta y a la fecha del borrador (`hoja_edicion.completar`); si no puede, la deja
PENDIENTE («PENDIENTE: sin APU en el catálogo») sin decir por qué. Quien decide es siempre la Hoja;
este módulo solo **redacta** el motivo: qué insumos no tienen precio en qué lista, en qué otras
listas están, qué rendimiento falta a esa fecha y qué hacer.

Lo usan llevar los tramos al presupuesto (`aplicacion.hoja_vial`, pasada de navegador del
31/10/2026) y agregar una partida a una versión (`elaboracion.explicar_pendiente`, prueba en vivo
del 18/11/2026: una partida compuesta hoy en Componer deja sus precios en una lista nueva «… al
<hoy>», `listas_para_armar.lista_de_hoy`, y las versiones siguen con su lista de antes). Solo
importa `hoja_edicion` (la base de su error): la política de «rendimiento vigente» llega como
`vigente`, y quien llama pasa la de siempre, `aplicacion.elaboracion.es_rendimiento_vigente`; así
no se cierra ningún ciclo de importaciones.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.hoja_edicion import SinListaDeLaObra
from aplicacion.listas_para_armar import lista_para_armar
from core import models
from core.catalog import Catalogo
from core.catalog.errores import CatalogoIncompleto

__all__ = [
    "DE_NUEVO",
    "INSUMOS_POR_PARTIDA",
    "PartidasSinValorar",
    "SinValorar",
    "Vigente",
    "explicar",
    "fecha_para_componer",
    "listas_con_precio",
    "mensaje_sin_valorar",
    "por_que",
]

#: Cuántos insumos sin precio se nombran por partida (el resto solo se cuenta).
INSUMOS_POR_PARTIDA = 3

DE_NUEVO = (
    "si la partida ya existía, cambie también las condiciones del rendimiento para que se "
    "registre de nuevo"
)


class PartidasSinValorar(SinListaDeLaObra):
    """Alguna partida está en el catálogo, pero la Hoja no puede armar su APU con la lista de la
    versión y a su fecha: quedaría PENDIENTE (la API responde 409). El mensaje dice qué partidas,
    qué insumos faltan en qué lista, qué rendimiento falta y qué hacer. Es un caso de «no hay con
    qué valorar» (`SinListaDeLaObra`): toda ruta de la Hoja que ya responde 409 a aquel responde
    igual a este."""


@dataclass(frozen=True, slots=True)
class SinValorar:
    """Por qué la Hoja no puede armar el APU de una partida con su lista y a su fecha."""

    codigo: str
    sin_rendimiento: bool
    sin_precio: tuple[str, ...]  # las descripciones de los insumos sin precio en la lista
    insumos_sin_precio: tuple[int, ...]
    otro: str | None  # el motivo del catálogo cuando no es ninguno de los dos


#: La política de «rendimiento vigente» (`elaboracion.es_rendimiento_vigente`): tipo y fecha del
#: rendimiento, y la fecha a la que se valora.
Vigente = Callable[[str, date, date], bool]


def por_que(
    sesion: Session, codigo: str, lista: models.ListaPrecios, fecha: date, vigente: Vigente
) -> SinValorar:
    """Por qué la Hoja no armó la partida `codigo` (solo para redactar el mensaje; quien decide es
    `hoja_edicion.completar`): rendimiento vigente al `fecha` (`vigente`), y los insumos de su APU
    sin precio en `lista`; si no es nada de eso, el motivo del catálogo."""
    partida = sesion.scalars(select(models.Partida).where(models.Partida.codigo == codigo)).one()
    con_rendimiento = any(vigente(r.tipo, r.fecha, fecha) for r in partida.rendimientos)
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
    return SinValorar(
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


def listas_con_precio(sesion: Session, insumos: set[int], fuera: int) -> list[str]:
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


def _componer_escribe_en(sesion: Session, lista: models.ListaPrecios, fecha: date) -> bool:
    """Si Componer, guardando con `fecha`, deja sus precios en `lista`: cuando es la lista para
    armar a esa fecha y rige desde ese mismo día (`listas_para_armar.lista_de_hoy`). Solo lee."""
    try:
        para_armar = lista_para_armar(sesion, fecha)
    except ValueError:  # SinListaParaArmar
        return False
    return para_armar.id == lista.id and lista.fecha_vigencia == fecha


def fecha_para_componer(sesion: Session, lista: models.ListaPrecios, fecha: date) -> date | None:
    """La fecha con que Componer deja sus precios en `lista` y un rendimiento que la Hoja acepta a
    `fecha` (la del borrador), o `None` si no hay ninguna. Primero `fecha` misma; si no, el día
    desde que rige `lista` (no posterior a `fecha`): una versión guardada después de crear su
    lista tiene fecha propia, y Componer a hoy escribiría en otra lista (prueba en vivo del
    18/11/2026)."""
    if _componer_escribe_en(sesion, lista, fecha):
        return fecha
    desde = lista.fecha_vigencia
    if desde <= fecha and _componer_escribe_en(sesion, lista, desde):
        return desde
    return None


def _citadas(textos: Sequence[str]) -> str:
    return ", ".join(f"«{texto}»" for texto in textos)


def _insumos(descripciones: Sequence[str]) -> str:
    resto = len(descripciones) - INSUMOS_POR_PARTIDA
    nombradas = _citadas(descripciones[:INSUMOS_POR_PARTIDA])
    return nombradas if resto <= 0 else f"{nombradas} y {resto} más"


def mensaje_sin_valorar(
    faltas: Sequence[SinValorar],
    lista: models.ListaPrecios,
    version: str,
    fecha: date,
    otras_listas: Sequence[str],
    *,
    componer_con: date | None,
    inicio: str,
    se_valora: str = "se pueden valorar",
    esas: str = "esas partidas",
    cierre: str = "Luego vuelva a llevar.",
) -> str:
    """El 409 de `PartidasSinValorar`: qué partidas, por qué y qué hacer, en un solo párrafo.

    `inicio` abre el mensaje («No se llevó nada: 2 partidas quedarían pendientes en el
    Presupuesto»); `cierre` lo termina. `componer_con` es la fecha con que guardar en Componer deja
    los precios en `lista` (`fecha_para_componer`), o `None`."""
    sin_precio = [f for f in faltas if f.sin_precio]
    como = ", sin precio," if sin_precio else ""
    partes = [
        f"{inicio}{como} porque el Presupuesto arma cada APU con la lista «{lista.nombre}» de la "
        f"versión {version}, al {fecha:%d/%m/%Y}, y con ella no {se_valora}."
    ]
    if sin_precio:
        detalle = "; ".join(f"«{f.codigo}» ({_insumos(f.sin_precio)})" for f in sin_precio)
        partes.append(f"Insumos sin precio en «{lista.nombre}»: {detalle}.")
        if otras_listas:
            partes.append(f"Esos precios están en {_citadas(otras_listas)}.")
    sin_rendimiento = [f.codigo for f in faltas if f.sin_rendimiento]
    if sin_rendimiento:
        partes.append(
            f"Sin rendimiento registrado al {fecha:%d/%m/%Y} o antes: {_citadas(sin_rendimiento)}."
        )
    otros = [f for f in faltas if f.otro is not None]
    if otros:
        partes.append("; ".join(f"«{f.codigo}»: {f.otro}" for f in otros) + ".")
    if componer_con is not None:
        partes.append(
            f"Qué hacer: en Componer, guarde {esas} con fecha {componer_con:%d/%m/%Y}: sus precios "
            f"quedan en «{lista.nombre}» y su rendimiento a esa fecha ({DE_NUEVO}). {cierre}"
        )
    else:
        pasos = [f"cargue esos precios en «{lista.nombre}»"] if sin_precio else []
        if sin_rendimiento:
            pasos.append(
                f"en Componer, guarde {esas} con fecha {fecha:%d/%m/%Y} o anterior ({DE_NUEVO})"
            )
        partes.append(f"Qué hacer: {'; '.join(pasos)}. {cierre}")
    return " ".join(partes)


def explicar(
    sesion: Session,
    faltan: Sequence[str],
    lista: models.ListaPrecios,
    version: str,
    fecha: date,
    *,
    vigente: Vigente,
    **textos: str,
) -> str:
    """El mensaje de `PartidasSinValorar` para las partidas `faltan` (las que la Hoja dejó sin
    componer con `lista` a `fecha`): el motivo de cada una (`por_que`), las otras listas con esos
    precios y la fecha con que Componer los deja en `lista`. `textos`: `inicio` y, si cambian, los
    demás textos de `mensaje_sin_valorar`."""
    faltas = [por_que(sesion, codigo, lista, fecha, vigente) for codigo in faltan]
    insumos = {insumo for falta in faltas for insumo in falta.insumos_sin_precio}
    return mensaje_sin_valorar(
        faltas,
        lista,
        version,
        fecha,
        listas_con_precio(sesion, insumos, lista.id),
        componer_con=fecha_para_componer(sesion, lista, fecha),
        **textos,
    )
