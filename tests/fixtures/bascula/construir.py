"""Generadores deterministas de reportes de báscula (EJEMPLO CONSTRUIDO).

Nada de lo que sale de aquí es real: placas, clientes y pesos son inventados para probar el lector.
Lo que debe salir de cada archivo está escrito a mano en `ORACULO.md`, que se redactó antes que este
módulo. Sin reloj ni azar: dos llamadas devuelven los mismos bytes (se fijan los metadatos de fecha
del xlsx y del ZIP).

`openpyxl` solo se usa para ESCRIBIR el xlsx; `csv` y `zipfile` hacen el resto.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Sequence
from datetime import datetime

from openpyxl import Workbook

__all__ = [
    "ENCABEZADOS_BASICOS",
    "ENCABEZADOS_SIN_UNIDAD",
    "FILAS_BASICAS",
    "FILAS_COMA_DECIMAL",
    "csv_basico",
    "csv_coma_decimal",
    "csv_desmedido",
    "xlsx_basico",
    "xlsx_con_macros_renombrado",
    "xlsx_sin_unidad",
]

ENCABEZADOS_BASICOS: tuple[str, ...] = (
    "Ticket",
    "Fecha",
    "Placa",
    "Cliente",
    "Material",
    "Bruto (kg)",
    "Tara (kg)",
    "Neto (kg)",
)
ENCABEZADOS_SIN_UNIDAD: tuple[str, ...] = (
    "Ticket",
    "Fecha",
    "Placa",
    "Cliente",
    "Material",
    "Bruto",
    "Tara",
    "Neto",
)

# (ticket, fecha ISO, placa, cliente, material, bruto kg, tara kg, neto kg). Ver ORACULO.md §1.
FILAS_BASICAS: tuple[tuple[str, str, str, str, str, int, int, int], ...] = (
    ("TCK-001", "2026-10-15", "EJ-001", "Cliente Ejemplo A", "ARENA", 42500, 14200, 28300),
    ("TCK-002", "2026-10-15", "EJ-002", "Cliente Ejemplo B", "PIEDRA34", 38000, 13500, 24500),
    ("TCK-003", "2026-10-16", "EJ-003", "Cliente Ejemplo A", "ARENA", 42000, 45000, -3000),
    ("TCK-004", "2026-10-16", "EJ-004", "Cliente Ejemplo C", "ARENA", 40000, 15000, 20000),
    ("TCK-005", "2026-12-31", "EJ-005", "Cliente Ejemplo B", "PIEDRA34", 40000, 15000, 25000),
    ("TCK-006", "2026-10-17", "EJ-006", "Cliente Ejemplo C", "GRAVA9", 40000, 15000, 25000),
)

# Pesos como TEXTO: la ambigüedad de separadores solo existe en texto. Ver ORACULO.md §3.
FILAS_COMA_DECIMAL: tuple[tuple[str, str, str, str, str, str, str, str], ...] = (
    (
        "TCK-101",
        "2026-10-15",
        "EJ-101",
        "Cliente Ejemplo A",
        "ARENA",
        "1.234,56",
        "234,56",
        "1.000,00",
    ),
    (
        "TCK-102",
        "2026-10-15",
        "EJ-102",
        "Cliente Ejemplo A",
        "ARENA",
        "1,234.56",
        "234.56",
        "1,000.00",
    ),
    ("TCK-103", "2026-10-15", "EJ-103", "Cliente Ejemplo A", "ARENA", "42500", "14200", "28,300"),
)

_FECHA_FIJA_ZIP = (1980, 1, 1, 0, 0, 0)
_FECHA_FIJA_LIBRO = datetime(2026, 10, 18, 0, 0, 0)
_RELLENO_MACRO = b"EJEMPLO CONSTRUIDO: relleno de prueba, no es una macro ni codigo ejecutable.\n"


def _csv(encabezados: Sequence[str], filas: Sequence[Sequence[object]]) -> bytes:
    """CSV UTF-8 sin BOM, delimitado por `;`, fin de línea `\\n`."""
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, delimiter=";", lineterminator="\n")
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return salida.getvalue().encode("utf-8")


def _zip_determinista(piezas: Sequence[tuple[str, bytes]]) -> bytes:
    """ZIP con fecha fija por pieza y el orden dado (así dos llamadas dan los mismos bytes)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for nombre, contenido in piezas:
            info = zipfile.ZipInfo(nombre, date_time=_FECHA_FIJA_ZIP)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, contenido)
    return buffer.getvalue()


def _xlsx(encabezados: Sequence[str], filas: Sequence[Sequence[object]]) -> bytes:
    """xlsx de una hoja `Reporte`; los números van como celdas numéricas nativas."""
    libro = Workbook()
    hoja = libro.active
    assert hoja is not None
    hoja.title = "Reporte"
    hoja.append(list(encabezados))
    for fila in filas:
        hoja.append(list(fila))
    libro.properties.creator = "ejemplo construido"
    libro.properties.created = _FECHA_FIJA_LIBRO
    libro.properties.modified = _FECHA_FIJA_LIBRO
    crudo = io.BytesIO()
    libro.save(crudo)
    with zipfile.ZipFile(io.BytesIO(crudo.getvalue())) as zf:
        piezas = [(i.filename, zf.read(i.filename)) for i in zf.infolist()]
    return _zip_determinista(piezas)


def csv_basico() -> bytes:
    """Reporte básico en CSV: 6 filas de datos, pesos en texto (ORACULO.md §1)."""
    return _csv(ENCABEZADOS_BASICOS, [tuple(str(c) for c in fila) for fila in FILAS_BASICAS])


def xlsx_basico() -> bytes:
    """Reporte básico en xlsx: las mismas 6 filas, pesos como números nativos (ORACULO.md §1)."""
    return _xlsx(ENCABEZADOS_BASICOS, FILAS_BASICAS)


def xlsx_sin_unidad() -> bytes:
    """Como `xlsx_basico()` pero los encabezados de peso no llevan unidad (ORACULO.md §2)."""
    return _xlsx(ENCABEZADOS_SIN_UNIDAD, FILAS_BASICAS)


def csv_coma_decimal() -> bytes:
    """Tres filas con `1.234,56`, `1,234.56` y el ambiguo `28,300` (ORACULO.md §3)."""
    return _csv(ENCABEZADOS_BASICOS, FILAS_COMA_DECIMAL)


def xlsx_con_macros_renombrado() -> bytes:
    """xlsx básico al que se le añade `xl/vbaProject.bin` (ORACULO.md §4).

    El relleno no es una macro: solo hace que la pieza exista, que es lo que delata a un libro con
    macros guardado con extensión `.xlsx`.
    """
    with zipfile.ZipFile(io.BytesIO(xlsx_basico())) as zf:
        piezas = [(i.filename, zf.read(i.filename)) for i in zf.infolist()]
    piezas.append(("xl/vbaProject.bin", _RELLENO_MACRO))
    return _zip_determinista(piezas)


def csv_desmedido(filas: int) -> bytes:
    """Encabezado más `filas` líneas de datos coherentes (ORACULO.md §5)."""
    if filas < 0:
        raise ValueError("filas no puede ser negativa")
    datos = (
        (
            f"TCK-{i:06d}",
            "2026-10-01",
            f"EJ-{i:06d}",
            "Cliente Ejemplo A",
            "ARENA",
            "40000",
            "15000",
            "25000",
        )
        for i in range(1, filas + 1)
    )
    return _csv(ENCABEZADOS_BASICOS, list(datos))
