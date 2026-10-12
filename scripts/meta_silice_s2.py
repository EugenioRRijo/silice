# scripts/meta_silice_s2.py
"""Parte S2 de la meta única de Sílice (spec S2 §8; plan 0.7.0, tarea 1).

`scripts/meta_silice.py` la descubre por su nombre. Con `--version 0.7.0 --hasta FASE` evalúa,
además de las siete comprobaciones comunes: C1, la presencia en la ERS de UC-19, UC-20, RF-72 a
RF-79 y RNF-15 (nunca un conteo, REQ-19); C3, el commit de la prueba de cada módulo nuevo de S2
anterior al de su código y el del expediente anterior al de las tablas; C6, que `medir_rnf15.py`
dejó su cifra (sin cifra no es OK: PRU-H21); y las comprobaciones propias:

* `S2-MEM`: la memoria OB-S2 y su XLSX existen y la memoria se versionó antes que
  `core/budget/valor_ganado.py`;
* `S2-REGLAS`: la ERS define R13 y R14 (en la fila de RF-74);
* `S2-EXPEDIENTES`: la bitácora trae SL-E4, SL-E5 y SL-E6;
* `S2-REG-S1`: las memorias de S1 no cambiaron desde `v0.6.0`;
* `S2-BASE-070`: la base de prueba de la 0.7.0 con su ficha (fase S2-5).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_sf import _ordenar_memoria, evaluar_s2_memorias  # noqa: E402
from scripts.meta_silice import (  # noqa: E402
    CifraDeTiempo,
    Comprobacion,
    Contexto,
    ParTDD,
    Parte,
    _git,
    _primer_commit,
    _referencia_existe,
)

REQUISITOS_S2: tuple[str, ...] = (
    "UC-19",
    "UC-20",
    *(f"RF-{numero}" for numero in range(72, 80)),
    "RNF-15",
)
MEMORIAS_S2: dict[str, tuple[str, ...]] = {
    "control_ob_s2.md": ("--", "core/budget/valor_ganado.py"),
}
XLSX_OB_S2 = "tests/fixtures/control/ob_s2.xlsx"
RUTA_MEMORIAS = RAIZ / "tests" / "fixtures" / "memorias"
RUTA_EXPEDIENTES = RAIZ / "docs" / "bitacora" / "2026-10-silice-s2-expedientes.md"
CARPETA_BASE_070 = RAIZ / "tests" / "fixtures" / "bases" / "v0_7_0"
ETIQUETA_S1 = "v0.6.0"
MEMORIAS_DE_S1 = (
    "tests/fixtures/memorias/s1_conversion.md",
    "tests/fixtures/memorias/s1_precios_empresa.md",
    "tests/fixtures/memorias/s1_reajuste.md",
    "tests/fixtures/memorias/s1_reajuste_por_partida.md",
)
EXPEDIENTES = ("SL-E4", "SL-E5", "SL-E6")
GUION = "[-‑]"

#: Prueba -> implementación, con la fase en que arranca cada par (C3 de la meta).
PARES_S2: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_meta_silice_s2.py", "scripts/meta_silice_s2.py", "S2-0"),
    ParTDD("docs/bitacora/2026-10-silice-s2-expedientes.md", "core/models/control.py", "S2-1"),
    ParTDD(
        "tests/integration/test_migracion_s2.py",
        "migraciones/caso/versions/caso_0005_s2_valuaciones.py",
        "S2-1",
    ),
    ParTDD("tests/unit/test_calendario.py", "core/budget/calendario.py", "S2-1"),
    ParTDD("tests/unit/test_r13_r14.py", "core/verification/valuaciones.py", "S2-1"),
    ParTDD("tests/integration/test_valuaciones.py", "core/budget/valuaciones.py", "S2-1"),
    ParTDD("tests/integration/test_importar_valuaciones.py", "core/budget/valuaciones.py", "S2-1"),
    ParTDD("tests/integration/test_ejecutado_por_periodo.py", "core/budget/puente.py", "S2-1"),
    ParTDD("tests/unit/test_valor_ganado.py", "core/budget/valor_ganado.py", "S2-2"),
    ParTDD("tests/unit/test_reproyeccion.py", "core/budget/valor_ganado.py", "S2-2"),
    ParTDD("tests/unit/test_alertas.py", "core/budget/valor_ganado.py", "S2-2"),
    ParTDD("tests/unit/test_pe_proyectado.py", "core/budget/valor_ganado.py", "S2-2"),
    ParTDD("tests/integration/test_control.py", "core/budget/control.py", "S2-2"),
    ParTDD("tests/unit/test_generar_obra_control.py", "scripts/generar_obra_control.py", "S2-2"),
    ParTDD("tests/integration/test_reajuste_reconocido.py", "core/budget/control.py", "S2-2"),
    ParTDD("tests/unit/test_recuperacion.py", "core/budget/recuperacion.py", "S2-3"),
    ParTDD("tests/integration/test_decision_crea_version.py", "core/budget/decision.py", "S2-3"),
    ParTDD(
        "tests/integration/test_migracion_s2.py",
        "migraciones/caso/versions/caso_0006_s2_decision.py",
        "S2-3",
    ),
    ParTDD("tests/integration/test_ui_control.py", "ui/control.py", "S2-4"),
    ParTDD("tests/unit/test_ui_pagina_control.py", "ui/paginas/control.py", "S2-4"),
    ParTDD("tests/unit/test_medir_rnf15.py", "scripts/medir_rnf15.py", "S2-4"),
)
CIFRAS_S2: tuple[CifraDeTiempo, ...] = (
    CifraDeTiempo(
        "RNF-15 (valuacion a reproyeccion)",
        "scripts/_salida_rnf15.json",
        "mediana_registro_s",
        "uv run python scripts/medir_rnf15.py",
        "S2-4",
    ),
    CifraDeTiempo(
        "RNF-15 (cuatro opciones)",
        "scripts/_salida_rnf15.json",
        "mediana_opciones_s",
        "uv run python scripts/medir_rnf15.py",
        "S2-4",
    ),
)


def evaluar_reglas_en_ers(texto_ers: str | None) -> tuple[Estado, str]:
    """S2-REGLAS: la fila de RF-74 de la ERS nombra R13 y R14 (las reglas externas de S2)."""
    if texto_ers is None:
        return Estado.PENDIENTE, "falta docs/ERS.md"
    fila = re.search(rf"^\|\s*RF{GUION}74\s*\|[^\n]*", texto_ers, re.MULTILINE)
    if fila is None:
        return Estado.FALLA, "la ERS no define RF-74"
    faltan = [regla for regla in ("R13", "R14") if regla not in fila.group(0)]
    if faltan:
        return Estado.FALLA, "la fila de RF-74 no nombra " + ", ".join(faltan)
    return Estado.OK, "RF-74 define R13 y R14 en la ERS"


def evaluar_expedientes(texto: str | None) -> tuple[Estado, str]:
    """S2-EXPEDIENTES: la bitácora tiene un encabezado por expediente de `core/` de S2."""
    if texto is None:
        return Estado.PENDIENTE, "falta docs/bitacora/2026-10-silice-s2-expedientes.md"
    faltan = [
        e
        for e in EXPEDIENTES
        if not re.search(rf"^#{{2,4}}\s+{e.replace('-', GUION)}\b", texto, re.MULTILINE)
    ]
    if faltan:
        return Estado.FALLA, "la bitacora no trae el expediente " + ", ".join(faltan)
    return Estado.OK, "expedientes escritos: " + ", ".join(EXPEDIENTES)


def evaluar_memorias_de_s1(existe_etiqueta: bool, diff: str | None) -> tuple[Estado, str]:
    """S2-REG-S1: `git diff v0.6.0..HEAD` vacío sobre las cuatro memorias de S1 (no se editan)."""
    if not existe_etiqueta:
        return Estado.PENDIENTE, f"falta la etiqueta {ETIQUETA_S1}: S1 aun no se cerro"
    if diff is None:
        return Estado.PENDIENTE, "git diff no devolvio evidencia"
    if diff.strip():
        return Estado.FALLA, "las memorias de S1 cambiaron desde v0.6.0:\n" + diff.strip()
    return Estado.OK, f"las memorias de S1 no cambiaron desde {ETIQUETA_S1}"


def evaluar_base_070(carpeta: Path) -> tuple[Estado, str]:
    """S2-BASE-070: `ficha.json` de la etiqueta v0.7.0 y la huella SHA-256 de cada base."""
    ruta_ficha = carpeta / "ficha.json"
    if not ruta_ficha.is_file():
        return Estado.PENDIENTE, "la base de prueba 0.7.0 se genera desde la etiqueta v0.7.0"
    ficha = json.loads(ruta_ficha.read_text(encoding="utf-8"))
    if (ficha.get("version"), ficha.get("etiqueta")) != ("0.7.0", "v0.7.0"):
        return Estado.FALLA, f"la ficha dice {ficha.get('version')!r} / {ficha.get('etiqueta')!r}"
    bases = ficha.get("bases") or {}
    if "s2.db" not in bases:
        return Estado.FALLA, "la ficha no trae la base s2.db (OB-S2 con su decision)"
    distintas = [
        nombre
        for nombre, datos in sorted(bases.items())
        if not (carpeta / nombre).is_file()
        or hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest() != datos["sha256_base"]
    ]
    if distintas:
        return Estado.FALLA, "bases ausentes o distintas de su ficha: " + ", ".join(distintas)
    return Estado.OK, "base de prueba 0.7.0 con ficha: " + ", ".join(sorted(bases))


def _orden_memoria(memoria: str, criterio: tuple[str, ...]) -> bool | None:
    """Antes de que exista el código, basta que la memoria esté versionada."""
    if not (RAIZ / criterio[-1]).exists():
        return True if _primer_commit(f"tests/fixtures/memorias/{memoria}") else None
    return _ordenar_memoria(memoria, criterio)


def _memorias(_ctx: Contexto) -> tuple[Estado, str]:
    presentes = {m: (RUTA_MEMORIAS / m).is_file() for m in MEMORIAS_S2}
    presentes[Path(XLSX_OB_S2).name] = (RAIZ / XLSX_OB_S2).is_file()
    antes = {m: _orden_memoria(m, c) for m, c in MEMORIAS_S2.items()}
    antes[Path(XLSX_OB_S2).name] = True if presentes[Path(XLSX_OB_S2).name] else None
    codigo = any((RAIZ / c[-1]).exists() for c in MEMORIAS_S2.values())
    return evaluar_s2_memorias(presentes, antes, codigo_existe=codigo)


def _reglas(_ctx: Contexto) -> tuple[Estado, str]:
    ers = RAIZ / "docs" / "ERS.md"
    return evaluar_reglas_en_ers(ers.read_text(encoding="utf-8") if ers.is_file() else None)


def _expedientes(_ctx: Contexto) -> tuple[Estado, str]:
    existe = RUTA_EXPEDIENTES.is_file()
    return evaluar_expedientes(RUTA_EXPEDIENTES.read_text(encoding="utf-8") if existe else None)


def _memorias_de_s1(_ctx: Contexto) -> tuple[Estado, str]:
    if not _referencia_existe(ETIQUETA_S1):
        return evaluar_memorias_de_s1(False, None)
    resultado = _git("diff", "--stat", f"{ETIQUETA_S1}..HEAD", "--", *MEMORIAS_DE_S1)
    diff = resultado.stdout if resultado is not None and resultado.returncode == 0 else None
    return evaluar_memorias_de_s1(True, diff)


def _base_070(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_base_070(CARPETA_BASE_070)


PARTE = Parte(
    nombre="S2 presupuesto vivo: valuaciones, valor ganado, alertas y recuperacion",
    requisitos={"S2-0": REQUISITOS_S2},
    pares_tdd=PARES_S2,
    cifras=CIFRAS_S2,
    comprobaciones=(
        Comprobacion("S2-MEM", "Memoria OB-S2 y su XLSX antes del codigo", "S2-0", _memorias),
        Comprobacion("S2-REGLAS", "La ERS define R13 y R14", "S2-0", _reglas),
        Comprobacion("S2-EXPEDIENTES", "Expedientes SL-E4 a SL-E6 escritos", "S2-0", _expedientes),
        Comprobacion("S2-REG-S1", "Memorias de S1 intactas desde v0.6.0", "S2-0", _memorias_de_s1),
        Comprobacion("S2-BASE-070", "Base de prueba 0.7.0 con su ficha", "S2-5", _base_070),
    ),
)
