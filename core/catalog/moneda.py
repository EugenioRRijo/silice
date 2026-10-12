"""SL-E1: monedas, conversión con tasa fechada y erosión (spec S1 §5.3).

Toda división con 28 dígitos y ROUND_HALF_EVEN fijados dentro de la función. No hace `commit`.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.indices import ValorFechado
from core.catalog.origen import origenes_efectivos

MONEDAS = ("Bs", "USD")  # S1-R15
_CERO = Decimal(0)


def _contexto():
    return localcontext(prec=28, rounding=ROUND_HALF_EVEN)


def exigir_moneda(moneda: str) -> str:
    if moneda not in MONEDAS:
        raise ValueError(f"moneda {moneda!r}; se espera Bs o USD (UC-17 4b)")
    return moneda


@dataclass(frozen=True, slots=True)
class TasaDeclarada:
    """Tasa Bs por USD con su fecha y su fuente (importación o texto). Las tres obligatorias."""

    valor: Decimal
    fecha: date
    fuente: str

    def __post_init__(self) -> None:
        if not isinstance(self.valor, Decimal) or not self.valor.is_finite() or self.valor <= 0:
            raise ValueError("la tasa debe ser un Decimal mayor que cero")
        if not isinstance(self.fecha, date):
            raise ValueError("la tasa debe declarar su fecha")
        if not self.fuente.strip():
            raise ValueError("la tasa debe declarar su fuente")

    @classmethod
    def de_importacion(cls, valor: ValorFechado) -> TasaDeclarada:
        return cls(valor.valor, valor.fecha, valor.fuente)


def convertir(monto: Decimal, de: str, a: str, tasa: Decimal) -> Decimal:
    exigir_moneda(de), exigir_moneda(a)
    with _contexto():
        if de == a:
            return monto
        return monto / tasa if de == "Bs" else monto * tasa


@dataclass(frozen=True, slots=True)
class Erosion:
    usd: Decimal
    bs: Decimal
    porcentaje: Decimal
    nota: str = ""


def erosion(
    precio: Decimal, moneda: str, tasa_precio: Decimal, tasa_evaluacion: Decimal
) -> Erosion:
    if exigir_moneda(moneda) == "USD":
        return Erosion(_CERO, _CERO, _CERO,
                       "precio en USD: no hay indice de inflacion en USD en el alcance (declarado)")
    with _contexto():
        return Erosion(precio / tasa_precio - precio / tasa_evaluacion,
                       precio * tasa_evaluacion / tasa_precio - precio,
                       1 - tasa_precio / tasa_evaluacion)


def erosion_por_indice(
    precio: Decimal, indice_precio: Decimal, indice_evaluacion: Decimal
) -> Decimal:
    with _contexto():
        return precio * (indice_evaluacion / indice_precio - 1)


def copiar_precios(
    session: Session,
    de: models.ListaPrecios,
    a_lista: models.ListaPrecios,
    tasa: TasaDeclarada | None,
    *,
    excluir: Collection[int] = frozenset(),
) -> None:
    """Copia a `a_lista` cada precio de `de` (salvo los insumos de `excluir`), convertido con `tasa`
    si las monedas difieren, con su referencia y su origen efectivo (moneda y precio originales se
    conservan; la tasa pasa a ser la de esta conversión). Hace `flush`."""
    if de.moneda != a_lista.moneda and tasa is None:
        raise ValueError(f"la lista {de.nombre!r} esta en {de.moneda}: hace falta una tasa")
    origenes = origenes_efectivos(session, de)
    referencias = dict(session.execute(
        select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
        .join(models.PrecioInsumo, models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id)
        .where(models.PrecioInsumo.lista_id == de.id)).all())
    pares = []
    for precio in de.precios:
        if precio.insumo_id in excluir:
            continue
        valor = precio.precio if tasa is None else convertir(precio.precio, de.moneda,
                                                              a_lista.moneda, tasa.valor)
        copia = models.PrecioInsumo(lista_id=a_lista.id, insumo_id=precio.insumo_id, precio=valor)
        pares.append((precio, copia))
    session.add_all(c for _, c in pares)
    session.flush()
    for original, copia in pares:
        o = origenes[original.id]
        convertida = tasa is not None and de.moneda != a_lista.moneda
        session.add(models.PrecioOrigen(
            precio_id=copia.id, moneda_original=o.moneda_original,
            precio_original=o.precio_original, fecha_precio=o.fecha_precio,
            tasa=tasa.valor if convertida else o.tasa,
            fecha_tasa=tasa.fecha if convertida else o.fecha_tasa,
            fuente_tasa=tasa.fuente if convertida else o.fuente_tasa, fuente=o.fuente))
        if original.id in referencias:
            session.add(models.ReferenciaPrecio(precio_id=copia.id,
                                                referencia=referencias[original.id]))
    session.flush()


def convertir_lista(
    session: Session,
    lista: models.ListaPrecios,
    a: str,
    tasa: TasaDeclarada,
    *,
    nombre: str,
    proyecto: models.Proyecto | None = None,
) -> models.ListaPrecios:
    """Lista derivada de alcance `proyecto` (SF-E7) con cada precio convertido.

    `lista_base_id` queda vacío a propósito: UC-02 compara listas de la misma moneda (`lista_base`
    devuelve esta)."""
    nueva = models.ListaPrecios(
        nombre=nombre[:120], moneda=exigir_moneda(a), fecha_vigencia=lista.fecha_vigencia,
        origen=f"{lista.nombre} en {a} con {tasa.valor} Bs/USD del {tasa.fecha:%d/%m/%Y}"[:200])
    session.add(nueva)
    session.flush()
    session.add(models.ListaPreciosOrigen(
        lista_id=nueva.id, tasa=tasa.valor, fecha_tasa=tasa.fecha,
        alcance=models.ALCANCE_PROYECTO, proyecto_id=proyecto.id if proyecto else None))
    copiar_precios(session, lista, nueva, tasa)
    session.expire(nueva, ["precios"])
    return nueva
