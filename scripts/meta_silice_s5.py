"""Parte S5 de la meta unica de Silice (spec S5 §12 y §13; plan 0.6.0, seccion B, tarea 7).

`scripts/meta_silice.py` (A4) la descubre por su nombre. Con `--hasta S5-1` o posterior evalua: C1,
RF-96 y RNF-20 por presencia en la ERS; C3, la prueba de cada pieza de S5-1 antes que su codigo; y
S5-M3, la base de prueba de la 0.5.0 con su ficha, generada con el codigo de `v0.5.0` (RV-3). El
nucleo intacto en la rama de S5-1 (S5-M2) no es acumulable a las fases de nucleo siguientes: lo
vigilan `scripts/guardia_nucleo.py` en la CI de esa rama y la compuerta GS5-1. La regresion (S5-M8)
es C5 de la meta.
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
from scripts.meta_silice import Comprobacion, Contexto, ParTDD, Parte  # noqa: E402

CARPETA_BASE_050 = RAIZ / "tests" / "fixtures" / "bases" / "v0_5_0"
BASES_050 = ("demo.db", "of001.db", "ti001.db")
COMMIT_V050 = "8610053"

#: Prueba -> implementacion de S5-1 (C3 de la meta; el commit de la prueba va antes).
PARES_S5: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_operacion_config.py", "operacion/config.py", "S5-1"),
    ParTDD("tests/unit/test_migraciones_metadatos.py", "migraciones/metadatos.py", "S5-1"),
    ParTDD("tests/unit/test_generar_base_prueba.py", "scripts/generar_base_prueba.py", "S5-1"),
    ParTDD("tests/unit/test_congelar_esquema.py", "scripts/congelar_esquema.py", "S5-1"),
    ParTDD("tests/integration/test_migraciones.py", "operacion/base_datos.py", "S5-1"),
    ParTDD("tests/integration/test_respaldo.py", "operacion/respaldo.py", "S5-1"),
    ParTDD("tests/integration/test_operacion_cli.py", "operacion/__main__.py", "S5-1"),
    ParTDD("tests/unit/test_meta_silice_s5.py", "scripts/meta_silice_s5.py", "S5-1"),
)


def evaluar_base_050(carpeta: Path) -> tuple[Estado, str]:
    """S5-M3: la ficha es de `v0.5.0` (commit 8610053) y cada base tiene la huella de su ficha."""
    ruta_ficha = carpeta / "ficha.json"
    if not ruta_ficha.is_file():
        return Estado.FALLA, f"falta {ruta_ficha}"
    ficha = json.loads(ruta_ficha.read_text(encoding="utf-8"))
    de_la_etiqueta = (ficha.get("version"), ficha.get("etiqueta")) == ("0.5.0", "v0.5.0")
    if not de_la_etiqueta or not str(ficha.get("commit", "")).startswith(COMMIT_V050):
        return Estado.FALLA, f"la ficha no es de v0.5.0 ({COMMIT_V050}): {ficha.get('commit')!r}"
    bases = ficha.get("bases") or {}
    distintas = [
        nombre
        for nombre in BASES_050
        if nombre not in bases
        or not (carpeta / nombre).is_file()
        or hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest()
        != bases[nombre]["sha256_base"]
    ]
    if distintas:
        return Estado.FALLA, "bases ausentes o distintas de su ficha: " + ", ".join(distintas)
    return Estado.OK, "base de prueba 0.5.0 de v0.5.0: " + ", ".join(BASES_050)


def _base_050(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_base_050(CARPETA_BASE_050)


PARTE = Parte(
    nombre="S5-1 Alembic, preparar_base y respaldo",
    requisitos={"S5-1": ("RF-96", "RNF-20")},
    pares_tdd=PARES_S5,
    comprobaciones=(
        Comprobacion("S5-M3", "Base de prueba 0.5.0 de su etiqueta, con ficha", "S5-1", _base_050),
    ),
)
