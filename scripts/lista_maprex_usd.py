"""Deriva la lista de precios MaPreX en el formato canonico de UC-02 (Tarea 6).

Los cuatro `data/precios/maprex_2026-07/referencia_{civil,telecom,industrial,sistemas}.csv`
(Sesion M0.2, `scripts/extraer_maprex.py`) traen once columnas de auditoria (`precio_bs`,
`bono_bs`, `factor_depreciacion`, `fecha_vigencia`, `archivo`, `ref_maprex`, `notas`...) que
documentan de donde sale cada precio. El cargador de UC-02 (`core.catalog.precios.
leer_lista_precios`) exige exactamente cuatro: `tipo,insumo,unidad,precio`
(`core.catalog.precios.COLUMNAS_ARCHIVO`). Este script deriva esa forma reducida sin transcribir
ningun precio a mano: cada fila de salida copia como texto la columna `precio_usd` que ya trae el
archivo de origen, calculada alli por conversion desde bolivares a la tasa declarada de
633,3644 Bs/USD al 01/07/2026 (README de la carpeta).

MaPreX es una referencia de mercado del sector construccion venezolano, no una ronda de
cotizaciones vigente levantada para este proyecto: sirve para contrastar los precios que el
sistema construye, no para sustituir la lista de precios de ningun presupuesto real.

ADVERTENCIA sobre `tipo=equipo`: la columna `precio` de la salida es el valor de reposicion del
activo completo (lo que cuesta comprarlo), NO una tarifa diaria de uso. Por ejemplo, la fila
`equipo,CAMION VOLTEO 8 M3 FORD 7000 O SIM,dia,113244.4451` no significa que el camion cueste
113 244,4451 USD por dia: ese numero es el precio del camion nuevo. El CSV crudo de origen
(`referencia_civil.csv` y hermanos) trae ademas `factor_depreciacion` (0,004000 para ese camion),
y es `precio x factor_depreciacion` lo que aproxima una tarifa diaria (≈ 453 USD/dia). El formato
canonico de cuatro columnas (`tipo,insumo,unidad,precio`) no tiene donde poner ese factor: quien
componga un APU con un equipo de esta lista debe ir a buscar `factor_depreciacion` al CSV crudo,
igual que exige `LineaEquipo.depreciacion` (`core/contracts/apu.py`) y la regla R6
(`CriterioDepreciacion`), que pide que el factor viva declarado en la composicion, no en la lista
de precios.

Que hace `filas_canonicas()`
-----------------------------
1. Lee los cuatro CSV de origen con `csv.DictReader` (no con un troceo por comas: varias
   descripciones de `referencia_civil.csv` traen comas dentro de un campo entrecomillado, por
   ejemplo un diametro escrito `4"" / 110 MM E = 2,2 MM`, y un `split(",")` las desalinearia en
   silencio).
2. Omite toda fila cuya columna `precio_usd` este vacia (red de seguridad: hoy ninguna de las 111
   filas lo esta) y cuenta cuantas omitio.
3. Descarta duplicados por la clave `(tipo, insumo, unidad)`, conservando la primera fila que
   aparece leyendo los cuatro archivos en orden (civil, telecom, industrial, sistemas).
4. Ordena por esa misma clave, para que la salida sea deterministica y dos ejecuciones produzcan
   el mismo archivo, byte a byte.

`main()` escribe el resultado en `RUTA_SALIDA` con `csv.DictWriter` y la cabecera
`COLUMNAS_ARCHIVO`, e imprime cuantas filas escribio y cuantas omitio por `precio_usd` vacio.

Uso::

    uv run python scripts/lista_maprex_usd.py
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

# Igual que en scripts/seed_telecom.py: ejecutado como `python scripts/...`, sys.path[0] es
# scripts/ y `core` no se resuelve (pyproject declara `package = false`).
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.catalog.precios import COLUMNAS_ARCHIVO  # noqa: E402

CARPETA = RAIZ / "data" / "precios" / "maprex_2026-07"

#: Los cuatro CSV de origen (Sesion M0.2), en el orden en que se leen y se resuelven duplicados.
ARCHIVOS_ORIGEN: tuple[Path, ...] = tuple(
    CARPETA / f"referencia_{dominio}.csv"
    for dominio in ("civil", "telecom", "industrial", "sistemas")
)

RUTA_SALIDA = CARPETA / "lista_maprex_usd.csv"

#: Clave que identifica un insumo entre los cuatro archivos: descarta duplicados y ordena la
#: salida (mismo criterio, para que el resultado sea deterministico y reejecutable).
_ClaveInsumo = tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class _Lectura:
    """Lo que produce leer los cuatro CSV de origen: las filas canonicas y la auditoria."""

    filas: list[dict[str, str]]
    omitidas: int


def _leer_origen() -> _Lectura:
    vistos: dict[_ClaveInsumo, dict[str, str]] = {}
    omitidas = 0
    for ruta in ARCHIVOS_ORIGEN:
        with ruta.open(newline="", encoding="utf-8") as archivo:
            for fila in csv.DictReader(archivo):
                precio = fila["precio_usd"].strip()
                if not precio:
                    omitidas += 1
                    continue
                clave: _ClaveInsumo = (fila["tipo"], fila["insumo"], fila["unidad"])
                if clave in vistos:
                    continue
                vistos[clave] = {
                    "tipo": fila["tipo"],
                    "insumo": fila["insumo"],
                    "unidad": fila["unidad"],
                    "precio": precio,
                }
    filas = [vistos[clave] for clave in sorted(vistos)]
    return _Lectura(filas=filas, omitidas=omitidas)


def filas_canonicas() -> list[dict[str, str]]:
    """Las filas de la lista MaPreX en el formato canonico `COLUMNAS_ARCHIVO`.

    Deterministico y reejecutable: la clave de deduplicacion y la de orden son la misma
    (`tipo, insumo, unidad`), asi que dos llamadas producen exactamente la misma lista.
    """
    return _leer_origen().filas


def main() -> int:
    lectura = _leer_origen()
    with RUTA_SALIDA.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_ARCHIVO)
        escritor.writeheader()
        escritor.writerows(lectura.filas)
    print(f"{RUTA_SALIDA} generado con {len(lectura.filas)} filas.")
    print(f"filas omitidas por precio_usd vacio: {lectura.omitidas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
