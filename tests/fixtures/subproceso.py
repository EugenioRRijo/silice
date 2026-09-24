"""Importar modulos en un proceso Python limpio (INV-023 e INV-024): una sola ayuda para las
pruebas que comprueban que importar no tiene efectos ni arrastra extras."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

#: Importa cada modulo de argv y escribe en stdout, uno por linea, los de `sys.modules` al final.
_CODIGO = (
    "import importlib, sys\n"
    "for nombre in sys.argv[1:]:\n"
    "    importlib.import_module(nombre)\n"
    "print('\\n'.join(sorted(sys.modules)))\n"
)


def importar_en_limpio(modulos: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Importa `modulos` en un proceso nuevo con `cwd` como directorio de trabajo y la raiz del
    repositorio en `PYTHONPATH`. No lanza si el proceso falla: el llamador afirma `returncode`."""
    return subprocess.run(
        [sys.executable, "-c", _CODIGO, *modulos],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(RAIZ)},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def modulos_cargados(salida: subprocess.CompletedProcess[str]) -> set[str]:
    """Los nombres de `sys.modules` que el proceso limpio dejo cargados."""
    return set(salida.stdout.split())
