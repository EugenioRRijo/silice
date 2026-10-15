"""Firma Ed25519 de `SHA256SUMS` con la clave del proyecto (spec S5 §10.4; RV-16).

El instalador no lleva firma de código (RS5-10): lleva `SHA256SUMS` (huella de cada archivo del
release) y `SHA256SUMS.ed25519`, la firma de esos bytes exactos con la clave del proyecto, con
separación de dominio (`b"silice-sumas-v1\\0"`, como `silice-paquete-v1\\0` en S3: una firma de un
tipo no vale como la de otro). La privada vive cifrada (Argon2id + AES-GCM, `seguridad.secretos`)
fuera del repositorio y de la CI; el repositorio solo tiene la pública (`clave_proyecto.pub`).
No se programa criptografía propia: todo es `cryptography`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from operacion import config

DOMINIO = b"silice-sumas-v1\0"
ASOCIADO = b"silice-clave-proyecto-v1"
FORMATO_CLAVE = "silice-clave-proyecto"
MIN_CONTRASENA = 12
RUTA_PUBLICA = config.RAIZ / "operacion" / "clave_proyecto.pub"
_LINEA = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")


def generar_par() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def bytes_publicos(privada: Ed25519PrivateKey) -> bytes:
    return privada.public_key().public_bytes_raw()


def huella(publica: bytes) -> str:
    return hashlib.sha256(publica).hexdigest()


def huella_agrupada(publica: bytes) -> str:
    h = huella(publica)
    return " ".join(h[i : i + 8] for i in range(0, 64, 8))


def formatear_sumas(entradas: Mapping[str, str]) -> bytes:
    """Líneas `<sha256>  <nombre>` (formato de `sha256sum`), ordenadas por nombre, solo LF."""
    return "".join(f"{entradas[n]}  {n}\n" for n in sorted(entradas)).encode("utf-8")


def parsear_sumas(datos: bytes) -> dict[str, str]:
    if b"\r" in datos:
        raise ValueError(
            "SHA256SUMS tiene saltos de línea de Windows (CRLF): no es el archivo firmado"
        )
    entradas: dict[str, str] = {}
    for numero, linea in enumerate(datos.decode("utf-8").splitlines(), start=1):
        if not linea:
            continue
        coincidencia = _LINEA.match(linea)
        if coincidencia is None:
            raise ValueError(f"SHA256SUMS, línea {numero}: no tiene la forma «<sha256>  <nombre>»")
        huella_, nombre = coincidencia.groups()
        if "/" in nombre or "\\" in nombre or nombre in {".", ".."}:
            raise ValueError(f"SHA256SUMS, línea {numero}: nombre sospechoso {nombre!r}")
        if nombre in entradas:
            raise ValueError(f"SHA256SUMS, línea {numero}: {nombre!r} repetido")
        entradas[nombre] = huella_
    return entradas


def firmar(sumas: bytes, privada: Ed25519PrivateKey) -> bytes:
    return privada.sign(DOMINIO + sumas)


def verificar(sumas: bytes, firma: bytes, publica: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(publica).verify(firma, DOMINIO + sumas)
    except (InvalidSignature, ValueError):
        return False
    return True


def verificar_instalador(exe: Path, sumas: bytes, firma: bytes, publica: bytes) -> tuple[bool, str]:
    """Firma de `SHA256SUMS` y huella del instalador, con la causa de cada fallo."""
    if not verificar(sumas, firma, publica):
        return (
            False,
            "La firma de SHA256SUMS no es válida con la clave del proyecto: no instale este "
            "archivo.",
        )
    try:
        entradas = parsear_sumas(sumas)
    except ValueError as error:
        return False, f"SHA256SUMS no tiene el formato esperado: {error}"
    if exe.name not in entradas:
        return False, f"{exe.name} no figura en SHA256SUMS: no instale este archivo."
    if hashlib.sha256(exe.read_bytes()).hexdigest() != entradas[exe.name]:
        return (
            False,
            f"La huella de {exe.name} no coincide con SHA256SUMS: el archivo cambió. "
            "No lo instale.",
        )
    return True, (
        f"VERIFICADO: {exe.name} coincide con SHA256SUMS firmado por la clave del proyecto "
        f"(huella de la clave {huella(publica)})."
    )


def guardar_privada(privada: Ed25519PrivateKey, contrasena: str, ruta: Path) -> None:
    from seguridad import secretos

    if len(contrasena) < MIN_CONTRASENA:
        raise ValueError(
            f"la contraseña de la clave debe tener al menos {MIN_CONTRASENA} caracteres"
        )
    publica = bytes_publicos(privada).hex()
    sobre = secretos.cifrar(
        privada.private_bytes_raw(), contrasena, asociado=ASOCIADO + publica.encode()
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(
            {
                "formato": FORMATO_CLAVE,
                "version": 1,
                "publica": publica,
                "sobre": base64.b64encode(sobre).decode("ascii"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def cargar_privada(ruta: Path, contrasena: str) -> Ed25519PrivateKey:
    from seguridad import secretos

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos.get("formato") != FORMATO_CLAVE:
        raise ValueError(f"{ruta.name} no es una clave del proyecto de Sílice")
    semilla = secretos.descifrar(
        base64.b64decode(datos["sobre"]), contrasena, asociado=ASOCIADO + datos["publica"].encode()
    )
    return Ed25519PrivateKey.from_private_bytes(semilla)


def leer_publica(ruta: Path | None = None) -> bytes:
    destino = ruta if ruta is not None else RUTA_PUBLICA
    texto = destino.read_text(encoding="utf-8").strip()
    try:
        publica = bytes.fromhex(texto)
    except ValueError:
        raise ValueError(f"{destino.name} no es una clave pública en hexadecimal") from None
    if len(publica) != 32:
        raise ValueError(
            f"{destino.name}: una clave pública Ed25519 mide 32 bytes, no {len(publica)}"
        )
    return publica
