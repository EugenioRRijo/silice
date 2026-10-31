"""La tasa del BCV del mismo día de un precio (decisión de Eugenio del 2026-10-27, Tarea D2b).

Las conversiones de precios del plan de decisiones (el precio del corte, D2, y las observaciones
del estudio de mercado, D3) exigen la tasa **del mismo día** del precio: «exigen la tasa del día».
La búsqueda es la general, `tasa_aplicable` (la más reciente hasta esa fecha); si la que devuelve
no es de esa fecha, no sirve. Las conversiones de versiones y de listas no pasan por aquí: siguen
con la regla S1-R2 (hasta 7 días antes). Es el único sitio de esta regla.

**Tasa del cierre del mes** (respuesta de Eugenio a la pregunta 14, plan vial, Tarea 4b): para
llevar a la moneda del costo de producción de un mes el precio de una lista o lo que pasa de un mes
al siguiente, la tasa es la **última del BCV con fecha valor dentro de ese mes** (la más reciente
hasta su último día, y solo si es de ese mes). Vive aquí también, para que la regla de las tasas
siga en un solo sitio.

Sin Streamlit ni FastAPI; solo lee.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from core.catalog.indices import TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import TasaDeclarada, convertir

__all__ = [
    "Equivalencia",
    "SinTasaDelDia",
    "equivalencia_del_cierre",
    "equivalencia_del_dia",
    "tasa_del_cierre",
    "tasa_del_dia",
]

_PERIODO = re.compile(r"(\d{4})-(\d{2})")


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


def _cierre(periodo: str) -> date:
    """El último día del mes `periodo` («AAAA-MM»); `ValueError` si no tiene esa forma."""
    forma = _PERIODO.fullmatch(periodo)
    if forma is None or not 1 <= int(forma.group(2)) <= 12:
        raise ValueError(f"El período debe tener la forma AAAA-MM (p. ej. 2026-11): {periodo!r}.")
    anio, mes = int(forma.group(1)), int(forma.group(2))
    return date(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)


def tasa_del_cierre(sesion: Session, periodo: str, moneda_destino: str) -> TasaDeclarada:
    """La tasa del BCV (Bs por USD) del cierre del mes `periodo`: la de fecha valor más reciente
    hasta su último día, solo si cae dentro del mes. `SinTasaDelDia` si no hay ninguna publicada
    en el mes; `moneda_destino` solo entra en el mensaje."""
    cierre = _cierre(periodo)
    try:
        tasa = TasaDeclarada.de_importacion(tasa_aplicable(sesion, cierre))
    except TasaNoDisponible:
        tasa = None
    if tasa is None or (tasa.fecha.year, tasa.fecha.month) != (cierre.year, cierre.month):
        raise SinTasaDelDia(
            f"No hay tasa del BCV publicada en {periodo} para convertir a {moneda_destino}. "
            "Cárguela en Índices y vuelva a intentarlo."
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
    return _equivalencia(precio, de, a, tasa_del_dia(sesion, fecha, a))


def _equivalencia(precio: Decimal, de: str, a: str, tasa: TasaDeclarada) -> Equivalencia:
    return Equivalencia(
        precio_original=precio,
        moneda_original=de,
        tasa=tasa.valor,
        fecha_tasa=tasa.fecha,
        fuente_tasa=tasa.fuente,
        convertido=convertir(precio, de, a, tasa.valor),
        moneda=a,
    )


def equivalencia_del_cierre(
    sesion: Session, precio: Decimal, de: str, a: str, periodo: str
) -> Equivalencia:
    """`precio` de la moneda `de` a `a` con la tasa del cierre del mes `periodo`
    (`tasa_del_cierre`; `SinTasaDelDia` si no hay ninguna publicada en el mes)."""
    return _equivalencia(precio, de, a, tasa_del_cierre(sesion, periodo, a))
