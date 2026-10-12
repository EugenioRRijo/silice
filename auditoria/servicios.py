"""Los `Servicios` de la reauditoría armados con la base de quien revisa (S1 y S2; spec S3 §3.4).

La reauditoría contrasta los precios de un documento ajeno con **la referencia MaPreX de esta
instalación** (`lista_de_referencia`, S1 §6.2) y los lleva a una moneda con **las tasas del BCV
que esta instalación importó** (`tasa_aplicable`, S1). Un día sin tasa no revienta: la tasa es
`None` y R11/R12 lo dicen («no contrastable», impacto sin cuantificar). La erosión es la de S1
§5.3 (la misma de `core.catalog.empresa._erosion_en_lista`, que es privada): 0 si el original es
USD, `None` sin tasa, y por unidad en la moneda de la lista.

R13-R14 desde un `anexos/control.json` dependen de un servicio de S2 que reconstruya su
instantánea desde el anexo: no existe todavía (`core.budget.valuaciones.anexo_control` solo lo
escribe), así que `reglas_de_control` es `None` y la reauditoría lo declara (RP8-21).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from auditoria.reauditoria import ReferenciaDeMercado, Servicios
from core import models
from core.budget import canonico
from core.catalog.empresa import lista_de_referencia
from core.catalog.indices import LADO_POR_DEFECTO, TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import erosion
from core.catalog.origen import origenes_efectivos
from core.contracts.verificacion import ReglaVerificacion

__all__ = ["servicios_de_la_instalacion"]

ReglasDeControl = Callable[
    [canonico.DocumentoLeido, Mapping[str, Any], date], Sequence[ReglaVerificacion]
]


def _erosion(
    precio: Decimal,
    moneda_lista: str,
    moneda_original: str,
    precio_original: Decimal,
    t0: Decimal | None,
    t1: Decimal | None,
) -> Decimal | None:
    if moneda_original == "USD":
        return Decimal(0)
    if t0 is None or t1 is None:
        return None
    if moneda_lista == "Bs":
        return erosion(precio, "Bs", t0, t1).bs
    return erosion(precio_original, "Bs", t0, t1).usd


def servicios_de_la_instalacion(
    session: Session,
    *,
    lado: str = LADO_POR_DEFECTO,
    reglas_de_control: ReglasDeControl | None = None,
) -> Servicios:
    """La referencia, las tasas y la erosión de esta instalación. `reglas_de_control` es el
    servicio de S2 para R13-R14 desde un anexo (`None` mientras S2 no lo entregue)."""
    referencia = lista_de_referencia(session)
    por_ref: dict[str, models.PrecioInsumo] = {}
    origenes = {}
    if referencia is not None:
        refs = dict(
            session.execute(
                select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
                .join(
                    models.PrecioInsumo,
                    models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id,
                )
                .where(models.PrecioInsumo.lista_id == referencia.id)
            ).all()
        )
        veces = Counter(refs.values())
        por_id = {p.id: p for p in referencia.precios}
        # una Ref repetida en la referencia no contrasta (S1 §6.3): solo las únicas
        por_ref = {ref: por_id[pid] for pid, ref in refs.items() if veces[ref] == 1}
        origenes = origenes_efectivos(session, referencia)

    def referencia_de(codigo: str) -> ReferenciaDeMercado | None:
        precio = por_ref.get(codigo)
        if precio is None or referencia is None:
            return None
        return ReferenciaDeMercado(
            codigo, precio.precio, referencia.moneda, origenes[precio.id].tasa
        )

    def tasa_en(fecha: date) -> Decimal | None:
        try:
            return tasa_aplicable(session, fecha, lado=lado).valor
        except TasaNoDisponible:
            return None

    return Servicios(
        referencia_de=referencia_de,
        tasa_en=tasa_en,
        erosion=_erosion,
        reglas_de_control=reglas_de_control,
    )
