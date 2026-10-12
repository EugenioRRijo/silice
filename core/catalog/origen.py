"""SF‑E7: de dónde sale cada precio (RF‑56, spec §9.6) y las listas con alcance de proyecto.

`ListaPrecios` guarda nombre, moneda, vigencia y origen; este módulo agrega, en tablas aditivas, la
tasa de cambio con su fecha y el alcance de la lista (`ListaPreciosOrigen`), la referencia de cada
precio (`ReferenciaPrecio`, p. ej. el Ref de MaPreX) y las cotizaciones activas de una lista de
proyecto (`Cotizacion`). Una lista sin fila de origen es **global**: así abren las bases anteriores.

Una **lista de proyecto** (DA‑SF‑9) es la copia de una lista base con los insumos cotizados
cambiados; la referencia explícitamente la versión que se valora con ella, y
`Catalogo.lista_vigente` nunca la resuelve. Es inmutable como cualquier lista que un presupuesto
referencia: una cotización nueva o un cambio de la lista base crean otra lista de proyecto, no
editan esta.

No hace `commit`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models

__all__ = [
    "Cotizado",
    "OrigenEfectivo",
    "OrigenPrecio",
    "alcance_de",
    "cotizaciones_activas",
    "crear_lista_de_proyecto",
    "fijar_referencia",
    "lista_base",
    "origen_de_precios",
    "origenes_efectivos",
    "registrar_origen_lista",
]


@dataclass(frozen=True, slots=True)
class Cotizado:
    """Una cotización activa: el insumo, su precio cotizado, el de la lista base y su respaldo."""

    insumo_id: int
    precio: Decimal
    precio_base: Decimal | None
    proveedor: str
    numero: str
    fecha: date


@dataclass(frozen=True, slots=True)
class OrigenPrecio:
    """El origen del precio de un insumo en la lista de una versión (pestaña Precios, RF‑56).

    `referencia` es `""` si la lista no la guarda y `cotizacion` es `""` si el precio no es una
    cotización; `tasa` y `fecha_tasa` son `None` si la lista no las declara.
    """

    insumo_id: int
    codigo: str
    descripcion: str
    tipo: str
    precio: Decimal
    lista: str
    fecha_vigencia: date
    moneda: str
    tasa: Decimal | None
    fecha_tasa: date | None
    referencia: str
    alcance: str
    cotizacion: str
    moneda_original: str = ""
    precio_original: Decimal | None = None
    fecha_precio: date | None = None
    fuente_tasa: str = ""
    fuente: str = ""


@dataclass(frozen=True, slots=True)
class OrigenEfectivo:
    """El origen de un precio por la regla única de precedencia (S1 §5.1). Los nombres son los
    de las columnas de `PrecioOrigen`, sin `precio_id`."""

    moneda_original: str
    precio_original: Decimal
    fecha_precio: date
    tasa: Decimal | None
    fecha_tasa: date | None
    fuente_tasa: str
    fuente: str


def origenes_efectivos(session: Session, lista: models.ListaPrecios) -> dict[int, OrigenEfectivo]:
    """Por `precio_id`: la fila de `PrecioOrigen` y, si falta, la lista (moneda, vigencia, tasa de
    `ListaPreciosOrigen` sin fuente, `origen`). Así abren las bases anteriores."""
    de_lista = session.get(models.ListaPreciosOrigen, lista.id)
    filas = {
        f.precio_id: f
        for f in session.scalars(
            select(models.PrecioOrigen)
            .join(models.PrecioInsumo, models.PrecioInsumo.id == models.PrecioOrigen.precio_id)
            .where(models.PrecioInsumo.lista_id == lista.id)
        )
    }
    salida: dict[int, OrigenEfectivo] = {}
    for precio in lista.precios:
        f = filas.get(precio.id)
        salida[precio.id] = (
            OrigenEfectivo(
                f.moneda_original,
                f.precio_original,
                f.fecha_precio,
                f.tasa,
                f.fecha_tasa,
                f.fuente_tasa,
                f.fuente,
            )
            if f is not None
            else OrigenEfectivo(
                lista.moneda,
                precio.precio,
                lista.fecha_vigencia,
                de_lista.tasa if de_lista else None,
                de_lista.fecha_tasa if de_lista else None,
                "",
                lista.origen,
            )
        )
    return salida


def alcance_de(session: Session, lista: models.ListaPrecios) -> str:
    """`models.ALCANCE_PROYECTO` o `models.ALCANCE_GLOBAL` (la de toda lista sin origen)."""
    origen = session.get(models.ListaPreciosOrigen, lista.id)
    return origen.alcance if origen is not None else models.ALCANCE_GLOBAL


def lista_base(session: Session, lista: models.ListaPrecios) -> models.ListaPrecios:
    """La lista global de la que sale `lista`: ella misma o, si es de proyecto, su base."""
    origen = session.get(models.ListaPreciosOrigen, lista.id)
    if origen is None or origen.alcance != models.ALCANCE_PROYECTO or origen.lista_base_id is None:
        return lista
    return session.get(models.ListaPrecios, origen.lista_base_id) or lista


def registrar_origen_lista(
    session: Session,
    lista: models.ListaPrecios,
    *,
    tasa: Decimal | None = None,
    fecha_tasa: date | None = None,
) -> models.ListaPreciosOrigen:
    """Declara (o corrige) la tasa de cambio de la lista y la fecha de esa tasa. Hace `flush`."""
    origen = session.get(models.ListaPreciosOrigen, lista.id)
    if origen is None:
        origen = models.ListaPreciosOrigen(lista_id=lista.id, alcance=models.ALCANCE_GLOBAL)
        session.add(origen)
    origen.tasa, origen.fecha_tasa = tasa, fecha_tasa
    session.flush()
    return origen


def fijar_referencia(
    session: Session, lista: models.ListaPrecios, insumo: models.Insumo, referencia: str
) -> None:
    """Guarda la referencia del precio de `insumo` en `lista` (`ValueError` si la lista no lo
    valora o la referencia está vacía). Reemplaza la anterior. Hace `flush`."""
    referencia = referencia.strip()
    if not referencia:
        raise ValueError("la referencia del precio no puede estar vacia")
    precio_id = session.scalar(
        select(models.PrecioInsumo.id).where(
            models.PrecioInsumo.lista_id == lista.id, models.PrecioInsumo.insumo_id == insumo.id
        )
    )
    if precio_id is None:
        raise ValueError(f"la lista {lista.nombre!r} no valora el insumo {insumo.codigo}")
    fila = session.get(models.ReferenciaPrecio, precio_id)
    if fila is None:
        session.add(models.ReferenciaPrecio(precio_id=precio_id, referencia=referencia))
    else:
        fila.referencia = referencia
    session.flush()


def cotizaciones_activas(session: Session, lista: models.ListaPrecios) -> list[Cotizado]:
    """Las cotizaciones de una lista de proyecto, en el orden en que se registraron (vacío en una
    lista global)."""
    return [
        Cotizado(c.insumo_id, c.precio, c.precio_base, c.proveedor, c.numero, c.fecha)
        for c in session.scalars(
            select(models.Cotizacion)
            .where(models.Cotizacion.lista_id == lista.id)
            .order_by(models.Cotizacion.id)
        )
    ]


def crear_lista_de_proyecto(
    session: Session,
    proyecto: models.Proyecto,
    base: models.ListaPrecios,
    cotizaciones: Sequence[Cotizado],
    nombre: str,
) -> models.ListaPrecios:
    """La lista del proyecto: copia de `base` (precios, referencias, tasa) con los insumos de
    `cotizaciones` a su precio cotizado. Sin cotizaciones devuelve `base` (no hay nada que
    aislar). Hace `flush`."""
    if not cotizaciones:
        return base
    lista = models.ListaPrecios(
        nombre=nombre[:120],
        moneda=base.moneda,
        fecha_vigencia=base.fecha_vigencia,
        origen=f"cotizaciones del proyecto {proyecto.nombre}"[:200],
    )
    session.add(lista)
    session.flush()
    de_base = session.get(models.ListaPreciosOrigen, base.id)
    session.add(
        models.ListaPreciosOrigen(
            lista_id=lista.id,
            tasa=de_base.tasa if de_base else None,
            fecha_tasa=de_base.fecha_tasa if de_base else None,
            alcance=models.ALCANCE_PROYECTO,
            proyecto_id=proyecto.id,
            lista_base_id=base.id,
        )
    )
    cotizados = {c.insumo_id: c.precio for c in cotizaciones}
    referencias = {
        precio_id: referencia
        for precio_id, referencia in session.execute(
            select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
            .join(models.PrecioInsumo, models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id)
            .where(models.PrecioInsumo.lista_id == base.id)
        )
    }
    copias: list[tuple[models.PrecioInsumo, str | None]] = []
    for precio in base.precios:
        copias.append(
            (
                models.PrecioInsumo(
                    lista_id=lista.id,
                    insumo_id=precio.insumo_id,
                    precio=cotizados.get(precio.insumo_id, precio.precio),
                ),
                referencias.get(precio.id),
            )
        )
    en_base = {precio.insumo_id for precio in base.precios}
    copias += [
        (models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo_id, precio=precio), None)
        for insumo_id, precio in cotizados.items()
        if insumo_id not in en_base
    ]
    session.add_all(copia for copia, _ in copias)
    session.add_all(
        models.Cotizacion(
            lista_id=lista.id,
            insumo_id=c.insumo_id,
            precio=c.precio,
            precio_base=c.precio_base,
            proveedor=c.proveedor,
            numero=c.numero,
            fecha=c.fecha,
        )
        for c in cotizaciones
    )
    session.flush()
    session.add_all(
        models.ReferenciaPrecio(precio_id=copia.id, referencia=referencia)
        for copia, referencia in copias
        if referencia is not None
    )
    session.flush()
    efectivos = origenes_efectivos(session, base)
    ids_base = {precio.insumo_id: precio.id for precio in base.precios}
    session.add_all(
        models.PrecioOrigen(precio_id=copia.id, **asdict(efectivos[ids_base[copia.insumo_id]]))
        for copia, _ in copias
        if copia.insumo_id in ids_base and copia.insumo_id not in cotizados
    )
    session.flush()
    session.expire(lista, ["precios"])
    return lista


def origen_de_precios(session: Session, version: models.Presupuesto) -> list[OrigenPrecio]:
    """El origen del precio de cada insumo que usa la versión, en la lista que la valoró.

    Los insumos son los de las líneas de su instantánea de composiciones (SF‑E6) y, para las
    partidas que no la tienen, los de la composición del catálogo. Ordenados por código de insumo.
    """
    lista = version.lista_precios
    origen = session.get(models.ListaPreciosOrigen, lista.id)
    congeladas = set(
        session.scalars(
            select(models.ComposicionVersion.codigo_partida).where(
                models.ComposicionVersion.presupuesto_id == version.id
            )
        )
    )
    sin = [
        renglon.partida.id
        for renglon in version.partidas
        if renglon.partida.codigo not in congeladas
    ]
    ids = set(
        session.scalars(
            select(models.LineaComposicionVersion.insumo_id)
            .join(models.ComposicionVersion)
            .where(
                models.ComposicionVersion.presupuesto_id == version.id,
                models.LineaComposicionVersion.insumo_id.is_not(None),
            )
        )
    )
    if sin:
        ids |= set(
            session.scalars(
                select(models.ComposicionAPU.insumo_id).where(
                    models.ComposicionAPU.partida_id.in_(sin)
                )
            )
        )
    precios = {p.insumo_id: p for p in lista.precios}
    referencias = dict(
        session.execute(
            select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia).where(
                models.ReferenciaPrecio.precio_id.in_([p.id for p in precios.values()])
            )
        ).all()
    )
    cotizadas = {c.insumo_id: c for c in cotizaciones_activas(session, lista)}
    efectivos = origenes_efectivos(session, lista)
    filas: list[OrigenPrecio] = []
    for insumo in session.scalars(
        select(models.Insumo).where(models.Insumo.id.in_(ids)).order_by(models.Insumo.codigo)
    ):
        precio = precios.get(insumo.id)
        if precio is None:
            continue
        cotizacion = cotizadas.get(insumo.id)
        efectivo = efectivos[precio.id]
        filas.append(
            OrigenPrecio(
                insumo_id=insumo.id,
                codigo=insumo.codigo,
                descripcion=insumo.descripcion,
                tipo=insumo.tipo,
                precio=precio.precio,
                lista=lista.nombre,
                fecha_vigencia=lista.fecha_vigencia,
                moneda=lista.moneda,
                tasa=efectivo.tasa,
                fecha_tasa=efectivo.fecha_tasa,
                referencia=referencias.get(precio.id, ""),
                alcance=origen.alcance if origen else models.ALCANCE_GLOBAL,
                cotizacion=(
                    f"{cotizacion.proveedor}, {cotizacion.numero}, {cotizacion.fecha.isoformat()}"
                    if cotizacion
                    else ""
                ),
                moneda_original=efectivo.moneda_original,
                precio_original=efectivo.precio_original,
                fecha_precio=efectivo.fecha_precio,
                fuente_tasa=efectivo.fuente_tasa,
                fuente=efectivo.fuente,
            )
        )
    return filas
