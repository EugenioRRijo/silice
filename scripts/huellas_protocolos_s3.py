"""Escribe `docs/protocolos_s3.json`: la huella SHA-256 de los protocolos de S3 (spec S3 §13.5).

Se corre UNA vez, al cerrar S3-0, cuando el texto de los dos protocolos y de la lista congelada ya
no va a cambiar. Después de Med no se vuelve a correr: la meta (`S3-M1`) compara el texto con esta
huella y falla si cambió. Un cambio de fondo es una versión 2 del protocolo, con su huella nueva.

    uv run python scripts/huellas_protocolos_s3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_silice_s3 import PROTOCOLOS, RUTA_HUELLAS, huella_de  # noqa: E402


def calcular(raiz: Path = RAIZ) -> dict:
    return {
        "algoritmo": "sha256",
        "protocolos": {relativa: huella_de(raiz / relativa) for relativa in PROTOCOLOS},
    }


def main() -> int:
    datos = calcular()
    RUTA_HUELLAS.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for relativa, huella in datos["protocolos"].items():
        print(f"{huella}  {relativa}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
