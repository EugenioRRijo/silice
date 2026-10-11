"""Descarga el modelo de similitud de partidas (I2) a la cache local de Hugging Face.

La suite corre sin red (`HF_HUB_OFFLINE=1` y la guardia de `tests/conftest.py`; maestro §6.3,
RV-17): este es el unico paso que descarga, una vez por equipo, antes de pytest. La CI lo corre en
su propio paso, con cache. En el producto, el instalador completo trae el modelo (S5 §10.2).

Uso: `uv run python scripts/descargar_modelo.py`.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from ml.normalization import MODELO_POR_DEFECTO  # noqa: E402


def descargar(
    nombre: str = MODELO_POR_DEFECTO, cargar: Callable[[str], object] | None = None
) -> object:
    """Carga (y, si falta, descarga) el modelo `nombre`; `cargar` reemplaza al cargador real."""
    if cargar is None:
        # Hugging Face lee la variable al importarse: se fija antes de importar.
        os.environ["HF_HUB_OFFLINE"] = "0"
        from sentence_transformers import SentenceTransformer

        cargar = SentenceTransformer
    return cargar(nombre)


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    descargar()
    print(f"modelo de similitud en la cache local: {MODELO_POR_DEFECTO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
