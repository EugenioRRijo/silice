"""Comprueba un instalador de Sílice sin tener Sílice (spec S5 §10.4; RP10-10).

    uv run --with cryptography verificar_sumas.py Silice-1.0.0.exe SHA256SUMS SHA256SUMS.ed25519 \
        --publica <clave pública del proyecto, 64 caracteres hexadecimales>

Comprueba (1) la firma Ed25519 de SHA256SUMS con la clave pública que usted pasa y (2) la huella
SHA-256 del instalador contra SHA256SUMS. Imprime la huella de la clave usada: debe ser la del
manual de instalación y la de la tesis. Sale con 1 si algo no cuadra.
"""

import argparse
import hashlib
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DOMINIO = b"silice-sumas-v1\0"


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("exe", type=Path)
    analizador.add_argument("sumas", type=Path)
    analizador.add_argument("firma", type=Path)
    analizador.add_argument("--publica", required=True, help="clave pública en hexadecimal")
    argumentos = analizador.parse_args()
    publica = bytes.fromhex(argumentos.publica)
    datos = argumentos.sumas.read_bytes()
    print(f"Huella de la clave usada: {hashlib.sha256(publica).hexdigest()}")
    try:
        Ed25519PublicKey.from_public_bytes(publica).verify(
            argumentos.firma.read_bytes(), DOMINIO + datos
        )
    except (InvalidSignature, ValueError):
        print("FIRMA NO VÁLIDA: NO INSTALE este archivo.", file=sys.stderr)
        return 1
    esperada = None
    for linea in datos.decode("utf-8").splitlines():
        huella, _, nombre = linea.partition(" ")
        if nombre.lstrip(" *") == argumentos.exe.name:
            esperada = huella
    if esperada is None:
        print(f"{argumentos.exe.name} no figura en SHA256SUMS: NO INSTALE.", file=sys.stderr)
        return 1
    if hashlib.sha256(argumentos.exe.read_bytes()).hexdigest() != esperada:
        print("La huella del instalador NO coincide con SHA256SUMS: NO INSTALE.", file=sys.stderr)
        return 1
    print(f"VERIFICADO: {argumentos.exe.name} coincide con SHA256SUMS firmado por esa clave.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
