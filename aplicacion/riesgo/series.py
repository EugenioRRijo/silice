"""Series de precios del riesgo vial y su mapa a insumos (plan vial, Tarea 12).

Las series se guardan con `core.catalog.indices` (la misma tabla que la tasa BCV); aquí solo se
declaran las dos propias del riesgo vial, se importan desde el CSV canónico y se lee su historia
por mes. Sin red. No hace `commit`: quien llama decide cuándo confirmar (como
`core.catalog.indices`)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.bcv.csv_canonico import leer_csv_canonico
from aplicacion.indices import texto_del_informe
from core import models
from core.catalog.indices import (
    DefinicionSerie,
    Observacion,
    registrar_importacion,
)

UNIDAD_INDICE = "indice"

# PPI de asfalto de EE. UU. (FRED/BLS, `WPU05810212`): un ÍNDICE, no un precio. No existe serie
# pública venezolana; se usa solo por su variación mensual (fuentes del plan vial, §5).
CEMENTO_ASFALTICO_PPI = DefinicionSerie(
    "CEMENTO_ASFALTICO_PPI",
    "PPI de asfalto de EE. UU. WPU05810212 (proxy internacional del cemento asfáltico)",
    "FRED/BLS",
    UNIDAD_INDICE,
    "mensual",
)

# Gasoil en USD por litro: precio administrado por decreto, una serie en escalones (a cotejar en
# la Gaceta).
GASOIL_USD = DefinicionSerie(
    "GASOIL_USD",
    "Gasoil, precio administrado (escalones; a cotejar en la Gaceta)",
    "Gaceta Oficial",
    "USD/l",
    "mensual",
)

SERIES_VIALES: tuple[DefinicionSerie, ...] = (CEMENTO_ASFALTICO_PPI, GASOIL_USD)


@dataclass(frozen=True)
class MapaSeries:
    """Qué serie mueve el precio de cada insumo. La clave es la **descripción** del insumo, porque
    así indexa `generar_escenario` sus `precios`. Un insumo en Bs sin serie sigue a la tasa (lo
    decide la proyección)."""

    serie_por_insumo: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "serie_por_insumo", MappingProxyType(dict(self.serie_por_insumo)))


def importar_serie_csv(
    sesion: Session, codigo: str, ruta: Path, *, fuente: str, responsable: str, hoy: date
) -> int | None:
    """Importa del CSV canónico la serie `codigo` (una de `SERIES_VIALES`). Devuelve el id de la
    importación o `None` si el archivo ya estaba importado (misma huella). Una fila rechazada
    detiene todo: no se importa a medias. `hoy` es la fecha de descarga (no se aceptan fechas
    posteriores)."""
    definiciones = {s.codigo: s for s in SERIES_VIALES}
    if codigo not in definiciones:
        raise ValueError(f"serie {codigo!r}; se espera una de {', '.join(definiciones)}")
    informe = leer_csv_canonico(ruta, fecha_descarga=hoy)
    if informe.rechazos:
        detalle = "; ".join(f"{r.lugar}: {r.motivo}" for r in informe.rechazos)
        raise ValueError(f"filas rechazadas, no se importó nada: {detalle}")
    leida = next((s for s in informe.series if s.clave == codigo), None)
    if leida is None:
        raise ValueError(f"el archivo {ruta.name} no trae la serie {codigo}")
    importacion = registrar_importacion(
        sesion,
        definiciones[codigo],
        [Observacion(v.fecha, v.valor, v.provisional) for v in leida.valores],
        archivo=informe.archivo,
        huella=informe.huella,
        fuente=fuente,
        fecha_descarga=informe.fecha_descarga,
        responsable=responsable,
        filas_leidas=informe.filas_leidas,
        filas_rechazadas=informe.filas_rechazadas,
        informe=texto_del_informe(informe),
        ahora=datetime.now(),
    )
    return None if importacion is None else importacion.id


def historia_mensual(
    sesion: Session, codigos: Sequence[str], desde: date, hasta: date
) -> dict[str, dict[date, Decimal]]:
    """Por serie, `{primer día del mes: valor}` de las observaciones con `desde <= fecha <= hasta`.
    Una fecha con dos importaciones toma la más reciente (nada se sobrescribe, pero la revisión
    manda); un mes con varias fechas (serie diaria, como la tasa) aporta la de mayor fecha. Una
    serie sin datos da `{}`."""
    historia: dict[str, dict[date, Decimal]] = {}
    for codigo in codigos:
        filas = sesion.execute(
            select(models.ValorIndice.fecha, models.ValorIndice.valor)
            .join(models.SerieIndice, models.SerieIndice.id == models.ValorIndice.serie_id)
            .where(
                models.SerieIndice.codigo == codigo,
                models.ValorIndice.fecha >= desde,
                models.ValorIndice.fecha <= hasta,
            )
            .order_by(models.ValorIndice.fecha, models.ValorIndice.importacion_id)
        ).all()
        por_fecha = {
            fecha: valor for fecha, valor in filas
        }  # la última importación pisa a la anterior
        historia[codigo] = {
            fecha.replace(day=1): valor for fecha, valor in sorted(por_fecha.items())
        }
    return historia
