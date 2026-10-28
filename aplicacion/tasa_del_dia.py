"""La tasa del BCV del mismo día de un precio (decisión de Eugenio del 2026-10-27, Tarea D2b).

Las conversiones de precios del plan de decisiones (el precio del corte, D2, y las observaciones
del estudio de mercado, D3) exigen la tasa **del mismo día** del precio: «exigen la tasa del día».
La búsqueda es la general, `tasa_aplicable` (la más reciente hasta esa fecha); si la que devuelve
no es de esa fecha, no sirve. Las conversiones de versiones y de listas no pasan por aquí: siguen
con la regla S1-R2 (hasta 7 días antes). Es el único sitio de esta regla.

Sin Streamlit ni FastAPI; solo lee.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from core.catalog.indices import TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import TasaDeclarada, convertir

__all__ = ["Equivalencia", "SinTasaDelDia", "equivalencia_del_dia", "tasa_del_dia"]


class SinTasaDelDia(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """No hay tasa del BCV de ese día; el mensaje es el que ve la persona."""


def tasa_del_dia(sesion: Session, fecha: date, moneda_destino: str) -> TasaDeclarada:
    """La tasa del BCV (Bs por USD) con fecha valor exactamente `fecha`. `SinTasaDelDia` si no hay
    tasa de ese día (sea porque no hay ninguna, sea porque la más reciente es de un día anterior);
    `moneda_destino` solo entra en el mensaje."""
    try:
        tasa = TasaDeclarada.de_importacion(tasa_aplicable(sesion, fecha))
    except TasaNoDisponible:
        tasa = None
    if tasa is None or tasa.fecha != fecha:
        raise SinTasaDelDia(
            f"No hay tasa del BCV del {fecha:%d/%m/%Y} (hace falta la del mismo día) para "
            f"convertir este precio a {moneda_destino}. Cárguela en Índices y vuelva a intentarlo."
        )
    return tasa


@dataclass(frozen=True, slots=True)
class Equivalencia:
    """La cuenta de un precio convertido, reconstruible por quien revise: el precio original (monto
    y moneda), la tasa (Bs por USD) con su fecha y su fuente, y el resultado en la moneda de destino
    (exacto: `core.catalog.moneda.convertir`, sin redondear)."""

    precio_original: Decimal
    moneda_original: str
    tasa: Decimal
    fecha_tasa: date
    fuente_tasa: str
    convertido: Decimal
    moneda: str

    @property
    def operacion(self) -> str:
        """«÷» si se dividió por la tasa (Bs a USD), «×» si se multiplicó (USD a Bs): lo que hace
        `convertir`, dicho en un solo sitio."""
        return "÷" if self.moneda_original == "Bs" else "×"

    @property
    def fuente_legible(self) -> str:
        """La fuente de la tasa como se lee: «BCV, publicación del dd/mm/aaaa» (`fuente_tasa` es la
        referencia interna del rastro)."""
        return f"BCV, publicación del {self.fecha_tasa:%d/%m/%Y}"


def equivalencia_del_dia(
    sesion: Session, precio: Decimal, de: str, a: str, fecha: date
) -> Equivalencia:
    """`precio` de la moneda `de` a `a` con la tasa del BCV de `fecha` (`SinTasaDelDia` si no hay
    tasa de ese día). Es la única aritmética de estas conversiones: la del núcleo."""
    tasa = tasa_del_dia(sesion, fecha, a)
    return Equivalencia(
        precio_original=precio,
        moneda_original=de,
        tasa=tasa.valor,
        fecha_tasa=tasa.fecha,
        fuente_tasa=tasa.fuente,
        convertido=convertir(precio, de, a, tasa.valor),
        moneda=a,
    )
