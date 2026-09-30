"""Meta del sprint I6: evalua el cumplimiento de sus 12 metas (Sesiones I6.2 e I6.3).

Se define ANTES de implementar las sesiones (principio 5 de NORMAS.md: las metas existen primero
y el sprint se escribe para ponerlas en OK): las metas de pruebas arrancan en PENDIENTE porque sus
archivos no existen todavia, y el cierre del sprint exige 12/12.

Reutiliza la maquinaria de `scripts/meta_alpha.py` (parseo JUnit, estados, tabla, subprocesos):
un solo lugar para esa logica, DRY. Lo unico propio de este script son las metas y la base git.

Uso: `uv run python scripts/meta_i6.py [--json] [--sin-cobertura] [--base REF]
[--umbral-cobertura N]`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import (  # noqa: E402
    Estado,
    Fila,
    Meta,
    _evaluar,
    _filas_a_json,
    render_tabla,
)

#: Etiqueta puesta sobre el merge de I6.1 (`2502c51`), el punto de partida del sprint.
BASE_POR_DEFECTO = "i6-base"
UMBRAL_COBERTURA_POR_DEFECTO = 80

METAS_I6: tuple[Meta, ...] = (
    Meta(
        "M1",
        "Registro de rendimientos medidos con referencia a ejecucion (RF-25)",
        "pruebas",
        ("tests/integration/test_rendimientos.py",),
    ),
    Meta(
        "M2",
        "Propuesta de rendimiento con dispersion: n, media, min, max (RF-26)",
        "pruebas",
        ("tests/integration/test_rendimientos.py",),
    ),
    Meta(
        "M3",
        "Advertencia por rendimiento desviado sin impedir el registro (RF-27)",
        "pruebas",
        ("tests/integration/test_api_rendimientos.py",),
    ),
    Meta(
        "M4",
        "Estimado y medido siempre distinguidos, del contrato a la API",
        "pruebas",
        (
            "tests/integration/test_rendimientos.py",
            "tests/integration/test_api_rendimientos.py",
        ),
    ),
    Meta(
        "M5",
        "Compuerta G2 cruzada: conteo por dominio documentado y tecnica elegida",
        "pruebas",
        ("tests/unit/test_prediccion.py",),
    ),
    Meta(
        "M6",
        "Prediccion por reglas con analisis de sensibilidad (dominios con < 50 registros)",
        "pruebas",
        ("tests/unit/test_prediccion.py",),
    ),
    Meta(
        "M7",
        "Contraste construido vs estimado: desviacion % y hallazgo ADVERTENCIA AACE (RF-29)",
        "pruebas",
        ("tests/unit/test_prediccion.py",),
    ),
    Meta(
        "M8",
        "docs/resultados_ml.md generado con MAPE, RMSE y R2 declarados (RF-28)",
        "pruebas",
        ("tests/unit/test_resultados_ml.py",),
    ),
    Meta(
        "M9",
        "Separacion de capas: ningun commit mezcla core/ con adapters/ o ml/",
        "git",
    ),
    Meta("M10", "Cobertura de core/ >= umbral", "cobertura"),
    Meta("M11", "ruff check y ruff format --check limpios", "ruff"),
    Meta("M12", "Suite completa sin fallos ni errores", "suite"),
)


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_i6.py",
        description="Evalua el cumplimiento de las 12 metas del sprint I6.",
    )
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    parser.add_argument(
        "--sin-cobertura",
        action="store_true",
        help="no mide cobertura de core/ al correr pytest (M10 queda PENDIENTE)",
    )
    parser.add_argument(
        "--base",
        default=BASE_POR_DEFECTO,
        help=f"referencia git de inicio del sprint (por defecto {BASE_POR_DEFECTO})",
    )
    parser.add_argument(
        "--umbral-cobertura",
        type=int,
        default=UMBRAL_COBERTURA_POR_DEFECTO,
        help=f"umbral de cobertura de core/, en % (por defecto {UMBRAL_COBERTURA_POR_DEFECTO})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear_args(argv)
    filas: list[Fila] = _evaluar(
        args.base, args.umbral_cobertura, con_cobertura=not args.sin_cobertura, metas=METAS_I6
    )

    if args.json:
        print(_filas_a_json(filas))
    else:
        print(render_tabla(filas))

    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
