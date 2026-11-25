"""Genera un libro FICTICIO con errores sembrados y su clave, para ver la auditoría y ensayarla.

El libro sale de la misma fábrica de libros sintéticos de las pruebas
(`tests/fixtures/libros_empresa`): empresa, obra y precios son inventados. Trae errores de varias
clases a la vez, para que la auditoría muestre la variedad de sus reglas (F1, L1, L3 a L7 y L9) y
no solo los avisos que salen en todo libro.

La clave (`clave_ficticia.xlsx`) tiene el formato de `scripts/medir_auditoria_libro.py`, así que
con este libro se ensaya el protocolo completo sin tocar un libro real:

    uv run python scripts/libro_ficticio_con_errores.py --salida D:/ensayo
    uv run python scripts/medir_auditoria_libro.py exportar \\
        D:/ensayo/libro_ficticio_con_errores.xlsx --salida D:/ensayo/planilla.xlsx \\
        --fecha AAAA-MM-DD
    uv run python scripts/medir_auditoria_libro.py calcular \\
        --planilla D:/ensayo/planilla.xlsx --clave D:/ensayo/clave_ficticia.xlsx \\
        --libro D:/ensayo/libro_ficticio_con_errores.xlsx \\
        --libro-base D:/ensayo/libro_ficticio_base.xlsx --fecha AAAA-MM-DD

`libro_ficticio_base.xlsx` es el mismo libro sin sembrar: `calcular --clave` lo audita para no
acreditar a una falla sembrada lo que el libro ya señalaba.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.medir_auditoria_libro import (  # noqa: E402
    _destino_seguro,
    escribir_clave_vacia,
)


@dataclass(frozen=True, slots=True)
class Sembrada:
    regla: str  # la regla que debe señalarlo
    que: str  # qué se cambió en el libro
    celda: str = ""  # dónde, si es una celda (vacía si es un nombre, un vínculo o una hoja)


SIEMBRAS: tuple[Sembrada, ...] = (
    Sembrada("F1", "P.U. de la partida 1 guardado en 999,99 (el APU da otra cosa)",
             "PRESUPUESTO!P5"),
    Sembrada("L3", "rendimiento de la partida 3 guardado viejo, distinto del de su APU"),
    Sembrada("L1", "el CRONOGRAMA lee el rendimiento de una fila fija equivocada",
             "CRONOGRAMA!D4"),
    Sembrada("L4", "el costo directo de APU-02 deja fuera los equipos", "APU-02!G36"),
    Sembrada("L6", "la utilidad de APU-02 escrita a mano (0,02) en vez del parámetro",
             "APU-02!F39"),
    Sembrada("L6", "los equipos de APU-03 divididos entre 12 en vez del rendimiento"),
    Sembrada("L5", "una fórmula del RESUMEN con #REF!", "RESUMEN!B13"),
    Sembrada("L5", "un nombre definido (MEDP1) que apunta a otro libro"),
    Sembrada("L5", "un vínculo a un libro de un servidor ficticio"),
    Sembrada("L7", "una medición con las medidas escritas dentro de la fórmula", "MEDICIONES!D5"),
    Sembrada("L9", "la verificación del PLAN DE PAGOS no da cero (40)", "PLAN DE PAGOS!B6"),
    Sembrada("L9", "la diferencia de PROCURA contra el presupuesto no da cero (5)"),
)


OBRA = "Tramo vial de ensayo — obra ficticia"
NOMBRE_BASE = "libro_ficticio_base.xlsx"


def construir_base() -> bytes:
    """Los bytes del mismo libro sin ninguna siembra (el libro base de la medición)."""
    from tests.fixtures.libros_empresa import APUS_LIMPIOS, Siembra, construir_libro

    return construir_libro(APUS_LIMPIOS, Siembra(obra=OBRA)).datos


def construir() -> bytes:
    """Los bytes del libro con todas las siembras de `SIEMBRAS`."""
    from tests.fixtures.libros_empresa import APUS_LIMPIOS, Siembra, con, construir_libro

    a1, a2, a3 = APUS_LIMPIOS
    apus = (a1, con(a2, cd_sin_equipos=True, utilidad_literal=Decimal("0.02")),
            con(a3, divisor_equipos=Decimal("12")))
    siembra = Siembra(
        p_guardado={1: Decimal("999.99")},
        rend_guardado={3: Decimal("0.5")},
        cronograma_fila_rend=23,
        resumen_ref_rota=True,
        nombres_externos=("MEDP1",),
        vinculo_externo="file:///servidor-ficticio/obras/mediciones.xlsx",
        mediciones_literales=("=9.73*2.75",),
        plan_dif=Decimal("40"),
        procura_dif=Decimal("5"),
        obra=OBRA,
    )
    return construir_libro(apus, siembra).datos


def generar(carpeta: Path, *, raiz_repo: Path = RAIZ) -> tuple[Path, Path]:
    """Escribe el libro, su clave y el libro base sin sembrar (`NOMBRE_BASE`) en `carpeta`
    (fuera del repositorio) y devuelve las rutas del libro y de la clave."""
    import openpyxl

    carpeta = Path(carpeta)
    libro = _destino_seguro(carpeta / "libro_ficticio_con_errores.xlsx", Path(raiz_repo))
    _destino_seguro(carpeta / "clave_ficticia.xlsx", Path(raiz_repo))
    base = _destino_seguro(carpeta / NOMBRE_BASE, Path(raiz_repo))
    carpeta.mkdir(parents=True, exist_ok=True)  # solo después de comprobar que es seguro
    clave = escribir_clave_vacia(carpeta / "clave_ficticia.xlsx", raiz_repo=Path(raiz_repo))
    libro.write_bytes(construir())
    base.write_bytes(construir_base())
    hoja_libro = openpyxl.load_workbook(clave)
    hoja = hoja_libro["Sembrados"]
    for numero, s in enumerate(SIEMBRAS, start=1):
        hoja.append([numero, s.celda, f"{s.regla}: {s.que}", s.que, None])
    hoja_libro.save(clave)
    return libro, clave


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", required=True, help="carpeta fuera del repositorio")
    analizador.add_argument("--raiz-repo", default=str(RAIZ))
    args = analizador.parse_args(argv)
    libro, clave = generar(Path(args.salida), raiz_repo=Path(args.raiz_repo))
    print(f"Libro ficticio con {len(SIEMBRAS)} errores sembrados: {libro}")
    print(f"Su clave: {clave}")
    print(f"El mismo libro sin sembrar: {clave.parent / NOMBRE_BASE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
