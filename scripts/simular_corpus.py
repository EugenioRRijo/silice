"""Generador determinista de un corpus simulado de composiciones APU (Sesion P4.3).

**Que es.** Un corpus de composiciones **simulado** para probar la interfaz con volumen: abrir la
pantalla de composicion (`ui/paginas/componer.py`) contra una base con cientos de partidas. Cada
composicion combina, con un unico `random.Random(semilla)`, filas de la referencia MaPreX de julio
de 2026 (`ui.composicion.buscar_referencia`) con cantidades y rendimientos sorteados desde enteros,
y se arma con la **misma** capa pura que usa la pantalla (`fila_*_desde_referencia` y
`composicion_desde_tablas`): el corpus ejercita ese codigo, no una copia de el.

**Que no es.** No es un dato de mercado, no proviene de obra ejecutada, no alimenta `ml/` y
no cuenta para ninguna compuerta: en particular, no cuenta para la compuerta G2 (CLAUDE.md §8.1),
que sigue cruzada con degradacion a reglas. Las cantidades, los rendimientos y la combinacion de
insumos de cada partida `SIM-*` son sorteados; solo los precios unitarios de los insumos vienen de
la referencia MaPreX (CLAUDE.md §1, naturaleza de los datos).

**Cuarentena, en dos capas.**

1. Por archivo: `main` se niega (codigo de salida distinto de cero y mensaje en `stderr`) si el
   archivo de `--db` ya existe. El corpus vive siempre en su propia base nueva, nunca mezclado con
   el catalogo de trabajo ni con `data/apu.db`; por eso `--db` es obligatorio y no tiene valor por
   defecto. Como la base es nueva, `sembrar_corpus` no tiene lista de precios anterior que heredar.
2. Por codigo: la meta P11 (`scripts/meta_prototipo.py`) falla si algun modulo de `ml/` menciona
   este generador o el corpus que produce.

Uso::

    uv run python scripts/simular_corpus.py --db /tmp/corpus_simulado.db
    uv run python scripts/simular_corpus.py --db /tmp/corpus_simulado.db --n 500 --semilla 7
"""

from __future__ import annotations

import argparse
import random
import sys
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

# Ejecutado como `python scripts/simular_corpus.py`, sys.path[0] es scripts/, no el raiz del repo.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy.orm import Session  # noqa: E402

from core import models  # noqa: E402
from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_motor  # noqa: E402
from core.contracts import ComposicionAPU, Dominio  # noqa: E402
from ui.composicion import (  # noqa: E402
    FilaReferencia,
    buscar_referencia,
    composicion_desde_tablas,
    fila_equipos_desde_referencia,
    fila_mano_obra_desde_referencia,
    fila_materiales_desde_referencia,
)

#: Fecha fija del corpus (vigencia de su lista y de sus rendimientos): una constante y no
#: `date.today()`, para que dos corridas con la misma semilla dejen la misma base.
FECHA_CORPUS = date(2026, 9, 21)

#: Unidades de las partidas simuladas; todas son formas canonicas de `normalizar_unidad`
#: (`core/contracts/unidades.py`), lo que comprueba `tests/unit/test_simular_corpus.py`.
UNIDADES_CORPUS: tuple[str, ...] = ("m", "m2", "m3", "pieza", "unidad")

N_POR_DEFECTO = 200
SEMILLA_POR_DEFECTO = 42

#: Dominio con el que se cargan las partidas. El corpus mezcla filas de las cuatro referencias
#: MaPreX, asi que el dominio no describe su origen: es solo el que la pantalla lista primero.
DOMINIO_CORPUS = Dominio.CIVIL
MONEDA_CORPUS = "USD"
NOMBRE_LISTA_CORPUS = "Lista del corpus simulado (pruebas de volumen, no es mercado)"
ORIGEN_LISTA_CORPUS = "scripts/simular_corpus.py (precios de la referencia MaPreX jul-2026)"
CONDICIONES_CORPUS = (
    "rendimiento simulado por scripts/simular_corpus.py para pruebas de volumen de la interfaz; "
    "sorteado, no proviene de una ejecucion medida ni de una estimacion de obra"
)

#: Intervalos de los sorteos (enteros; cada cantidad es `Decimal(entero) / Decimal(100)`).
_MATERIALES = (1, 4)
_EQUIPOS = (0, 2)
_OBREROS = (1, 3)
_CENTESIMAS_CANTIDAD = (1, 400)
_RENDIMIENTO = (1, 200)


def _cantidad(generador: random.Random) -> str:
    """Cantidad de una linea, desde enteros y nunca desde `random.random()` (sin `float`)."""
    return str(Decimal(generador.randint(*_CENTESIMAS_CANTIDAD)) / Decimal(100))


def _equipos_validos() -> list[FilaReferencia]:
    """Equipos de MaPreX que forman un `LineaEquipo` valido: `0 < factor_depreciacion <= 1`."""
    return [
        fila
        for fila in buscar_referencia("", "equipo")
        if fila.factor_depreciacion is not None and 0 < fila.factor_depreciacion <= 1
    ]


def generar_corpus(n: int, semilla: int) -> tuple[ComposicionAPU, ...]:
    """`n` composiciones simuladas `SIM-0001`...; pura y determinista (sin base de datos).

    Dentro de una composicion no se repite ninguna fila de la referencia (`random.sample`).
    """
    generador = random.Random(semilla)
    materiales = buscar_referencia("", "material")
    equipos = _equipos_validos()
    obreros = buscar_referencia("", "mano_obra")

    corpus = []
    for indice in range(1, n + 1):
        filas_materiales = []
        for fila in generador.sample(materiales, generador.randint(*_MATERIALES)):
            filas_materiales.append(
                {**fila_materiales_desde_referencia(fila), "cantidad": _cantidad(generador)}
            )
        filas_equipos = []
        for fila in generador.sample(equipos, generador.randint(*_EQUIPOS)):
            filas_equipos.append(
                {**fila_equipos_desde_referencia(fila), "cantidad": _cantidad(generador)}
            )
        filas_mano_obra = []
        for fila in generador.sample(obreros, generador.randint(*_OBREROS)):
            filas_mano_obra.append(
                {**fila_mano_obra_desde_referencia(fila), "cantidad": _cantidad(generador)}
            )
        unidad = generador.choice(UNIDADES_CORPUS)
        rendimiento = str(Decimal(generador.randint(*_RENDIMIENTO)))
        corpus.append(
            composicion_desde_tablas(
                codigo=f"SIM-{indice:04d}",
                descripcion=f"Partida simulada {indice:04d} (corpus de volumen, no es obra)",
                unidad=unidad,
                rendimiento=rendimiento,
                filas_materiales=filas_materiales,
                filas_equipos=filas_equipos,
                filas_mano_obra=filas_mano_obra,
            )
        )
    return tuple(corpus)


def sembrar_corpus(sesion: Session, composiciones: Sequence[ComposicionAPU], fecha: date) -> int:
    """Crea la lista de precios propia del corpus y carga cada composicion; devuelve cuantas.

    No confirma la transaccion: eso es de quien llama (`main`). Pensada para una base nueva (la
    cuarentena por archivo de `main`), no hereda precios de ninguna lista anterior.
    """
    lista = models.ListaPrecios(
        nombre=NOMBRE_LISTA_CORPUS,
        moneda=MONEDA_CORPUS,
        fecha_vigencia=fecha,
        origen=ORIGEN_LISTA_CORPUS,
    )
    sesion.add(lista)
    sesion.flush()

    catalogo = Catalogo(sesion)
    for composicion in composiciones:
        catalogo.cargar_composicion(composicion, lista, DOMINIO_CORPUS, fecha, CONDICIONES_CORPUS)
    return len(composiciones)


def main(argv: Sequence[str] | None = None) -> int:
    """Genera el corpus y lo carga en una base SQLite nueva; se niega si el archivo ya existe."""
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--db", required=True, help="ruta de un archivo SQLite NUEVO (se niega si ya existe)"
    )
    analizador.add_argument(
        "--n",
        type=int,
        default=N_POR_DEFECTO,
        help=f"cantidad de composiciones (por defecto {N_POR_DEFECTO})",
    )
    analizador.add_argument(
        "--semilla",
        type=int,
        default=SEMILLA_POR_DEFECTO,
        help=f"semilla para reproducibilidad (por defecto {SEMILLA_POR_DEFECTO})",
    )
    argumentos = analizador.parse_args(argv)

    ruta = Path(argumentos.db)
    if ruta.exists():
        print(
            f"{ruta} ya existe: el corpus simulado solo se carga en una base nueva (cuarentena); "
            "elija otra ruta",
            file=sys.stderr,
        )
        return 1

    composiciones = generar_corpus(argumentos.n, argumentos.semilla)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            cargadas = sembrar_corpus(sesion, composiciones, FECHA_CORPUS)
            sesion.commit()
    finally:
        motor.dispose()

    print(
        f"Corpus simulado: {cargadas} composiciones SIM-* cargadas en {ruta} "
        f"(semilla {argumentos.semilla}, vigencia {FECHA_CORPUS})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
