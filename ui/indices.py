"""UC‑17 1‑3 sin Streamlit: adaptador -> informe previo -> core.catalog.indices (S1 §4.3)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from adapters.bcv.csv_canonico import leer_csv_canonico
from adapters.bcv.formatos import cargar_formatos
from adapters.bcv.informe import InformeImportacion
from adapters.bcv.inpc import leer_inpc
from adapters.bcv.libro import abrir_libro
from adapters.bcv.tasa import leer_tasa
from core.catalog.indices import (
    UNIDAD_INDICE_BS,
    DefinicionSerie,
    Observacion,
    definicion_tasa,
    registrar_importacion,
)

TIPOS = ("tasa", "inpc", "csv")


def leer(ruta: Path, tipo: str, *, fuente: str, fecha_descarga: date) -> InformeImportacion:
    if tipo == "csv":
        return leer_csv_canonico(ruta, fecha_descarga=fecha_descarga)
    libro, formatos = abrir_libro(ruta), cargar_formatos()
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
