"""Cada módulo de `aplicacion/` se puede importar como el primero de un proceso.

Línea vial de la prueba de punta a punta (2026-11-13): `import aplicacion.hoja_vial` en un proceso
nuevo fallaba por el ciclo `hoja_vial` → `elaboracion` → `hoja_edicion` → `hoja_vista` →
`hoja_vial`; el servidor y las pruebas no lo veían porque importaban antes `hoja_edicion`. Un
guion importa cada módulo con `aplicacion` recién descargada de `sys.modules` (lo de fuera, como
`core`, sigue cargado: los ciclos que importan aquí son internos) y dice cuáles fallan.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

GUION = """
import importlib, pkgutil, sys, traceback
import aplicacion
nombres = sorted(m.name for m in pkgutil.iter_modules(aplicacion.__path__, "aplicacion."))
fallan = []
for nombre in nombres:
    for cargado in [m for m in sys.modules if m == "aplicacion" or m.startswith("aplicacion.")]:
        del sys.modules[cargado]
    try:
        importlib.import_module(nombre)
    except Exception as error:
        fallan.append(f"{nombre}: {type(error).__name__}: {error}")
print("\\n".join(fallan))
"""


def test_cada_modulo_de_aplicacion_se_importa_primero_sin_ciclos() -> None:
    salida = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", GUION],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
        check=True,
    )
    assert salida.stdout.strip() == "", salida.stdout
