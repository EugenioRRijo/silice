"""Llevar a la Hoja el libro auditado (libro por frentes, ola 2, línea 3, 2026-11-13).

La prueba de punta a punta del 2026-11-13 auditó un libro vial con un APU por hoja y un
presupuesto con una hoja por frente, y después hubo que teclear en la Hoja los APU de cada frente.
Aquí el libro ya auditado (`fusion.apu_por_hoja`, que quien llama corre: `aplicacion` no importa
`fusion`) llega al borrador de la Hoja de una obra **sin teclear**:

1. **El catálogo.** Cada APU que usa algún renglón entra con sus materiales, equipos y mano de obra,
   su rendimiento y sus precios, por la misma puerta que Componer (`Catalogo.cargar_composicion` en
   la lista de `listas_para_armar.lista_de_hoy`, la lista para armar a la fecha del borrador). Si el
   código ya está con la **misma** composición y los mismos precios, se reutiliza (llevar otra vez
   no duplica nada); si está con otra, entra como variante «-B», «-C»… (otro frente con otro precio;
   D6). Cada precio que escribe el libro lleva su referencia: «<libro>, <HOJA!CELDA>»
   (`core.catalog.origen.fijar_referencia`), así la pestaña Precios dice de dónde salió.
2. **Los renglones.** Con presupuesto, uno por renglón enlazado con su APU, con la cantidad del
   presupuesto, su origen (`libro:<HOJA!CELDA>` de la cantidad, TABULAR) y su frente (la hoja del
   presupuesto, `aplicacion.frentes`). Sin presupuesto, uno por APU con la cantidad de su cabecera y
   el frente que se diga. Un renglón sin APU o sin cantidad no se lleva y se dice. Llevar otra vez
   reemplaza los renglones de las mismas hojas; los demás no se tocan.
3. **Los porcentajes.** La Hoja lleva un solo juego de parámetros por obra: los del libro
   (prestaciones como FCAS, administración y utilidad) pasan al borrador; si las hojas usan juegos
   distintos, `PorcentajesDistintos` (422) dice cuáles.

Reglas que protegen los precios (D6): el libro se lleva a una obra **sin versiones** (una versión
ya valorada con otra lista dejaría los precios del libro fuera; `ObraConVersiones`, 409), y su
moneda, que declara quien lo lleva, debe ser la de la lista para armar (`MonedaDistinta`, 409):
ningún precio cambia de moneda en silencio. Todo o nada: si algo falla, el catálogo se deshace y el
borrador vuelve a como estaba.

La respuesta dice, por partida, el P.U. impreso en el libro y el que da la Hoja con lo llevado, y si
casan (`TOLERANCIA_PRECIO`, un centavo): un APU con financiamiento o con bono por renglón no casa
(la auditoría ya lo dijo: AH2 y AH3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.vial.constantes import TOLERANCIA_PRECIO
from aplicacion import elaboracion, hoja, hoja_borradores, hoja_edicion, importaciones
from aplicacion.frentes import con_frente
from aplicacion.listas_para_armar import lista_de_hoy, lista_para_armar
from core import models
from core.catalog import Catalogo, CatalogoIncompleto
from core.catalog.origen import fijar_referencia
from core.contracts import Dominio, ItemComputo, OrigenTipo
from core.contracts.apu import ComposicionAPU, ParametrosCosto

__all__ = [
    "PREFIJO_LIBRO",
    "ApuDelLibro",
    "LibroLlevado",
    "LibroParaLlevar",
    "LibroSinRenglones",
    "MonedaDistinta",
    "ObraConVersiones",
    "PartidaLlevada",
    "PorcentajesDistintos",
    "RenglonDelLibro",
    "llevar_libro_a_la_hoja",
]

#: El prefijo del `origen_id` de un renglón que vino del libro: «libro:FRENTE A!E4».
PREFIJO_LIBRO = "libro:"
#: Largo de `referencia_precio.referencia` (`core/models/entidades.py`).
_LARGO_REFERENCIA = 60
_VARIANTES = "BCDEFGHIJKLMNOPQRSTUVWXYZ"
_CIEN = Decimal(100)


class LibroSinRenglones(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """No queda ningún renglón que llevar (la API responde 422); el mensaje dice por qué."""


class PorcentajesDistintos(ValueError):  # noqa: N818
    """Las hojas del libro usan porcentajes distintos y la Hoja lleva uno por obra (422)."""


class MonedaDistinta(Exception):  # noqa: N818
    """El libro está en otra moneda que la lista para armar de la carpeta (409)."""


class ObraConVersiones(Exception):  # noqa: N818
    """La obra ya tiene versiones: el libro se lleva a una obra sin versiones (409)."""


@dataclass(frozen=True, slots=True)
class ApuDelLibro:
    """Una hoja de APU auditada: su composición (con el código del libro) y sus parámetros, el P.U.
    impreso y el que recalculó la auditoría, la cantidad de la cabecera con su celda y la celda del
    precio de cada línea, en el orden canónico (materiales, equipos y mano de obra)."""

    hoja: str
    numero: int | None
    composicion: ComposicionAPU
    parametros: ParametrosCosto
    precio_impreso: Decimal
    cantidad: Decimal | None = None
    celda_cantidad: str | None = None
    celdas_precio: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RenglonDelLibro:
    """Un renglón del presupuesto: su hoja (el frente), el número que lo enlaza con su APU, la
    cantidad (`None` si la celda no trae un número) y la celda de la cantidad («FRENTE A!E4»)."""

    hoja: str
    numero: int
    cantidad: Decimal | None
    celda_cantidad: str


@dataclass(frozen=True, slots=True)
class LibroParaLlevar:
    """El libro auditado: su nombre, sus APU, los renglones del presupuesto (vacío sin él), la
    moneda que declara quien lo lleva y, sin presupuesto, el frente de todos sus renglones."""

    archivo: str
    apus: tuple[ApuDelLibro, ...]
    renglones: tuple[RenglonDelLibro, ...] = ()
    moneda: str = ""
    frente: str | None = None


@dataclass(frozen=True, slots=True)
class PartidaLlevada:
    """Una partida llevada: su código en Sílice (el del libro o su variante), el del libro, su
    hoja, si entró nueva al catálogo, el P.U. impreso, el de la Hoja (`None` si quedó pendiente) y
    si casan."""

    codigo: str
    codigo_libro: str
    hoja: str
    nueva: bool
    precio_impreso: Decimal
    precio_hoja: Decimal | None
    casa: bool


@dataclass(frozen=True, slots=True)
class LibroLlevado:
    """Lo que quedó en el borrador: su id, cuántos renglones del libro tiene, las partidas, los
    renglones que no se llevaron (sin APU o sin cantidad), la lista y la moneda."""

    borrador_id: str
    renglones: int
    partidas: tuple[PartidaLlevada, ...]
    sin_apu: tuple[str, ...]
    sin_cantidad: tuple[str, ...]
    lista: str
    moneda: str


# --- los renglones y los porcentajes ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Renglon:
    apu: ApuDelLibro
    cantidad: Decimal
    celda: str  # la de la cantidad: el origen del renglón
    frente: str | None


def _renglones(libro: LibroParaLlevar) -> tuple[list[_Renglon], list[str], list[str]]:
    """Los renglones que se llevan, los que no tienen APU y los que no tienen cantidad."""
    por_numero: dict[int, ApuDelLibro] = {}
    for apu in libro.apus:
        if apu.numero is not None:
            por_numero.setdefault(apu.numero, apu)
    llevar, sin_apu, sin_cantidad = [], [], []
    if libro.renglones:
        for r in libro.renglones:
            quien = f"{r.hoja}, renglón {r.numero}"
            apu = por_numero.get(r.numero)
            if apu is None:
                sin_apu.append(quien)
            elif r.cantidad is None:
                sin_cantidad.append(quien)
            else:
                llevar.append(_Renglon(apu, r.cantidad, r.celda_cantidad, r.hoja))
        return llevar, sin_apu, sin_cantidad
    for apu in libro.apus:
        if apu.cantidad is None or apu.celda_cantidad is None:
            sin_cantidad.append(apu.hoja)
        else:
            llevar.append(_Renglon(apu, apu.cantidad, apu.celda_cantidad, libro.frente))
    return llevar, sin_apu, sin_cantidad


def _y(textos: Sequence[str]) -> str:
    return textos[0] if len(textos) == 1 else f"{', '.join(textos[:-1])} y {textos[-1]}"


def _pct(fraccion: Decimal) -> str:
    texto = format((fraccion * _CIEN).normalize(), "f")
    return texto.replace(".", ",")


_CAMPOS = (
    ("fcas", "unas prestaciones"),
    ("administracion", "una administración"),
    ("utilidad", "una utilidad"),
)


def _porcentajes(apus: Sequence[ApuDelLibro]) -> ParametrosCosto:
    """El único juego de porcentajes de las hojas que se llevan; `PorcentajesDistintos` si hay
    más de uno: dice, del juego que usa la mayoría, en qué se apartan las demás hojas."""
    grupos: dict[ParametrosCosto, list[str]] = {}
    for apu in apus:
        grupos.setdefault(apu.parametros, [])
        if apu.hoja not in grupos[apu.parametros]:
            grupos[apu.parametros].append(apu.hoja)
    if len(grupos) == 1:
        return next(iter(grupos))
    mayoria = max(grupos, key=lambda p: len(grupos[p]))
    partes = []
    for parametros, hojas in grupos.items():
        if parametros == mayoria:
            continue
        distintos = [(c, t) for c, t in _CAMPOS if getattr(parametros, c) != getattr(mayoria, c)]
        suyo = _y([f"{t} del {_pct(getattr(parametros, c))} %" for c, t in distintos])
        demas = _y([f"del {_pct(getattr(mayoria, c))} %" for c, _t in distintos])
        partes.append(f"{_y(hojas)} usa{'n' if len(hojas) > 1 else ''} {suyo} y las demás {demas}")
    raise PorcentajesDistintos(
        "Las hojas del libro no usan los mismos porcentajes y la Hoja lleva uno solo por obra: "
        + "; ".join(partes)
        + "."
    )


# --- el catálogo --------------------------------------------------------------------------------


def _misma(catalogo: Catalogo, composicion: ComposicionAPU, fecha: date, lista) -> bool:
    try:
        guardada = catalogo.composicion(composicion.codigo_partida, fecha=fecha, lista=lista)
    except (KeyError, ValueError, CatalogoIncompleto):
        return False
    return guardada == composicion


def _existe(sesion: Session, codigo: str) -> bool:
    return (
        sesion.scalar(select(models.Partida.id).where(models.Partida.codigo == codigo)) is not None
    )


def _al_catalogo(
    sesion: Session,
    apu: ApuDelLibro,
    lista: models.ListaPrecios,
    fecha: date,
    dominio: Dominio,
    archivo: str,
) -> tuple[str, bool]:
    """El código con que el APU queda en el catálogo y si entró nuevo (ver la cabecera, punto 1)."""
    catalogo = Catalogo(sesion)
    base = apu.composicion.codigo_partida
    for codigo in (base, *(f"{base}-{letra}" for letra in _VARIANTES)):
        composicion = replace(apu.composicion, codigo_partida=codigo)
        if not _existe(sesion, codigo):
            condiciones = f"Rendimiento del libro «{archivo}», hoja {apu.hoja}"
            catalogo.cargar_composicion(composicion, lista, dominio, fecha, condiciones)
            # `cargar_composicion` agrega los precios sin pasar por `lista.precios`, y
            # `Catalogo.composicion` lee esa colección: si ya se cargó en esta sesión (al
            # comparar otra partida), no los vería. Expediente de `core/` propuesto en la bitácora.
            sesion.expire(lista, ["precios"])
            _referenciar(sesion, codigo, lista, apu, archivo)
            return codigo, True
        if _misma(catalogo, composicion, fecha, lista):
            return codigo, False
    raise LibroSinRenglones(f"La partida «{base}» ya tiene demasiadas variantes en el catálogo.")


def _referenciar(
    sesion: Session, codigo: str, lista: models.ListaPrecios, apu: ApuDelLibro, archivo: str
) -> None:
    """La referencia de cada precio que el libro puso en la lista (solo si ese precio no tenía
    una: un precio que ya estaba con su fuente la conserva)."""
    partida = sesion.scalars(select(models.Partida).where(models.Partida.codigo == codigo)).one()
    lineas = sesion.scalars(
        select(models.ComposicionAPU)
        .where(models.ComposicionAPU.partida_id == partida.id)
        .order_by(models.ComposicionAPU.orden)
    ).all()
    for linea, celda in zip(lineas, apu.celdas_precio, strict=False):
        precio = sesion.scalars(
            select(models.PrecioInsumo).where(
                models.PrecioInsumo.lista_id == lista.id,
                models.PrecioInsumo.insumo_id == linea.insumo_id,
            )
        ).one_or_none()
        if precio is None or sesion.get(models.ReferenciaPrecio, precio.id) is not None:
            continue
        insumo = sesion.get(models.Insumo, linea.insumo_id)
        fijar_referencia(sesion, lista, insumo, f"{archivo}, {celda}"[:_LARGO_REFERENCIA])


# --- llevar ------------------------------------------------------------------------------------


def _hoja_del_origen(origen_id: str) -> str | None:
    if not origen_id.startswith(PREFIJO_LIBRO) or "!" not in origen_id:
        return None
    return origen_id[len(PREFIJO_LIBRO) :].rsplit("!", 1)[0]


def _dominio(proyecto: models.Proyecto) -> Dominio:
    try:
        return Dominio(proyecto.dominio)
    except ValueError:  # una obra sin dominio declarado se presupuesta como obra civil
        return Dominio.CIVIL


def _exigir_moneda(sesion: Session, libro: LibroParaLlevar, fecha: date) -> models.ListaPrecios:
    base = lista_para_armar(sesion, fecha)  # SinListaParaArmar (un ValueError) si no la hay
    if libro.moneda != base.moneda:
        raise MonedaDistinta(
            f"El libro está en {libro.moneda} y esta carpeta arma en {base.moneda} (lista "
            f"«{base.nombre}»): Sílice no cambia la moneda de sus precios. Lleve el libro a una "
            f"carpeta que arme en {libro.moneda}."
        )
    return base


def llevar_libro_a_la_hoja(
    sesion: Session,
    huella: str,
    caso: str,
    proyecto: models.Proyecto,
    libro: LibroParaLlevar,
    *,
    responsable: str,
    hoy: date,
) -> LibroLlevado:
    """Lleva el libro auditado al borrador de la Hoja de `proyecto` (ver la cabecera del módulo) y
    confirma el catálogo. No guarda versión: los renglones quedan como altas del borrador."""
    llevar, sin_apu, sin_cantidad = _renglones(libro)
    if not llevar:
        raise LibroSinRenglones(
            "Ningún renglón del libro se puede llevar: ninguno tiene su hoja de APU y su cantidad."
        )
    usados = list({id(r.apu): r.apu for r in llevar}.values())
    parametros = _porcentajes(usados)
    existente, vigente = elaboracion.version_del_borrador_de_la_obra(
        sesion, huella, caso, proyecto.nombre
    )
    if vigente is not None:
        raise ObraConVersiones(
            f"La obra «{proyecto.nombre}» ya tiene la versión {vigente}: el libro se lleva a una "
            "obra sin versiones, para que sus precios sean los del libro. Cree una obra nueva para "
            "el libro."
        )
    fecha = existente.borrador.fecha if existente is not None else hoy
    _exigir_moneda(sesion, libro, fecha)
    vivo, nuevo = elaboracion.borrador_de_la_obra(
        sesion, huella, caso, proyecto, responsable=responsable, hoy=hoy
    )
    hojas = {_hoja_del_origen(f"{PREFIJO_LIBRO}{r.celda}") for r in llevar}
    with vivo.cerrojo:
        antes = (vivo.borrador, vivo.rev, vivo.calculo, vivo.tamano, vivo.importaciones)
        try:
            ajenos = [
                i for i in vivo.borrador.items_base if _hoja_del_origen(i.origen_id) not in hojas
            ]
            if ajenos and vivo.borrador.parametros != parametros:
                raise PorcentajesDistintos(
                    "El borrador de la obra ya tiene renglones con otros porcentajes: lleve el "
                    "libro a una obra nueva o quite esos renglones."
                )
            lista = lista_de_hoy(sesion, vivo.borrador.fecha, nueva_si_usada=False)
            dominio = _dominio(proyecto)
            codigos: dict[int, tuple[str, bool]] = {}
            for apu in usados:
                codigos[id(apu)] = _al_catalogo(
                    sesion, apu, lista, vivo.borrador.fecha, dominio, libro.archivo
                )
            items = [
                con_frente(
                    ItemComputo(
                        codigo_partida=codigos[id(r.apu)][0],
                        descripcion=r.apu.composicion.descripcion,
                        unidad=r.apu.composicion.unidad,
                        cantidad=r.cantidad,
                        origen_id=f"{PREFIJO_LIBRO}{r.celda}",
                        origen_tipo=OrigenTipo.TABULAR,
                        dominio=dominio,
                    ),
                    r.frente,
                )
                for r in llevar
            ]

            def construir(actual: hoja_borradores.BorradorVivo) -> hoja.Borrador:
                propios = [
                    i
                    for i in actual.borrador.items_base
                    if _hoja_del_origen(i.origen_id) not in hojas
                ]
                return replace(
                    actual.borrador, items_base=(*propios, *items), parametros=parametros
                )

            vivo = hoja_edicion.cambiar_borrador(sesion, huella, vivo.id, vivo.rev, construir)
            faltan = sorted({i.codigo_partida for i in items} - set(vivo.borrador.composiciones))
            if faltan:
                raise LibroSinRenglones(
                    f"La Hoja no pudo valorar {_y([f'«{c}»' for c in faltan])} con la lista "
                    f"«{lista.nombre}»."
                )
            importaciones.anotar(
                vivo,
                importaciones.nueva(
                    "computo",
                    libro.archivo,
                    responsable,
                    f"{importaciones.resumen_de_computo(len(items))} del libro",
                ),
            )
            sesion.commit()
        except BaseException:
            sesion.rollback()
            if nuevo:
                hoja_borradores.descartar(huella, vivo.id)
            else:
                vivo.borrador, vivo.rev, vivo.calculo, vivo.tamano, vivo.importaciones = antes
            raise
    precios = {
        p.item.codigo_partida: p.resultado.precio_unitario
        for p in hoja.elaborar_borrador(vivo.borrador).elaboracion.presupuesto.partidas
    }
    tolerancia = Decimal(TOLERANCIA_PRECIO.valor)
    partidas = []
    for apu in usados:
        codigo, nueva = codigos[id(apu)]
        en_la_hoja = precios.get(codigo)
        casa = en_la_hoja is not None and abs(en_la_hoja - apu.precio_impreso) <= tolerancia
        partidas.append(
            PartidaLlevada(
                codigo,
                apu.composicion.codigo_partida,
                apu.hoja,
                nueva,
                apu.precio_impreso,
                en_la_hoja,
                casa,
            )
        )
    return LibroLlevado(
        borrador_id=vivo.id,
        renglones=len(items),
        partidas=tuple(partidas),
        sin_apu=tuple(sin_apu),
        sin_cantidad=tuple(sin_cantidad),
        lista=lista.nombre,
        moneda=libro.moneda,
    )
