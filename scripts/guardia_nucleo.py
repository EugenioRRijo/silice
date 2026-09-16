"""Guardia del nucleo para CI: la hipotesis central aplicada a un rango de commits.

Aplica a `<base>..HEAD` la regla de `scripts/meta_alpha.py` (`estado_nucleo_intacto`): falla si un
commit toca `core/` junto a `adapters/` o `ml/`, o si una rama fusionada que incorpora un dominio
cambia `core/` (CLAUDE.md seccion 1). A diferencia de las metas de sprint, la base no esta fija: la
pone quien llama (el workflow de CI o el desarrollador en local).

Codigos de salida: 0 si la regla se cumple o el rango no tiene commits de dominio; 1 si se viola;
2 si la base no existe (una base invalida nunca se lee como rango vacio).

Uso: `uv run python scripts/guardia_nucleo.py --base main`.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import (  # noqa: E402
    Estado,
    _commits_nucleo_intacto,
    _git,
    _ramas_adaptador,
    estado_nucleo_intacto,
)

SALIDA_CUMPLE = 0
SALIDA_VIOLACION = 1
SALIDA_BASE_INVALIDA = 2


def veredicto(
    base: str,
    *,
    base_existe: bool,
    commits: Sequence[tuple[str, Sequence[str]]],
    ramas: Sequence[tuple[str, Sequence[str]]],
) -> tuple[int, str]:
    """Codigo de salida y mensaje para el rango `base..HEAD` ya leido de git.

    2 si la base no existe; 1 si `estado_nucleo_intacto` da FALLA; 0 con OK o con PENDIENTE (el
    rango no tiene commits de `adapters/` ni `ml/`, asi que no hay nada que violar).
    """
    if not base_existe:
        return SALIDA_BASE_INVALIDA, f"la base {base!r} no existe en este repositorio"
    estado, evidencia = estado_nucleo_intacto(commits, ramas)
    codigo = SALIDA_VIOLACION if estado is Estado.FALLA else SALIDA_CUMPLE
    return codigo, f"{estado.value}: {evidencia}"


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--base", required=True, help="referencia git desde la que se evalua el rango base..HEAD"
    )
    base = analizador.parse_args(argv).base

    base_existe = bool(_git("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"))
    commits = _commits_nucleo_intacto(base) if base_existe else []
    ramas = _ramas_adaptador(base) if base_existe else []
    codigo, mensaje = veredicto(base, base_existe=base_existe, commits=commits, ramas=ramas)
    print(f"guardia del nucleo: {mensaje}")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
