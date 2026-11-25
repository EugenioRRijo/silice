"""Los archivos auxiliares de SQLite no se suben (NORMAS §1).

Con el servidor andando, SQLite escribe al lado de cada base un `-wal` y un `-shm` (o un `-journal`)
con lo último que guardó: cuentas, casos o datos de una obra. `*.db` ya estaba ignorado y estos
no; el 2026-11-25 aparecieron sueltos en `data/` después de una prueba en el navegador.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "ruta",
    [
        "data/instalacion.db-wal",
        "data/instalacion.db-shm",
        "data/casos/obra.db-wal",
        "otra/carpeta/base.db-journal",
    ],
)
def test_los_auxiliares_de_sqlite_quedan_ignorados(ruta: str):
    resultado = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", ruta],
        cwd=RAIZ,
        capture_output=True,
        check=False,
    )
    assert resultado.returncode == 0, f"«{ruta}» no está ignorado en .gitignore"
