"""Meta del sprint final del prototipo (SF): 10 metas agrupadas en seis fases (SF0-SF5).

Se define ANTES de las sesiones de `PLAN_SF.md`, igual que `meta_prototipo.py`: las metas existen
primero y cada fase se trabaja para ponerlas en OK (spec 2026-10-04, seccion 12.2). Reutiliza de
`scripts/meta_alpha.py` `Estado`, `Fila`, `_filas_a_json` y `render_tabla`.

Cada chequeo de contenido es una funcion pura sobre texto ya leido (`evaluar_*`). Las metas de
fases todavia no construidas dan PENDIENTE, nunca FALLA: es evidencia ausente, no un
incumplimiento. Hoy solo S1 (requisitos en la ERS) se evalua de verdad.

Nota: `FASES` agrupa cada meta en la fase donde ARRANCA su evaluacion. S3 («SF1-SF2» en la spec)
arranca en SF1 y S8 («todas») se conecta en SF1; por eso sus titulos llevan el alcance de la spec y
no la fase de agrupacion.

Uso: `uv run python scripts/meta_sf.py [--hasta SF0|SF1|SF2|SF3|SF4|SF5] [--json]`.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado, Fila, _filas_a_json, render_tabla  # noqa: E402

#: Fases del sprint final, en orden. Cada una agrupa las metas que arrancan en ella (spec 12.2).
FASES: dict[str, tuple[str, ...]] = {
    "SF0": ("S1",),
    "SF1": ("S2", "S3", "S8", "S10"),
    "SF2": ("S4",),
    "SF3": ("S5", "S9"),
    "SF4": ("S6",),
    "SF5": ("S7",),
}

TITULOS: dict[str, str] = {
    "S1": "(SF0) UC-13 a UC-16, RF-44 a RF-63 y RNF-11 a RNF-13 estan en docs/ERS.md",
    "S2": "(SF1) Memorias de calculo versionadas antes del codigo de su fase",
    "S3": "(SF1-SF2) Pruebas de agua, datos y electricidad en verde",
    "S4": "(SF2) core/ intacto desde gsf1 (y desde gsf4 al cerrar SF5)",
    "S5": "(SF3) Pruebas de edicion, versiones, restauracion, PE y Excel en verde",
    "S6": "(SF4) AppTest de navegacion y herramientas de la barra",
    "S7": "(SF5) Pruebas de importacion de DXF e IFC",
    "S8": "(todas) Regresion: linea base, R4, TI-001, huellas de RNF-04, cuatro hojas",
    "S9": "(SF3) RNF-11: mediana registrada <= 2 s en el equipo de desarrollo",
    "S10": "(SF1) adapters/espacio con cobertura >= 80 %",
}

#: Guion ASCII o no separable (U+2011): la ERS usa el tipografico.
_GUION = "[-‑]"

RUTA_ERS = RAIZ / "docs" / "ERS.md"

#: Identificadores que la ERS enmendada debe declarar (spec 4): (prefijo, numeros).
REQUISITOS_SF: tuple[tuple[str, range], ...] = (
    ("UC", range(13, 17)),
    ("RF", range(44, 64)),
    ("RNF", range(11, 14)),
)


def metas_hasta(fase: str) -> list[str]:
    """Codigos de las metas de `fase` y de todas las fases anteriores, en orden SF0 -> SF5."""
    if fase not in FASES:
        raise ValueError(f"fase desconocida: {fase!r}; validas: {', '.join(FASES)}")
    codigos: list[str] = []
    for nombre_fase, metas in FASES.items():
        codigos.extend(metas)
        if nombre_fase == fase:
            break
    return codigos


# --------------------------------------------------------------------------------------
# Chequeos puros
# --------------------------------------------------------------------------------------


def _patron_definicion(prefijo: str, numero: int) -> str:
    """Linea que DEFINE el requisito: UC por encabezado, RF por fila de tabla, RNF por fila de la
    tabla de calidad (el identificador va en la 2.a celda)."""
    id_ = rf"{prefijo}{_GUION}{numero}(?!\d)"
    if prefijo == "UC":
        return rf"^#{{3,4}}\s+{id_}"
    if prefijo == "RF":
        return rf"^\|\s*{id_}\s*\|"
    return rf"^\|[^|\n]*\|\s*{id_}"


def evaluar_s1_requisitos(texto_ers: str | None) -> tuple[Estado, str]:
    """Cada UC-13..16, RF-44..63 y RNF-11..13 esta DEFINIDO en la ERS (no basta mencionarlo)."""
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    faltan = [
        f"{prefijo}-{numero}"
        for prefijo, numeros in REQUISITOS_SF
        for numero in numeros
        if not re.search(_patron_definicion(prefijo, numero), texto_ers, re.MULTILINE)
    ]
    if faltan:
        return Estado.FALLA, "la ERS no define: " + ", ".join(faltan)
    total = sum(len(numeros) for _, numeros in REQUISITOS_SF)
    return Estado.OK, f"los {total} requisitos del sprint final estan definidos en docs/ERS.md"


def _pendiente(motivo: str) -> Callable[[], tuple[Estado, str]]:
    return lambda: (Estado.PENDIENTE, motivo)


# --------------------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------------------


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


def _evaluar_metas(codigos: list[str]) -> list[Fila]:
    chequeos: dict[str, Callable[[], tuple[Estado, str]]] = {
        "S1": lambda: evaluar_s1_requisitos(_leer(RUTA_ERS)),
        "S2": _pendiente("las memorias de calculo llegan con SF1"),
        "S3": _pendiente("las reglas de agua, datos y electricidad llegan con SF1-SF2"),
        "S4": _pendiente("se evalua al cerrar SF2 (git diff gsf1..HEAD -- core/)"),
        "S5": _pendiente("la hoja del proyecto llega con SF3"),
        "S6": _pendiente("la barra superior llega con SF4"),
        "S7": _pendiente("la importacion de planos llega con SF5"),
        "S8": _pendiente("la regresion se conecta al abrir SF1"),
        "S9": _pendiente("la medicion de RNF-11 llega con SF3"),
        "S10": _pendiente("adapters/espacio llega con SF1"),
    }
    return [Fila(codigo, TITULOS[codigo], *chequeos[codigo]()) for codigo in codigos]


def _parsear_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meta_sf.py",
        description="Evalua las 10 metas del sprint final del prototipo, agrupadas en SF0-SF5.",
    )
    parser.add_argument(
        "--hasta",
        choices=list(FASES),
        default=None,
        help="evalua solo las metas de esta fase y las anteriores (por defecto, las diez)",
    )
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de la tabla")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear_args(argv)
    if args.hasta:
        codigos = metas_hasta(args.hasta)
    else:
        codigos = [codigo for metas in FASES.values() for codigo in metas]
    filas = _evaluar_metas(codigos)
    print(_filas_a_json(filas) if args.json else render_tabla(filas))
    return 0 if all(fila.estado is Estado.OK for fila in filas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
