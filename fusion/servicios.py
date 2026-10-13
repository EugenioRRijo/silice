"""Los servicios de la instalación que consultan las alertas de la 1.5 (spec 1.5 §4, F-D8).

`servicios_desde_sesion` arma el `ContextoPrecios` desde una sesión de la base: las tasas del BCV
que la instalación importó y los precios de su lista de empresa más reciente. Es lo único de
`fusion` que abre la base; leer, recalcular, auditar y devolver un libro no la necesitan
(`fusion.proceso` recibe el contexto ya armado).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.origen import origenes_efectivos
from fusion.alertas import UMBRAL_POR_DEFECTO, ContextoPrecios

__all__ = ["servicios_desde_sesion"]


def _precios_de_empresa(session: Session) -> dict[str, tuple[Decimal, date, str]]:
    """Código -> (precio, fecha, moneda) de la lista de empresa más reciente de la instalación.

    El código de la empresa (MT-01, MO-03…) se busca primero como Ref del precio
    (`ReferenciaPrecio`, solo las Ref únicas en la lista, como hace la reauditoría con MaPreX) y
    luego como código del insumo del catálogo. La fecha es la del origen efectivo del precio
    (`PrecioOrigen` o, si falta, la vigencia de la lista).
    """
    lista = session.scalars(
        select(models.ListaPrecios)
        .join(models.ListaEmpresa, models.ListaEmpresa.lista_id == models.ListaPrecios.id)
        .order_by(models.ListaPrecios.id.desc())
        .limit(1)
    ).one_or_none()
    if lista is None:
        return {}
    origenes = origenes_efectivos(session, lista)
    refs = dict(
        session.execute(
            select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
            .join(models.PrecioInsumo, models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id)
            .where(models.PrecioInsumo.lista_id == lista.id)
        ).all()
    )
    veces: dict[str, int] = {}
    for ref in refs.values():
        veces[ref] = veces.get(ref, 0) + 1
    salida: dict[str, tuple[Decimal, date, str]] = {}
    for precio in lista.precios:
        dato = (precio.precio, origenes[precio.id].fecha_precio, lista.moneda)
        salida.setdefault(precio.insumo.codigo, dato)
    for precio in lista.precios:
        ref = refs.get(precio.id)
        if ref and veces[ref] == 1:
            salida[ref] = (precio.precio, origenes[precio.id].fecha_precio, lista.moneda)
    return salida


def servicios_desde_sesion(
    session: Session, umbral: Decimal = UMBRAL_POR_DEFECTO
) -> ContextoPrecios:
    """El `ContextoPrecios` de esta instalación: las tasas del BCV que importó (las mismas de la
    reauditoría, `auditoria.servicios.servicios_de_la_instalacion`), los precios de su lista de
    empresa más reciente y el `umbral` de variación de las alertas (fracción: 0,05 = 5 %, el valor
    por omisión del spec §4).

    Los precios se leen una vez, al armar el contexto: la sesión puede cerrarse después de
    consultar las alertas, pero no antes (las tasas se consultan con ella).

    Límite: la lista de empresa es una copia de su lista base con los propios encima (S1 §6.1);
    aquí cuentan todos sus precios, heredados o propios, porque todos son "el precio de la empresa"
    en la instalación. Un código de la empresa que no es Ref ni código del catálogo no contrasta.
    """
    if umbral < 0:
        raise ValueError(f"el umbral de las alertas es una fracción no negativa: {umbral}")
    # Importación diferida a propósito: `auditoria` importa la reauditoría, que arrastra
    # `adapters.espacio` y con él el extra `planos` (shapely, ezdxf). Leer, recalcular y devolver
    # un libro no lo necesita; solo armar el contexto desde la base de la instalación.
    from auditoria.servicios import servicios_de_la_instalacion

    servicios = servicios_de_la_instalacion(session)
    precios = _precios_de_empresa(session)
    return ContextoPrecios(
        tasa_en=servicios.tasa_en,
        precio_propio=precios.get if precios else None,
        umbral=umbral,
    )
