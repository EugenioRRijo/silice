"""Cuadrículas neutras para los casos negativos (S1 §7.1): sin escribir .xls."""

import re
from decimal import Decimal
from pathlib import Path

from adapters.bcv.libro import Hoja, Libro

D = Decimal
COMPRA = Decimal("858.02")
VENTA = Decimal("860.18")

CARPETA = Path(__file__).resolve().parent / "bcv"


def hoja_tasa(
    nombre,
    fecha="01/10/2026",
    compra=COMPRA,
    venta=VENTA,
    codigo="USD",
    etiqueta="Fecha Valor:",
):
    return Hoja(
        nombre,
        (
            ("BANCO CENTRAL DE VENEZUELA", None, None),
            (f"{etiqueta} {fecha}", None, None),
            ("EUR", D("1000.1"), D("1002.3")),
            (codigo, compra, venta),
        ),
    )


def libro(*hojas, archivo="2_1_2c26_smc.xls"):
    return Libro(archivo, "0" * 64, tuple(hojas))


def transcripcion(seccion: str) -> list[dict[str, str]]:
    """Filas de la transcripción a mano de FUENTE.md (Tarea 3)."""
    texto = (CARPETA / "FUENTE.md").read_text(encoding="utf-8").split(f"## {seccion}")[1]
    tabla = texto.split("### Transcripción")[1].split("\n## ")[0]
    filas = [f.strip().strip("|").split("|") for f in tabla.splitlines() if f.startswith("| ")]
    encabezado = [c.strip() for c in filas[0]]
    return [dict(zip(encabezado, (c.strip() for c in f), strict=True)) for f in filas[2:]]


def campo(seccion: str, nombre: str) -> str:
    texto = (CARPETA / "FUENTE.md").read_text(encoding="utf-8").split(f"## {seccion}")[1]
    return re.search(rf"^\| {re.escape(nombre)} \| ([^|]+?) \|$", texto, re.MULTILINE).group(1)
