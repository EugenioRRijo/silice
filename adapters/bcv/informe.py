"""Tipos propios del adaptador del BCV (biblioteca estándar) y validación de la fuente."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit

DOMINIO_BCV = "bcv.org.ve"


class FormatoNoReconocido(ValueError):  # noqa: N818 (nombre fijado por el plan y las pruebas)
    """El archivo no es lo que el formato documentado dice (UC‑17 2a); no se escribe nada."""


@dataclass(frozen=True, slots=True)
class ValorLeido:
    fecha: date
    valor: Decimal
    provisional: bool = False
    lugar: str = ""


@dataclass(frozen=True, slots=True)
class SerieLeida:
    clave: str
    nombre: str
    organismo: str
    unidad: str
    periodicidad: str
    base: str
    valores: tuple[ValorLeido, ...]


@dataclass(frozen=True, slots=True)
class Rechazo:
    lugar: str
    motivo: str


@dataclass(frozen=True, slots=True)
class InformeImportacion:
    archivo: str
    huella: str
    fuente: str
    fecha_descarga: date
    series: tuple[SerieLeida, ...]
    rechazos: tuple[Rechazo, ...] = ()
    advertencias: tuple[str, ...] = ()
    filas_leidas: int = 0

    @property
    def filas_rechazadas(self) -> int:
        return len(self.rechazos)

    @property
    def provisionales(self) -> int:
        return sum(v.provisional for s in self.series for v in s.valores)

    def texto(self) -> str:
        lineas = [f"{s.clave}: {len(s.valores)} valores" for s in self.series]
        lineas += [f"rechazo {r.lugar}: {r.motivo}" for r in self.rechazos]
        return "\n".join([*lineas, *self.advertencias])


def validar_fuente(fuente: str) -> str:
    partes = urlsplit(fuente.strip())
    host = (partes.hostname or "").lower()
    if partes.scheme not in ("http", "https") or not (
        host == DOMINIO_BCV or host.endswith("." + DOMINIO_BCV)
    ):
        raise FormatoNoReconocido(f"la fuente {fuente!r} no es una direccion de {DOMINIO_BCV}")
    return fuente.strip()
