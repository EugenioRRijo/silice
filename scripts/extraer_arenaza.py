"""Genera y verifica los dos CSV de presupuestos ARENAZA (Sesion M1.1 del PLAN_MULTIDOMINIO)
en `data/telecom/fuentes/`: `presupuesto_1_arenaza.csv` (14 renglones, 1109.29 USD) y
`presupuesto_2_arenaza.csv` (26 renglones, 5410.73 USD).

Unica copia estructurada de los 40 renglones (CLAUDE.md seccion 2, principio DRY)
------------------------------------------------------------------------------
`tests/fixtures/presupuestos_arenaza.py` (`PRESUPUESTO_1`, `PRESUPUESTO_2`) es la UNICA
transcripcion de los 40 renglones en todo el repositorio. Este script no repite esos datos: los
importa y (a) escribe los CSV a partir de ellos, (b) verifica el fixture contra el texto de los
PDF, recien extraido con PyMuPDF, cada vez que corre. Mismo patron que `scripts/seed.py`, el
unico modulo fuera de `tests/` que importa `tests.fixtures.apu_linea_base` (linea base civil):
un script de infraestructura puede importar un fixture de pruebas cuando ese fixture es,
deliberadamente, la unica copia de un dato del dominio.

PyMuPDF no es dependencia del proyecto (mismo criterio que `scripts/extraer_maprex.py`, Sesion
M0.2: los PDF son evidencia de una sola sesion, no un flujo de la aplicacion). Ejecutar con:

    uv run --with pymupdf python scripts/extraer_arenaza.py

Que hace este script
--------------------
1. Lee, con PyMuPDF, el texto de cada pagina de `Presupuesto_1_ARENAZA.pdf` y
   `Presupuesto_2_ARENAZA.pdf` (`data/samples/telecom/`). Cada PDF trae dos tablas: "Computos
   metricos" (pagina 1) y "Presupuesto" (pagina 2, la que tiene precio unitario y total, y la
   que transcribe el fixture).
2. `_verificar_contra_pdf()` comprueba que el `total` de cada renglon del fixture y el total
   impreso del PDF (con coma de millar, derivado de `TOTAL_1`/`TOTAL_2` del fixture, no
   duplicado a mano) aparecen literalmente en el texto que PyMuPDF extrae de la pagina 2. Si
   alguno no aparece -- un renglon del fixture no transcribe lo que dice el PDF, o el PDF
   cambio -- el script se detiene con un error explicito en vez de escribir un CSV no
   verificado. No revalida cantidad/unidad/precio por renglon: el layout de dos columnas del
   PDF intercala esos valores con los de otras filas de forma no trivial de emparejar por texto
   plano; el total por renglon mas el total impreso ya bastan para detectar un renglon omitido,
   una transcripcion incorrecta o un PDF que cambio.
3. Escribe la cabecera exacta `renglon,descripcion,unidad,cantidad,precio_unitario,total,origen`
   a partir de los campos de cada `RenglonPresupuesto` del fixture. `cantidad` y
   `precio_unitario` en `None` (unicamente el renglon "Micelaneos" del presupuesto 1, una
   partida global sin base de cantidad x precio -- ver el docstring del fixture) se escriben
   como celda vacia, igual que en el PDF de origen.

Regenerar los CSV con este script es un no-op: sus columnas ya se derivan integramente del
fixture, asi que dos corridas sucesivas (o una corrida despues de que otra persona edito el CSV
a mano) producen exactamente el mismo contenido. Si algun dia el fixture cambia un valor, correr
este script vuelve a dejar los CSV consistentes con el; si el cambio no coincide con el PDF,
`_verificar_contra_pdf` lo detiene antes de escribir nada.

Hallazgos declarados (documentados con mas detalle en el docstring del fixture y en
`data/telecom/fuentes/README.md`; no se repiten aqui los numeros, solo se referencian)
-------------------------------------------------------------------------------------------
- El renglon del "Tubo Corrugado Flexible 1 Pulgada" del presupuesto 2 (item 5) trae una
  cantidad distinta en cada tabla del mismo PDF (`TUBO_CORRUGADO` del fixture): la
  inconsistencia que esta sesion registra tal cual, sin corregir.
- Dos renglones del presupuesto 2 (items 14 y 18) tienen un `total` impreso que no coincide con
  `cantidad x precio_unitario`: hallazgos adicionales, tambien preservados tal cual.
"""

from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover - guia de uso, no logica de negocio
    raise SystemExit(
        "Falta PyMuPDF. Ejecutar con:\n"
        "  uv run --with pymupdf python scripts/extraer_arenaza.py"
    ) from exc

# Ejecutado como `python scripts/extraer_arenaza.py`, sys.path[0] es scripts/, no la raiz del
# repositorio: `tests` no se resuelve sin este ajuste (mismo problema y misma solucion que
# `scripts/seed.py`, que importa `tests.fixtures.apu_linea_base`).
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from tests.fixtures.presupuestos_arenaza import (  # noqa: E402
    PRESUPUESTO_1,
    PRESUPUESTO_2,
    TOTAL_1,
    TOTAL_2,
    TUBO_CORRUGADO,
    RenglonPresupuesto,
)

CARPETA_PDF = RAIZ / "data" / "samples" / "telecom"
CARPETA_SALIDA = RAIZ / "data" / "telecom" / "fuentes"

RUTA_PDF_1 = CARPETA_PDF / "Presupuesto_1_ARENAZA.pdf"
RUTA_PDF_2 = CARPETA_PDF / "Presupuesto_2_ARENAZA.pdf"

CABECERA = ["renglon", "descripcion", "unidad", "cantidad", "precio_unitario", "total", "origen"]

PAGINA_PRESUPUESTO = 2  # 1-indexada: pagina 1 = Computos metricos, pagina 2 = Presupuesto


def _paginas_pdf(ruta: Path) -> list[str]:
    """El texto de cada pagina del PDF, por separado (no concatenado): la verificacion contra
    el PDF necesita distinguir la pagina 1 ("Computos metricos") de la pagina 2
    ("Presupuesto")."""
    with fitz.open(ruta) as doc:
        return [pagina.get_text() for pagina in doc]


def _verificar_contra_pdf(
    nombre_pdf: str,
    texto_paginas: list[str],
    filas: tuple[RenglonPresupuesto, ...],
    total_impreso: str,
) -> None:
    """Comprueba que el `total` de cada renglon del FIXTURE y el total impreso del PDF aparecen
    literalmente en el texto extraido de la pagina 2 ("Presupuesto"). Ver el docstring del
    modulo (punto 2) para el porque no revalida cantidad/unidad/precio por renglon.
    """
    texto_presupuesto = texto_paginas[PAGINA_PRESUPUESTO - 1]
    faltantes = [
        f"{nombre_pdf} renglon {fila.renglon} ({fila.descripcion}): total {fila.total} no "
        "aparece en el texto de la pagina 2 del PDF"
        for fila in filas
        if str(fila.total) not in texto_presupuesto
    ]
    if total_impreso not in texto_presupuesto:
        faltantes.append(
            f"{nombre_pdf}: el total impreso {total_impreso} no aparece en el texto de la "
            "pagina 2 del PDF"
        )
    if faltantes:
        raise SystemExit(
            "Verificacion contra el PDF fallida (revisar tests/fixtures/presupuestos_arenaza.py "
            "o si el PDF cambio):\n  " + "\n  ".join(faltantes)
        )


def _fila_csv(fila: RenglonPresupuesto) -> dict[str, str]:
    return {
        "renglon": str(fila.renglon),
        "descripcion": fila.descripcion,
        "unidad": fila.unidad,
        "cantidad": "" if fila.cantidad is None else str(fila.cantidad),
        "precio_unitario": "" if fila.precio_unitario is None else str(fila.precio_unitario),
        "total": str(fila.total),
        "origen": fila.origen,
    }


def escribir_csv(ruta: Path, filas: list[dict[str, str]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CABECERA)
        escritor.writeheader()
        escritor.writerows(filas)


def _suma(filas: tuple[RenglonPresupuesto, ...]) -> Decimal:
    return sum((fila.total for fila in filas), Decimal("0"))


def main() -> int:
    paginas_1 = _paginas_pdf(RUTA_PDF_1)
    paginas_2 = _paginas_pdf(RUTA_PDF_2)

    # Con coma de millar (formato en que el PDF imprime "TOTAL PRESUPUESTO"), derivado de
    # TOTAL_1/TOTAL_2 del fixture -- no un literal "1,109.29" duplicado a mano.
    total_impreso_1 = format(TOTAL_1, ",")
    total_impreso_2 = format(TOTAL_2, ",")

    _verificar_contra_pdf(RUTA_PDF_1.name, paginas_1, PRESUPUESTO_1, total_impreso_1)
    _verificar_contra_pdf(RUTA_PDF_2.name, paginas_2, PRESUPUESTO_2, total_impreso_2)

    # El fixture ya fija estos totales en tests/unit/test_fuentes_arenaza.py::test_totales_
    # exactos; esta comprobacion es barata y evita escribir un CSV si alguien edito una fila del
    # fixture sin actualizar TOTAL_1/TOTAL_2.
    suma_1, suma_2 = _suma(PRESUPUESTO_1), _suma(PRESUPUESTO_2)
    if suma_1 != TOTAL_1:
        raise SystemExit(
            f"La suma de PRESUPUESTO_1 da {suma_1}, no coincide con TOTAL_1={TOTAL_1}."
        )
    if suma_2 != TOTAL_2:
        raise SystemExit(
            f"La suma de PRESUPUESTO_2 da {suma_2}, no coincide con TOTAL_2={TOTAL_2}."
        )

    filas_csv_1 = [_fila_csv(fila) for fila in PRESUPUESTO_1]
    filas_csv_2 = [_fila_csv(fila) for fila in PRESUPUESTO_2]

    escribir_csv(CARPETA_SALIDA / "presupuesto_1_arenaza.csv", filas_csv_1)
    escribir_csv(CARPETA_SALIDA / "presupuesto_2_arenaza.csv", filas_csv_2)

    print("Fuentes ARENAZA generadas desde tests/fixtures/presupuestos_arenaza.py:")
    print(f"  presupuesto_1_arenaza.csv -> {len(filas_csv_1)} renglones, total {suma_1}")
    print(f"  presupuesto_2_arenaza.csv -> {len(filas_csv_2)} renglones, total {suma_2}")
    print(
        f"  tubo corrugado (presupuesto 2, renglon 5): "
        f"{TUBO_CORRUGADO['cantidad_presupuesto']} m en la tabla Presupuesto vs "
        f"{TUBO_CORRUGADO['cantidad_computos']} m en Computos metricos (inconsistencia "
        "registrada, no corregida)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
