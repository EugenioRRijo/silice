"""Parte S1 de la meta unica de Silice (spec S1 §9.4; plan 0.6.0, seccion C, tarea 1).

`scripts/meta_silice.py` (A4) la descubre por su nombre. Con `--hasta` en una fase de S1 evalua:
C1, los once requisitos de S1-0 por presencia en la ERS; C3, la prueba de cada expediente (SL-E1,
SL-E2, SL-E3) y de cada interprete del BCV antes que su codigo; y tres comprobaciones propias:
S1-MEM (memorias a mano antes del codigo que rigen), S1-FUENTE (archivos reales del BCV con su
`FUENTE.md` antes del primer interprete) y S1-BASE-060 (base de prueba de la 0.6.0 con su ficha).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_sf import _ordenar_memoria, evaluar_s2_memorias  # noqa: E402
from scripts.meta_silice import (  # noqa: E402
    Comprobacion,
    Contexto,
    ParTDD,
    Parte,
    _primer_commit,
    orden_de_par,
)

REQUISITOS_S1: tuple[str, ...] = (
    "UC-17",
    "UC-18",
    *(f"RF-{numero}" for numero in range(64, 72)),
    "RNF-14",
)

#: Memoria -> argumentos de `git log` que localizan el primer commit del codigo que rige.
MEMORIAS_S1: dict[str, tuple[str, ...]] = {
    "s1_conversion.md": ("--", "core/catalog/moneda.py"),
    "s1_precios_empresa.md": ("--", "core/verification/precios.py"),
    "s1_reajuste.md": ("--", "core/budget/reajuste.py"),
    "s1_reajuste_por_partida.md": ("--", "core/budget/reajuste.py"),
}
RUTA_MEMORIAS = RAIZ / "tests" / "fixtures" / "memorias"
RUTA_FUENTE_BCV = "tests/fixtures/bcv/FUENTE.md"
PRIMER_INTERPRETE_BCV = "adapters/bcv/tasa.py"
CARPETA_BASE_060 = RAIZ / "tests" / "fixtures" / "bases" / "v0_6_0"

#: Prueba -> implementacion, con la fase en que arranca cada par (C3 de la meta).
PARES_S1: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_meta_silice_s1.py", "scripts/meta_silice_s1.py", "S1-0"),
    ParTDD("tests/integration/test_indices.py", "core/catalog/indices.py", "S1-1"),
    ParTDD("tests/unit/test_moneda.py", "core/catalog/moneda.py", "S1-1"),
    ParTDD("tests/integration/test_conversion_version.py", "core/budget/moneda.py", "S1-1"),
    ParTDD("tests/unit/adapters/test_bcv_libro.py", "adapters/bcv/libro.py", "S1-2"),
    ParTDD("tests/unit/adapters/test_bcv_tasa.py", "adapters/bcv/tasa.py", "S1-2"),
    ParTDD("tests/unit/adapters/test_bcv_inpc.py", "adapters/bcv/inpc.py", "S1-2"),
    ParTDD("tests/unit/adapters/test_bcv_csv.py", "adapters/bcv/csv_canonico.py", "S1-2"),
    ParTDD("tests/integration/test_lista_empresa.py", "core/catalog/empresa.py", "S1-3"),
    ParTDD("tests/integration/test_precios_empresa.py", "core/verification/precios.py", "S1-3"),
    ParTDD("tests/unit/test_reajuste.py", "core/budget/reajuste.py", "S1-4"),
)


def evaluar_fuente_bcv(
    fuente_existe: bool, interprete_existe: bool, orden: bool | None
) -> tuple[Estado, str]:
    """S1-FUENTE: la transcripcion a mano existe y su commit precede al del primer interprete."""
    if not fuente_existe:
        return Estado.FALLA, f"falta {RUTA_FUENTE_BCV}"
    if not interprete_existe:
        return Estado.OK, f"{RUTA_FUENTE_BCV} presente; el interprete aun no existe"
    if orden is None:
        return Estado.PENDIENTE, f"sin commit de {RUTA_FUENTE_BCV} o de {PRIMER_INTERPRETE_BCV}"
    if not orden:
        return Estado.FALLA, f"{RUTA_FUENTE_BCV} no entro antes que {PRIMER_INTERPRETE_BCV}"
    return Estado.OK, f"{RUTA_FUENTE_BCV} versionado antes que {PRIMER_INTERPRETE_BCV}"


def evaluar_base_060(carpeta: Path) -> tuple[Estado, str]:
    """S1-BASE-060: `ficha.json` de la etiqueta v0.6.0 y la huella SHA-256 de cada base."""
    ruta_ficha = carpeta / "ficha.json"
    if not ruta_ficha.is_file():
        return Estado.PENDIENTE, "la base de prueba 0.6.0 se genera desde la etiqueta v0.6.0"
    ficha = json.loads(ruta_ficha.read_text(encoding="utf-8"))
    if (ficha.get("version"), ficha.get("etiqueta")) != ("0.6.0", "v0.6.0"):
        return Estado.FALLA, f"la ficha dice {ficha.get('version')!r} / {ficha.get('etiqueta')!r}"
    bases = ficha.get("bases") or {}
    distintas = [
        nombre
        for nombre, datos in sorted(bases.items())
        if not (carpeta / nombre).is_file()
        or hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest() != datos["sha256_base"]
    ]
    if not bases or distintas:
        detalle = ", ".join(distintas) or "la ficha no trae bases"
        return Estado.FALLA, "bases ausentes o distintas de su ficha: " + detalle
    return Estado.OK, "base de prueba 0.6.0 con ficha: " + ", ".join(sorted(bases))


def _orden_memoria(memoria: str, criterio: tuple[str, ...]) -> bool | None:
    """Antes de que exista el codigo, basta que la memoria este versionada."""
    if not (RAIZ / criterio[-1]).exists():
        return True if _primer_commit(f"tests/fixtures/memorias/{memoria}") else None
    return _ordenar_memoria(memoria, criterio)


def _memorias(_ctx: Contexto) -> tuple[Estado, str]:
    presentes = {m: (RUTA_MEMORIAS / m).is_file() for m in MEMORIAS_S1}
    antes = {m: _orden_memoria(m, criterio) for m, criterio in MEMORIAS_S1.items()}
    codigo = any((RAIZ / criterio[-1]).exists() for criterio in MEMORIAS_S1.values())
    return evaluar_s2_memorias(presentes, antes, codigo_existe=codigo)


def _fuente(_ctx: Contexto) -> tuple[Estado, str]:
    interprete = (RAIZ / PRIMER_INTERPRETE_BCV).is_file()
    par = ParTDD(RUTA_FUENTE_BCV, PRIMER_INTERPRETE_BCV, "S1-0")
    orden = orden_de_par(par) if interprete else None
    return evaluar_fuente_bcv((RAIZ / RUTA_FUENTE_BCV).is_file(), interprete, orden)


def _base_060(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_base_060(CARPETA_BASE_060)


PARTE = Parte(
    nombre="S1 moneda, precios de empresa, BCV y reajuste",
    requisitos={"S1-0": REQUISITOS_S1},
    pares_tdd=PARES_S1,
    comprobaciones=(
        Comprobacion("S1-MEM", "Memorias antes del codigo que rigen", "S1-0", _memorias),
        Comprobacion("S1-FUENTE", "FUENTE.md del BCV antes del interprete", "S1-0", _fuente),
        Comprobacion("S1-BASE-060", "Base de prueba 0.6.0 con su ficha", "S1-5", _base_060),
    ),
)
