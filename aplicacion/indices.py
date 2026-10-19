"""UC‑17 1‑3 sin Streamlit: adaptador -> informe previo -> core.catalog.indices (S1 §4.3).

Lo comparten la pantalla clásica (`ui.indices` lo reexporta) y la API (`api/rutas/indices.py`),
RM-1. Un `.xls` pide `xlrd` (extra `bcv`); si falta, `leer` lo dice en lenguaje llano en vez de
dejar escapar un `ModuleNotFoundError`."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from pathlib import Path

from adapters.bcv.csv_canonico import leer_csv_canonico
from adapters.bcv.formatos import cargar_formatos
from adapters.bcv.informe import InformeImportacion
from adapters.bcv.inpc import leer_inpc
from adapters.bcv.libro import abrir_libro
from adapters.bcv.tasa import leer_tasa
from core.catalog.indices import (
    PERIODICIDADES,
    UNIDAD_INDICE_BS,
    DefinicionSerie,
    Observacion,
    definicion_tasa,
    registrar_importacion,
)

TIPOS = ("tasa", "inpc", "csv")
ROTULOS_TIPO = {
    "tasa": "Tasa de referencia del USD (.xls trimestral)",
    "inpc": "INPC (.xls mensual)",
    "csv": "Una serie en CSV canonico (serie, fecha, valor, provisional, fuente)",
}
MENSAJE_SIN_XLRD = (
    "No se puede leer un archivo .xls: falta el componente xlrd (extra «bcv» de la instalación). "
    "Instálelo, o use el .xlsx o el CSV canónico."
)


def _abrir(ruta: Path):
    try:
        return abrir_libro(ruta)
    except ImportError as error:  # solo `xlrd` se importa dentro de `abrir_libro` para un .xls
        if getattr(error, "name", None) == "xlrd":
            raise ValueError(MENSAJE_SIN_XLRD) from None
        raise


def leer(ruta: Path, tipo: str, *, fuente: str, fecha_descarga: date) -> InformeImportacion:
    if tipo == "csv":
        return leer_csv_canonico(ruta, fecha_descarga=fecha_descarga)
    libro, formatos = _abrir(ruta), cargar_formatos()
    if tipo == "tasa":
        return leer_tasa(
            libro,
            fuente=fuente,
            fecha_descarga=fecha_descarga,
            trimestre_por_letra=formatos.trimestre_por_letra,
        )
    if tipo == "inpc":
        return leer_inpc(libro, fuente=fuente, fecha_descarga=fecha_descarga, formato=formatos.inpc)
    raise ValueError(f"tipo {tipo!r}; se espera uno de {TIPOS}")


def _definicion(serie, definiciones_csv) -> DefinicionSerie:
    if serie.clave == "usd_compra":
        return definicion_tasa("compra")
    if serie.clave == "usd_venta":
        return definicion_tasa("venta")
    if serie.clave == "inpc_general":
        return DefinicionSerie(
            "BCV-INPC-GENERAL",
            serie.nombre,
            serie.organismo,
            UNIDAD_INDICE_BS,
            "mensual",
            serie.base,
        )
    if serie.clave not in (definiciones_csv or {}):
        raise ValueError(
            f"declare nombre, organismo, unidad y periodicidad de la serie {serie.clave}"
        )
    return definiciones_csv[serie.clave]


def filas_del_informe(informe: InformeImportacion) -> list[dict[str, str]]:
    return [{"Lugar": r.lugar, "Motivo": r.motivo} for r in informe.rechazos]


def resumen_de_series(informe: InformeImportacion) -> list[dict[str, str | int]]:
    """Una fila por serie leída: cuántos valores trae y de qué fecha a qué fecha (ISO o vacío)."""
    filas: list[dict[str, str | int]] = []
    for serie in informe.series:
        fechas = [valor.fecha for valor in serie.valores]
        filas.append(
            {
                "serie": serie.clave,
                "valores": len(serie.valores),
                "desde": min(fechas).isoformat() if fechas else "",
                "hasta": max(fechas).isoformat() if fechas else "",
            }
        )
    return filas


def definiciones_desde_filas(
    filas: Iterable[Mapping[str, str]],
) -> dict[str, DefinicionSerie]:
    """Lo que declara quien importa un CSV por cada serie (nombre, organismo, unidad y
    periodicidad). Una serie con nombre, organismo o unidad en blanco no se define: `confirmar`
    pide entonces que se declare. Una periodicidad ajena es el `ValueError` del núcleo."""
    definiciones: dict[str, DefinicionSerie] = {}
    for fila in filas:
        nombre, organismo, unidad = (fila[c].strip() for c in ("nombre", "organismo", "unidad"))
        if nombre and organismo and unidad:
            clave = fila["serie"]
            definiciones[clave] = DefinicionSerie(
                clave, nombre, organismo, unidad, fila["periodicidad"]
            )
    return definiciones


def confirmar(sesion, informe, *, responsable, definiciones_csv=None, ahora=None) -> list[str]:
    """UC‑17 3: guarda cada serie (una importación por serie, misma huella) y confirma."""
    mensajes = []
    try:
        for serie in informe.series:
            hecho = registrar_importacion(
                sesion,
                _definicion(serie, definiciones_csv),
                [Observacion(v.fecha, v.valor, v.provisional) for v in serie.valores],
                archivo=informe.archivo,
                huella=informe.huella,
                fuente=informe.fuente,
                fecha_descarga=informe.fecha_descarga,
                responsable=responsable,
                filas_leidas=informe.filas_leidas,
                filas_rechazadas=informe.filas_rechazadas,
                informe=informe.texto(),
                ahora=ahora or datetime.now(),
            )
            mensajes.append(
                f"{serie.clave}: "
                + (
                    "ya importado; no se escribio nada"
                    if hecho is None
                    else f"importada ({len(serie.valores)} valores)"
                )
            )
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    return mensajes


__all__ = [
    "MENSAJE_SIN_XLRD",
    "PERIODICIDADES",
    "ROTULOS_TIPO",
    "TIPOS",
    "UNIDAD_INDICE_BS",
    "confirmar",
    "definiciones_desde_filas",
    "filas_del_informe",
    "leer",
    "resumen_de_series",
]
