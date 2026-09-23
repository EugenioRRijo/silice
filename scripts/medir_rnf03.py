"""Mide RNF‑03: tiempo del recálculo masivo de UC‑02 con N partidas en SQLite local.

La métrica de docs/ERS.md §3.3 exige recalcular un presupuesto de hasta 100 partidas en menos de
5 segundos tras cambiar la lista de precios, en el equipo de desarrollo, con SQLite local y sin
exportación. Este script produce esa evidencia de forma reproducible:

1. siembra la línea base (5 APU) y la replica hasta alcanzar N partidas de catálogo;
2. elabora, audita y guarda el presupuesto 001 con esos N renglones;
3. escribe una lista de precios nueva con todos los insumos un 10 % más caros;
4. cronometra únicamente `actualizar_precios` (UC‑02 completo: recomposición de los N APU,
   reelaboración con auditoría, guardado de la versión 002 e histórico de cambios e incidencias).

Uso:
    uv run python scripts/medir_rnf03.py                  # 100 partidas, umbral 5 s
    uv run python scripts/medir_rnf03.py --partidas 50    # otro tamaño

Como scripts/seed.py, importa `tests.fixtures.apu_linea_base` a propósito: es la única copia de la
línea base (CLAUDE.md §2, DRY). Sale con código 0 si cumple la meta y 1 si no.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
import time
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.budget import actualizar_precios, elaborar, guardar_presupuesto  # noqa: E402
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor  # noqa: E402
from core.catalog.precios import crear_lista_desde_archivo  # noqa: E402
from core.contracts.dominio import Dominio  # noqa: E402
from core.contracts.item_computo import ItemComputo, OrigenTipo  # noqa: E402
from scripts.seed import NOMBRE_PROYECTO, sembrar  # noqa: E402
from tests.fixtures import apu_linea_base as linea_base  # noqa: E402

UMBRAL_SEGUNDOS = Decimal("5")
AUMENTO = Decimal("1.10")
CODIGO_BASE = "001"
CODIGO_NUEVO = "002"
#: RF-33 (spec §3.3): esta es una carga sintetica para medir tiempos, no un rendimiento de obra.
CONDICIONES_SINTETICAS = "carga sintetica de la medicion RNF-03; no es un rendimiento de obra"


def replicar_catalogo(catalogo: Catalogo, partidas_objetivo: int) -> list[str]:
    """Replica los cinco APU de la línea base hasta que el catálogo tenga N códigos.

    Cada réplica es la misma composición con otro código (`EXC-R01`, `EXC-R02`, …): lo que se
    mide es el volumen del recálculo, no la variedad de los desgloses.
    """
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    codigos = [apu.codigo_partida for apu in linea_base.APUS_LINEA_BASE]
    replica = 0
    while len(codigos) < partidas_objetivo:
        replica += 1
        for apu in linea_base.APUS_LINEA_BASE:
            if len(codigos) >= partidas_objetivo:
                break
            copia = replace(apu, codigo_partida=f"{apu.codigo_partida}-R{replica:02d}")
            catalogo.cargar_composicion(
                copia, lista, Dominio.CIVIL, linea_base.FECHA_LINEA_BASE, CONDICIONES_SINTETICAS
            )
            codigos.append(copia.codigo_partida)
    return codigos


def escribir_lista_aumentada(destino: Path) -> Path:
    """Escribe el CSV de UC‑02 con cada insumo de la línea base un 10 % más caro."""
    filas: dict[tuple[str, str, str], Decimal] = {}
    for apu in linea_base.APUS_LINEA_BASE:
        for material in apu.materiales:
            filas[("material", material.descripcion, material.unidad)] = material.precio
        for equipo in apu.equipos:
            filas[("equipo", equipo.descripcion, "")] = equipo.precio
        for obrero in apu.mano_obra:
            filas[("mano_obra", obrero.descripcion, "")] = obrero.sueldo
    ruta = destino / "lista_rnf03.csv"
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(("tipo", "insumo", "unidad", "precio"))
        for (tipo, insumo, unidad), precio in sorted(filas.items()):
            escritor.writerow((tipo, insumo, unidad, precio * AUMENTO))
    return ruta


def medir(partidas_objetivo: int, directorio: Path) -> tuple[Decimal, int, int]:
    """Prepara el escenario y cronometra UC‑02. Devuelve (segundos, renglones, afectados)."""
    motor = crear_motor(f"sqlite:///{(directorio / 'rnf03.db').as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            catalogo = Catalogo(sesion)
            codigos = replicar_catalogo(catalogo, partidas_objetivo)

            composiciones = catalogo.composiciones(codigos, fecha=linea_base.FECHA_LINEA_BASE)
            items = [
                ItemComputo(
                    codigo_partida=codigo,
                    descripcion=composiciones[codigo].descripcion,
                    unidad=composiciones[codigo].unidad,
                    cantidad=Decimal(1),
                    origen_id=f"rnf03:{codigo}",
                    origen_tipo=OrigenTipo.MANUAL,
                    dominio=Dominio.CIVIL,
                )
                for codigo in codigos
            ]
            resultado = elaborar(
                items,
                composiciones,
                linea_base.PARAMETROS_LINEA_BASE,
                codigo=CODIGO_BASE,
                fecha=linea_base.FECHA_LINEA_BASE,
                moneda=linea_base.MONEDA,
            )
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=proyecto,
                lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
                parametros=linea_base.PARAMETROS_LINEA_BASE,
            )
            sesion.commit()

            resumen = crear_lista_desde_archivo(
                sesion,
                escribir_lista_aumentada(directorio),
                nombre="RNF-03 todos los insumos +10 %",
                moneda=linea_base.MONEDA,
                fecha_vigencia=linea_base.FECHA_LINEA_BASE + timedelta(days=1),
                origen="scripts/medir_rnf03.py",
            )
            sesion.commit()

            inicio = time.perf_counter()
            _, comparativo = actualizar_precios(
                sesion, NOMBRE_PROYECTO, CODIGO_BASE, resumen.lista, CODIGO_NUEVO
            )
            sesion.commit()
            segundos = Decimal(str(time.perf_counter() - inicio))
            return segundos, len(codigos), comparativo.insumos_afectados
    finally:
        motor.dispose()


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--partidas", type=int, default=100, help="renglones del presupuesto (por defecto 100)"
    )
    argumentos = analizador.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="rnf03-") as temporal:
        segundos, renglones, afectados = medir(argumentos.partidas, Path(temporal))

    cumple = segundos < UMBRAL_SEGUNDOS
    print(f"Partidas recalculadas: {renglones}")
    print(f"Insumos con precio nuevo: {afectados}")
    print(f"Tiempo de actualizar_precios: {segundos:.2f} s (umbral {UMBRAL_SEGUNDOS} s)")
    print(f"RNF-03: {'CUMPLE' if cumple else 'NO CUMPLE'}")
    return 0 if cumple else 1


if __name__ == "__main__":
    raise SystemExit(main())
