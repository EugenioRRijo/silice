"""Secretos cifrados con contraseña: Argon2id -> AES-GCM (maestro §4.4, RV-13; spec S3 §7.1).

Un solo módulo para todo secreto de la instalación que se guarda cifrado con una contraseña: la
clave de firma de la empresa (S3) y la clave de IA de la empresa (S4, que lo importa). No hay
criptografía propia: se componen dos primitivas de las bibliotecas.

    clave de 32 B = Argon2id(contraseña, sal de 16 B; m >= 64 MiB, t >= 3)
    cifrado       = AES-GCM(clave, nonce de 12 B, secreto, dato asociado)
    dato asociado = b"silice-clave-v1" + huella pública (UTF-8)

El dato asociado ata el cifrado a la huella de la clave pública: un cifrado movido a otra fila
no descifra. Una contraseña errónea (o un dato asociado distinto) da `InvalidTag`; el llamador
la convierte en un mensaje sin traza.
"""

from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass
from typing import Any

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

__all__ = [
    "InvalidTag",
    "MINIMO_CLAVE",
    "ContrasenaRechazada",
    "ParametrosKdf",
    "SecretoCifrado",
    "cifrar",
    "descifrar",
    "exigir_contrasena_de_clave",
]

PREFIJO_DATO_ASOCIADO = b"silice-clave-v1"
TAMANO_SAL = 16
TAMANO_NONCE = 12
TAMANO_CLAVE = 32
#: Minimo de caracteres de la contraseña de una clave (spec S3 §7.1).
MINIMO_CLAVE = 12
MAXIMO_CLAVE = 128
#: Mínimos de S3 §7.1 para Argon2id (m >= 64 MiB, t >= 3): por debajo no se cifra.
MEMORIA_MINIMA_KIB = 65536
PASADAS_MINIMAS = 3

#: Lista corta de contraseñas comunes que se rechazan (minusculas, sin espacios en los bordes).
#: SUPUESTO_DECLARADO: no es un diccionario completo; es el filtro minimo de S3 §7.1.
CONTRASENAS_COMUNES = frozenset(
    {
        "password", "password1", "password12", "password123", "passw0rd1234", "contrasena",
        "contrasena1", "contrasena12", "contrasena123", "contraseña", "contraseña1",
        "contraseña12", "contraseña123", "123456", "1234567", "12345678", "123456789",
        "1234567890", "12345678901", "123456789012", "1234567890123", "0123456789",
        "qwerty", "qwertyuiop", "qwertyuiopas", "qwerty123456", "asdfghjkl", "asdfghjklñ",
        "abcdefghijkl", "abc123456789", "iloveyou", "letmein", "welcome", "welcome123",
        "admin", "admin123", "administrador", "administrador1", "admin1234567",
        "silice", "silice123", "silice2026", "silice123456", "arenia", "arenia123",
        "venezuela", "venezuela123", "caracas123", "11111111", "111111111111",
        "000000000000", "aaaaaaaaaaaa", "changeme", "changeme123", "cambiame",
    }
)


class ContrasenaRechazada(ValueError):  # noqa: N818
    """La contraseña no cumple la política; el mensaje dice cuál regla y no la repite."""


@dataclass(frozen=True, slots=True)
class ParametrosKdf:
    """Parámetros de Argon2id con que se derivó una clave; se guardan junto al cifrado."""

    memoria_kib: int = 65536
    pasadas: int = 3
    paralelismo: int = 4

    def __post_init__(self) -> None:
        if self.memoria_kib < MEMORIA_MINIMA_KIB or self.pasadas < PASADAS_MINIMAS:
            raise ValueError(
                "parametros de Argon2id por debajo del minimo (m >= 64 MiB, t >= 3)"
            )
        if self.paralelismo < 1:
            raise ValueError("el paralelismo de Argon2id debe ser >= 1")

    def a_json(self) -> str:
        return json.dumps(
            {"alg": "argon2id", "v": 19, "m": self.memoria_kib, "t": self.pasadas,
             "p": self.paralelismo},
            sort_keys=True,
        )

    @classmethod
    def de_json(cls, texto: str) -> ParametrosKdf:
        datos = json.loads(texto)
        if datos.get("alg") != "argon2id" or datos.get("v") != 19:
            raise ValueError("el cifrado no usa Argon2id version 19")
        return cls(datos["m"], datos["t"], datos["p"])


@dataclass(frozen=True, slots=True)
class SecretoCifrado:
    """Lo que se guarda: parámetros del KDF (JSON), sal, nonce y el cifrado con su etiqueta."""

    kdf: str
    sal: bytes
    nonce: bytes
    cifrado: bytes


def exigir_contrasena_de_clave(contrasena: str) -> None:
    """`ContrasenaRechazada` si mide menos de 12, más de 128 o está en la lista de comunes."""
    if len(contrasena) < MINIMO_CLAVE:
        raise ContrasenaRechazada(
            f"La contraseña de la clave debe tener al menos {MINIMO_CLAVE} caracteres."
        )
    if len(contrasena) > MAXIMO_CLAVE:
        raise ContrasenaRechazada(f"La contraseña de la clave admite hasta {MAXIMO_CLAVE}.")
    if contrasena.strip().casefold() in CONTRASENAS_COMUNES:
        raise ContrasenaRechazada("Esa contraseña es demasiado común; elija otra.")


def _derivar(contrasena: str, sal: bytes, parametros: ParametrosKdf) -> bytes:
    return hash_secret_raw(
        contrasena.encode("utf-8"),
        sal,
        time_cost=parametros.pasadas,
        memory_cost=parametros.memoria_kib,
        parallelism=parametros.paralelismo,
        hash_len=TAMANO_CLAVE,
        type=Type.ID,
    )


def _dato_asociado(huella_publica: str) -> bytes:
    return PREFIJO_DATO_ASOCIADO + huella_publica.encode("utf-8")


def cifrar(
    secreto: bytes,
    contrasena: str,
    huella_publica: str = "",
    parametros: ParametrosKdf | None = None,
    *,
    asociado: bytes | None = None,
) -> Any:
    """Cifra `secreto` con la contraseña. Sal y nonce nuevos en cada llamada."""
    parametros = parametros or ParametrosKdf()
    sal = secrets.token_bytes(TAMANO_SAL)
    nonce = secrets.token_bytes(TAMANO_NONCE)
    clave = _derivar(contrasena, sal, parametros)
    ad = asociado if asociado is not None else _dato_asociado(huella_publica)
    cifrado = AESGCM(clave).encrypt(nonce, secreto, ad)
    if asociado is not None:
        sobre_dict = {
            "kdf": parametros.a_json(),
            "sal": base64.b64encode(sal).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "cifrado": base64.b64encode(cifrado).decode("ascii"),
        }
        return json.dumps(sobre_dict, sort_keys=True).encode("utf-8")
    return SecretoCifrado(parametros.a_json(), sal, nonce, cifrado)


def descifrar(
    cifrado: Any,
    contrasena: str,
    huella_publica: str = "",
    *,
    asociado: bytes | None = None,
) -> bytes:
    """El secreto original; `InvalidTag` si la contraseña o la huella no son las del cifrado."""
    if isinstance(cifrado, (bytes, bytearray)):
        datos = json.loads(cifrado)
        parametros = ParametrosKdf.de_json(datos["kdf"])
        sal = base64.b64decode(datos["sal"])
        nonce = base64.b64decode(datos["nonce"])
        cuerpo = base64.b64decode(datos["cifrado"])
    else:
        parametros = ParametrosKdf.de_json(cifrado.kdf)
        sal = cifrado.sal
        nonce = cifrado.nonce
        cuerpo = cifrado.cifrado
    clave = _derivar(contrasena, sal, parametros)
    ad = asociado if asociado is not None else _dato_asociado(huella_publica)
    return AESGCM(clave).decrypt(nonce, cuerpo, ad)
