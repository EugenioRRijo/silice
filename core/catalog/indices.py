"""SL-E1: series de índices y tasa aplicable (spec S1 §5.3). Recibe definiciones y observaciones ya
validadas (las arma `ui.indices` con lo que entrega `adapters.bcv`); no conoce formatos de archivo.
Sin red (RNF-14). No hace `commit`."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models

PERIODICIDADES = ("diaria", "mensual", "trimestral", "anual")
SERIE_USD_COMPRA = "BCV-USD-COMPRA"
SERIE_USD_VENTA = "BCV-USD-VENTA"
SERIES_DE_TASA = {"compra": SERIE_USD_COMPRA, "venta": SERIE_USD_VENTA}
LADO_POR_DEFECTO = "venta"  # S1-R1, SUPUESTO_DECLARADO
DIAS_MAXIMOS_SIN_TASA = 7  # S1-R2
UNIDAD_TASA = "Bs/USD"
UNIDAD_INDICE_BS = "indice_bs"


class TasaNoDisponible(ValueError):  # noqa: N818
    """No hay tasa a esa fecha, o la más cercana tiene más de 7 días naturales."""


@dataclass(frozen=True, slots=True)
class DefinicionSerie:
    codigo: str
    nombre: str
    organismo: str
    unidad: str
    periodicidad: str
    base: str = ""

    def __post_init__(self) -> None:
        if not self.codigo.strip():
            raise ValueError("el codigo de la serie no puede estar vacio")
        if self.periodicidad not in PERIODICIDADES:
            raise ValueError(
                f"periodicidad {self.periodicidad!r}; se espera una de {PERIODICIDADES}"
            )


@dataclass(frozen=True, slots=True)
class Observacion:
    fecha: date
    valor: Decimal
    provisional: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.valor, Decimal) or not self.valor.is_finite() or self.valor <= 0:
            raise ValueError(f"el valor del {self.fecha} debe ser un Decimal mayor que cero")


@dataclass(frozen=True, slots=True)
class ValorFechado:
    serie: str
    fecha: date
    valor: Decimal
    provisional: bool
    importacion_id: int

    @property
    def fuente(self) -> str:
        return f"importacion:{self.importacion_id}"


def definicion_tasa(lado: str) -> DefinicionSerie:
    if lado not in SERIES_DE_TASA:
        raise ValueError(f"lado {lado!r}; se espera compra o venta")
    return DefinicionSerie(SERIES_DE_TASA[lado], f"Tasa de referencia USD ({lado})", "BCV",
                           UNIDAD_TASA, "diaria")


def _serie(session: Session, definicion: DefinicionSerie) -> models.SerieIndice:
    serie = session.scalars(
        select(models.SerieIndice).where(models.SerieIndice.codigo == definicion.codigo)
    ).one_or_none()
    if serie is None:
        serie = models.SerieIndice(codigo=definicion.codigo, nombre=definicion.nombre,
                                   organismo=definicion.organismo, unidad=definicion.unidad,
                                   periodicidad=definicion.periodicidad, base=definicion.base)
        session.add(serie)
        session.flush()
    elif (serie.unidad, serie.periodicidad) != (definicion.unidad, definicion.periodicidad):
        raise ValueError(f"la serie {definicion.codigo} ya existe con otra unidad o periodicidad")
    return serie


def registrar_importacion(
    session: Session,
    definicion: DefinicionSerie,
    observaciones: Sequence[Observacion],
    *,
    archivo: str,
    huella: str,
    fuente: str,
    fecha_descarga: date,
    responsable: str,
    filas_leidas: int,
    filas_rechazadas: int,
    informe: str = "",
    ahora: datetime | None = None,
) -> models.ImportacionIndice | None:
    """Guarda una importación nueva; `None` si la serie ya tiene esa huella (UC-17 2c). Una
    revisión de valores es otra importación (2d): nunca se sobrescribe un valor guardado."""
    fuente, responsable = fuente.strip(), responsable.strip()
    if not fuente:
        raise ValueError("la fuente de la importacion es obligatoria (UC-17 paso 1)")
    if not responsable:
        raise ValueError("el responsable de la importacion es obligatorio")
    if len(huella) != 64:
        raise ValueError("la huella debe ser un SHA-256 en hexadecimal (64 caracteres)")
    repetidas = sorted(f for f, n in Counter(o.fecha for o in observaciones).items() if n > 1)
    if repetidas:
        raise ValueError("fecha repetida en la importacion: " + ", ".join(map(str, repetidas)))
    serie = _serie(session, definicion)
    ya = session.scalar(select(models.ImportacionIndice.id).where(
        models.ImportacionIndice.serie_id == serie.id, models.ImportacionIndice.huella == huella))
    if ya is not None:
        return None
    importacion = models.ImportacionIndice(
        serie_id=serie.id, archivo=archivo, huella=huella, fuente=fuente,
        fecha_descarga=fecha_descarga, fecha_importacion=ahora or datetime.now(),
        responsable=responsable, filas_leidas=filas_leidas, filas_rechazadas=filas_rechazadas,
        informe=informe)
    session.add(importacion)
    session.flush()
    session.add_all(
        models.ValorIndice(serie_id=serie.id, importacion_id=importacion.id, fecha=o.fecha,
                           valor=o.valor, provisional=o.provisional)
        for o in observaciones
    )
    session.flush()
    return importacion


def _consulta(codigo: str):
    return (select(models.ValorIndice, models.SerieIndice.codigo)
            .join(models.SerieIndice)
            .where(models.SerieIndice.codigo == codigo))


def _fechado(fila: models.ValorIndice, codigo: str) -> ValorFechado:
    return ValorFechado(codigo, fila.fecha, fila.valor, fila.provisional, fila.importacion_id)


def valor_en(
    session: Session, codigo: str, fecha: date, *, importacion_id: int | None = None
) -> ValorFechado | None:
    """El valor exacto de esa fecha: el de la importación citada o, sin cita, el más reciente."""
    consulta = _consulta(codigo).where(models.ValorIndice.fecha == fecha)
    if importacion_id is not None:
        consulta = consulta.where(models.ValorIndice.importacion_id == importacion_id)
    fila = session.execute(
        consulta.order_by(models.ValorIndice.importacion_id.desc()).limit(1)).first()
    return None if fila is None else _fechado(fila[0], codigo)


def tasa_aplicable(session: Session, fecha: date, *, lado: str = LADO_POR_DEFECTO) -> ValorFechado:
    """La de mayor fecha valor ≤ `fecha` (S1-R1); más de 7 días naturales se rechaza (S1-R2)."""
    codigo = definicion_tasa(lado).codigo
    fila = session.execute(
        _consulta(codigo).where(models.ValorIndice.fecha <= fecha)
        .order_by(models.ValorIndice.fecha.desc(), models.ValorIndice.importacion_id.desc())
        .limit(1)).first()
    if fila is None:
        raise TasaNoDisponible(
            f"no hay tasa {lado} del BCV importada al {fecha:%d/%m/%Y} o antes: importe el "
            "archivo trimestral (UC-17)")
    dias = (fecha - fila[0].fecha).days
    if dias > DIAS_MAXIMOS_SIN_TASA:
        raise TasaNoDisponible(
            f"la tasa {lado} mas reciente es del {fila[0].fecha:%d/%m/%Y}, {dias} dias antes del "
            f"{fecha:%d/%m/%Y}: con mas de 7 dias naturales sin tasa no se convierte (S1-R2)")
    return _fechado(fila[0], codigo)
