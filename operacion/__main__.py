"""`python -m operacion` (spec S5 §6.5): casos, revisión, migrar, respaldar, restaurar y adoptar.

En la 0.6.0 se corre a mano en desarrollo (`uv run python -m operacion …`); desde la 1.0.0 la llaman
el instalador y el lanzador. `restaurar` exige Sílice detenido: hasta que el lanzador (S5-2) deje
`estado/servidor.json`, lo comprueba quien la ejecuta.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from operacion import base_datos, config, respaldo


def _texto_revision(estado: base_datos.EstadoBase) -> str:
    if not estado.existe:
        return "no existe"
    if respaldo.TABLA_VERSION not in estado.tablas:
        return "sin alembic_version"
    return estado.revision or "sin revisiones"


def _casos(_argumentos: argparse.Namespace) -> int:
    casos = base_datos.listar_casos()
    print(
        "\n".join(r.name for r in casos) if casos else f"(ningún caso en {config.carpeta_casos()})"
    )
    return 0


def _revision(_argumentos: argparse.Namespace) -> int:
    bases = [(config.ruta_instalacion(), base_datos.Destino.INSTALACION)]
    bases += [(caso, base_datos.Destino.CASO) for caso in base_datos.listar_casos()]
    for ruta, destino in bases:
        head = base_datos.revision_head(destino) or "sin revisiones"
        print(f"{ruta.name}: {_texto_revision(base_datos.leer_estado(ruta))} (head {head})")
    return 0


def _migrar(_argumentos: argparse.Namespace) -> int:
    for resultado in base_datos.migrar_todo():
        if resultado.nueva:
            detalle = "creada"
        elif resultado.juego is not None:
            detalle = f"migrada (respaldo previo: {resultado.juego})"
        else:
            detalle = "al día"
        print(f"{resultado.ruta.name}: {detalle}")
    return 0


def _respaldar(_argumentos: argparse.Namespace) -> int:
    print(base_datos.respaldar_todo())
    return 0


def _restaurar(argumentos: argparse.Namespace) -> int:
    resultado = base_datos.restaurar_juego(argumentos.juego, solo_caso=argumentos.solo_caso)
    print("Restauradas: " + ", ".join(ruta.name for ruta in resultado.restauradas))
    print(f"Bases de antes de restaurar: {resultado.antes}")
    if resultado.eventos_perdidos is not None:
        print(f"Eventos de seguridad perdidos (revíselos): {resultado.eventos_perdidos}")
    return 0


def _adoptar(argumentos: argparse.Namespace) -> int:
    resultado = base_datos.adoptar_base(argumentos.origen, argumentos.nombre)
    print(
        f"Adoptada en {resultado.ruta} (revisión {resultado.revision_destino}); respaldo previo: "
        f"{resultado.juego}. El original no se modificó."
    )
    return 0


_ORDENES: dict[str, Callable[[argparse.Namespace], int]] = {
    "casos": _casos,
    "revision": _revision,
    "migrar": _migrar,
    "respaldar": _respaldar,
    "restaurar": _restaurar,
    "adoptar": _adoptar,
}


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="python -m operacion", description=__doc__.splitlines()[0]
    )
    ordenes = analizador.add_subparsers(dest="orden", required=True)
    ordenes.add_parser("casos", help="lista los casos de la carpeta de datos")
    ordenes.add_parser("revision", help="revisión de cada base y la head de su destino")
    ordenes.add_parser(
        "migrar", help="lleva a head la instalación y todos los casos, con un solo juego"
    )
    ordenes.add_parser("respaldar", help="juego manual de la instalación y de todos los casos")
    restaurar = ordenes.add_parser("restaurar", help="restaura un juego (con Sílice detenido)")
    restaurar.add_argument("juego", type=Path)
    restaurar.add_argument("--solo-caso", dest="solo_caso")
    adoptar = ordenes.add_parser(
        "adoptar", help="copia una base anterior a la carpeta de casos y la migra"
    )
    adoptar.add_argument("origen", type=Path)
    adoptar.add_argument("--nombre")
    argumentos = analizador.parse_args(argv)
    try:
        return _ORDENES[argumentos.orden](argumentos)
    except base_datos.ErrorDeBase as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
