"""Siembra la oficina OF-001 en su propia base para CP-08 a CP-11 del guion (sprint final).

Deja, en un archivo SQLite propio (por defecto `data/prueba_sf.db`), el catalogo de las 30 partidas
de OF-001, su lista de precios y el proyecto con la version `001` (la hoja manual: 6 ambientes,
6 fuentes, 21 puntos y 2 circuitos) con su informe de auditoria. Es la base de la hoja del
proyecto: CP-10 y CP-11 parten de esta version `001`; CP-08 y CP-09 empiezan en un borrador vacio.

**Caso didactico, no obra ejecutada.** OF-001 es un caso construido para el proyecto
(NORMAS.md §1); sus precios y rendimientos son supuestos declarados de las memorias de calculo.

Uso::

    uv run python scripts/seed_of001.py --db data/prueba_sf.db            # la primera vez
    uv run python scripts/seed_of001.py --db data/prueba_sf.db --reiniciar # repetir la prueba

Nunca escribe en `data/apu.db` (la base de trabajo de la aplicacion): se niega aunque se le pida con
`--confirmar` o con una ruta equivalente. Sobre una base que ya existe exige `--reiniciar`, que la
borra antes de sembrarla, de modo que cada repeticion de la prueba parte de la misma base.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.catalog import Catalogo, abrir_sesion, crear_motor  # noqa: E402
from scripts.seed import RUTA_POR_DEFECTO as RUTA_TRABAJO  # noqa: E402
from scripts.seed import agregar_opciones_de_reinicio, linea_auditoria, monto  # noqa: E402
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001  # noqa: E402
from ui import hoja  # noqa: E402

RUTA_POR_DEFECTO = "data/prueba_sf.db"
CODIGO_VERSION = "001"


def _motivo_para_no_sembrar(ruta: Path, reiniciar: bool) -> str | None:
    """Por que no se debe sembrar `ruta`, o `None` si se puede."""
    if ruta.resolve() == Path(RUTA_TRABAJO).resolve():
        return (
            f"{RUTA_TRABAJO} es la base de trabajo de la aplicacion y esta siembra no la toca. "
            f"Use otra ruta, por ejemplo --db {RUTA_POR_DEFECTO}."
        )
    if ruta.exists() and not reiniciar:
        return f"{ruta} ya existe. Repita la orden con --reiniciar para sembrarla de nuevo."
    return None


def _imprimir_resumen(ruta: Path) -> None:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            abierta = hoja.abrir_version(sesion, Catalogo(sesion), NOMBRE_OF001, CODIGO_VERSION)
            presupuesto = abierta.guardada.presupuesto
            print(f"Base de datos: {ruta}")
            print(f"Proyecto: {NOMBRE_OF001}")
            print(f"Version {CODIGO_VERSION}: {len(presupuesto.partidas)} partidas")
            print(f"  Total: {monto(presupuesto.total)} {presupuesto.moneda}")
            print(f"  {linea_auditoria(abierta.guardada.informe)}")
    finally:
        motor.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--db",
        default=RUTA_POR_DEFECTO,
        help=f"ruta del archivo SQLite (por defecto {RUTA_POR_DEFECTO})",
    )
    agregar_opciones_de_reinicio(analizador)
    argumentos = analizador.parse_args(argv)
    ruta = Path(argumentos.db)
    motivo = _motivo_para_no_sembrar(ruta, argumentos.reiniciar)
    if motivo is not None:
        print(motivo, file=sys.stderr)
        return 2
    if ruta.exists():
        ruta.unlink()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    plantilla_of001(ruta)
    _imprimir_resumen(ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
