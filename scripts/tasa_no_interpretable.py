"""Mide la tasa de libros auditados, rechazados por la guardia y no interpretables en una carpeta.

Recorre una carpeta de archivos `.xlsx` fuera del repositorio (NORMAS §1), audita cada uno con
`procesar_libro` y agrupa los rechazos (`ArchivoRechazado`) y fallos de interpretación
(`LibroNoInterpretable`) por motivo normalizado, sin imprimir nombres de archivo, clientes ni
montos.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from adapters.hoja_empresa.guardia import ArchivoRechazado  # noqa: E402
from adapters.hoja_empresa.modelo import LibroNoInterpretable  # noqa: E402
from core.verification.texto import formatear_decimal  # noqa: E402
from fusion.proceso import procesar_libro  # noqa: E402

EXTENSIONES_LIBRO: frozenset[str] = frozenset({".xlsx", ".xls", ".xlsm", ".xlsb", ".xltm"})

_REGLAS_RECHAZO: tuple[tuple[tuple[str, ...], str], ...] = (
    (("no tiene la hoja", "plantilla"), "falta la hoja PRESUPUESTO de la plantilla"),
    (("está dañado o no es de excel",), "archivo dañado o no es un .xlsx válido"),
    (("alguna hoja está dañada",), "hoja dañada"),
    (("falta xl/workbook.xml",), "falta xl/workbook.xml"),
    (("vbaproject.bin",), "contiene macros (vbaProject.bin)"),
    (("solo se aceptan libros de excel .xlsx sin macros",), "extensión no admitida o con macros"),
    (("celdas combinadas",), "demasiadas celdas combinadas"),
    (("por hoja", "máximo es"), "hoja supera el máximo de celdas declaradas"),
    (("filas con datos o con formato más allá",), "hoja supera el máximo de filas"),
    (("hasta la columna",), "hoja supera el máximo de columnas"),
    (("entre sus hojas",), "libro supera el máximo de celdas"),
    (("compresión anómala",), "compresión anómala"),
    (("por pieza",), "pieza interna supera el tamaño máximo descomprimido"),
    (("descomprimido y supera el máximo",), "supera el tamaño máximo descomprimido"),
    (("piezas internas",), "supera el máximo de piezas internas"),
    (("pesa", "supera el máximo"), "supera el tamaño máximo de archivo"),
)

_REGLAS_NO_INTERPRETABLE: tuple[tuple[tuple[str, ...], str], ...] = (
    (("fcas",), "FCAS fuera de rango (menor que 1)"),
    (("no se puede recalcular",), "APU no recalculable"),
    (("no pudo recalcularlo",), "datos no compatibles con la plantilla"),
    (("pdf",), "PDF sin tablas revisables"),
)


@dataclass(frozen=True, slots=True)
class ResumenTasa:
    """Conteo agregado de libros y motivos normalizados sin datos identificables."""

    total: int
    auditados: int
    rechazados: int
    no_interpretables: int
    motivos_rechazo: dict[str, int]
    motivos_no_interpretable: dict[str, int]


def normalizar_motivo(error: ArchivoRechazado | LibroNoInterpretable) -> str:
    """Traduce el mensaje de excepción a una etiqueta cerrada, sin nombres ni cifras."""
    texto = str(error).casefold()
    reglas = (
        _REGLAS_RECHAZO if isinstance(error, ArchivoRechazado) else _REGLAS_NO_INTERPRETABLE
    )
    for claves, etiqueta in reglas:
        if all(clave in texto for clave in claves):
            return etiqueta
    if isinstance(error, ArchivoRechazado):
        return "otro rechazo de la guardia"
    return "otro error de interpretación"


def _carpeta_segura(carpeta: Path, raiz_repo: Path) -> Path:
    resuelta = carpeta.resolve()
    if resuelta.is_relative_to(raiz_repo.resolve()):
        raise ValueError(
            f"«{resuelta}» está dentro del repositorio: la carpeta de libros debe vivir fuera "
            "del proyecto (NORMAS §1)."
        )
    if not resuelta.is_dir():
        raise NotADirectoryError(f"«{resuelta}» no es una carpeta existente.")
    return resuelta


def medir_carpeta(
    carpeta: Path,
    *,
    raiz_repo: Path = RAIZ,
    fecha: date | None = None,
    perfil: str | None = None,
) -> ResumenTasa:
    """Recorre todos los `.xlsx` de `carpeta` y cuenta auditados, rechazados y no interpretables."""
    raiz = _carpeta_segura(Path(carpeta), Path(raiz_repo))
    archivos = sorted(
        ruta
        for ruta in raiz.rglob("*")
        if ruta.is_file()
        and ruta.suffix.lower() in EXTENSIONES_LIBRO
        and not ruta.name.startswith("~$")
    )
    auditados = 0
    motivos_rechazo: Counter[str] = Counter()
    motivos_no_interpretable: Counter[str] = Counter()
    for ruta in archivos:
        try:
            procesar_libro(ruta.read_bytes(), ruta.name, fecha_devolucion=fecha, perfil=perfil)
        except ArchivoRechazado as exc:
            motivos_rechazo[normalizar_motivo(exc)] += 1
        except LibroNoInterpretable as exc:
            motivos_no_interpretable[normalizar_motivo(exc)] += 1
        else:
            auditados += 1
    return ResumenTasa(
        total=len(archivos),
        auditados=auditados,
        rechazados=sum(motivos_rechazo.values()),
        no_interpretables=sum(motivos_no_interpretable.values()),
        motivos_rechazo=dict(sorted(motivos_rechazo.items())),
        motivos_no_interpretable=dict(sorted(motivos_no_interpretable.items())),
    )


def _porcentaje(cuenta: int, total: int) -> str:
    if total == 0:
        return "0,0 %"
    pct = Decimal(cuenta) * Decimal(100) / Decimal(total)
    return formatear_decimal(pct, 1).replace(".", ",") + " %"


def formatear_tabla(resumen: ResumenTasa) -> str:
    """Tablas Markdown con porcentajes en coma decimal y motivos normalizados."""
    lineas = [
        "| Estado | Libros | Porcentaje |",
        "|---|---:|---:|",
        f"| Auditados | {resumen.auditados} | {_porcentaje(resumen.auditados, resumen.total)} |",
        f"| Rechazados por la guardia | {resumen.rechazados} | "
        f"{_porcentaje(resumen.rechazados, resumen.total)} |",
        f"| No interpretables | {resumen.no_interpretables} | "
        f"{_porcentaje(resumen.no_interpretables, resumen.total)} |",
        f"| **Total** | **{resumen.total}** | **{_porcentaje(resumen.total, resumen.total)}** |",
    ]
    if resumen.motivos_rechazo or resumen.motivos_no_interpretable:
        lineas += [
            "",
            "| Tipo | Motivo normalizado | Libros | Porcentaje |",
            "|---|---|---:|---:|",
        ]
        for motivo, cuenta in resumen.motivos_rechazo.items():
            lineas.append(
                f"| Rechazado | {motivo} | {cuenta} | {_porcentaje(cuenta, resumen.total)} |"
            )
        for motivo, cuenta in resumen.motivos_no_interpretable.items():
            lineas.append(
                f"| No interpretable | {motivo} | {cuenta} | "
                f"{_porcentaje(cuenta, resumen.total)} |"
            )
    return "\n".join(lineas)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("carpeta", help="carpeta con libros .xlsx fuera del repositorio")
    analizador.add_argument("--fecha", type=date.fromisoformat, default=None, help="AAAA-MM-DD")
    analizador.add_argument("--perfil", default=None, help="perfil de plantilla")
    analizador.add_argument("--raiz-repo", default=str(RAIZ))
    args = analizador.parse_args(argv)
    resumen = medir_carpeta(
        Path(args.carpeta),
        raiz_repo=Path(args.raiz_repo),
        fecha=args.fecha,
        perfil=args.perfil,
    )
    print(formatear_tabla(resumen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
