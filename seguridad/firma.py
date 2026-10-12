"""Firma Ed25519 por empresa, huella legible y archivos firmados (spec S3 §7; maestro §4.4).

Nada de criptografía propia: `cryptography` genera, firma y verifica; aquí solo se fijan los
**dominios** (prefijos) de lo que se firma y la forma de los archivos:

* paquete: `b"silice-paquete-v1\\0"` + los bytes exactos de `manifiesto.json`;
* aviso de revocación: `b"silice-revocacion-v1\\0"` + el JSON canónico del aviso sin su firma.

Una firma de un dominio nunca vale en el otro (RV-16). La huella corta son los primeros 100 bits
del SHA-256 de la clave pública en el alfabeto de Crockford (sin I, L, O ni U), en cinco grupos
de cuatro: sirve solo para compararla por teléfono; toda búsqueda interna usa la clave completa.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from seguridad.json_estricto import JsonRechazado, leer_json

DOMINIO_PAQUETE = b"silice-paquete-v1\0"
DOMINIO_REVOCACION = b"silice-revocacion-v1\0"
ALFABETO_HUELLA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
FORMATO_CLAVE = "silice-clave"
FORMATO_REVOCACION = "silice-revocacion"
EXTENSION_CLAVE = ".silice-clave"
BITS_HUELLA_CORTA = 100


@dataclass(frozen=True, slots=True)
class ParDeClaves:
    privada: bytes  # 32 B crudos
    publica: bytes  # 32 B crudos


@dataclass(frozen=True, slots=True)
class ClavePublicaLeida:
    """Lo que trae un archivo `.silice-clave`. La huella se calcula; la declarada se compara."""

    nombre: str
    rif: str
    publica: bytes
    huella: str  # completa, calculada por el sistema
    huella_corta: str  # la que se compara por teléfono, calculada por el sistema
    huella_corta_declarada: str  # la que trae el archivo

    @property
    def huella_coincide(self) -> bool:
        return self.huella_corta == self.huella_corta_declarada


def huella_completa(publica: bytes) -> str:
    """SHA-256 (64 hex) de la clave pública cruda: la huella que usa todo el sistema."""
    return hashlib.sha256(publica).hexdigest()


def huella_corta(publica: bytes) -> str:
    """`K7QF-M9XR-A2PT-W4HN-C8DV`: 100 bits en 20 símbolos de 5 bits, en 5 grupos de 4."""
    entero = int.from_bytes(hashlib.sha256(publica).digest(), "big") >> (256 - BITS_HUELLA_CORTA)
    simbolos = [
        ALFABETO_HUELLA[(entero >> (5 * (19 - i))) & 31] for i in range(BITS_HUELLA_CORTA // 5)
    ]
    texto = "".join(simbolos)
    return "-".join(texto[i : i + 4] for i in range(0, len(texto), 4))


def normalizar_huella_corta(texto: str) -> str:
    """La huella corta tecleada: mayúsculas, sin espacios y con los guiones en su lugar."""
    limpia = "".join(c for c in texto.upper() if c.isalnum())
    if len(limpia) != BITS_HUELLA_CORTA // 5 or any(c not in ALFABETO_HUELLA for c in limpia):
        raise ValueError("la huella corta son 20 caracteres (sin I, L, O ni U)")
    return "-".join(limpia[i : i + 4] for i in range(0, len(limpia), 4))


def generar_par() -> ParDeClaves:
    privada = Ed25519PrivateKey.generate()
    return ParDeClaves(
        privada=privada.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        ),
        publica=privada.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ),
    )


def publica_de(privada: bytes) -> bytes:
    return (
        Ed25519PrivateKey.from_private_bytes(privada)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )


def firmar(privada: bytes, dominio: bytes, mensaje: bytes) -> bytes:
    """Firma `dominio + mensaje`. Ed25519 es determinista: el mismo par da la misma firma."""
    return Ed25519PrivateKey.from_private_bytes(privada).sign(dominio + mensaje)


def verificar(publica: bytes, dominio: bytes, mensaje: bytes, firma: bytes) -> bool:
    """True solo si `firma` es de `publica` sobre `dominio + mensaje`. Nunca lanza por la firma:
    una vacía, truncada o de otro dominio es False."""
    try:
        Ed25519PublicKey.from_public_bytes(publica).verify(firma, dominio + mensaje)
    except (InvalidSignature, ValueError):
        return False
    return True


def _canonico(objeto: dict) -> bytes:
    return json.dumps(objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def exportar_clave_publica(nombre: str, rif: str, publica: bytes, ahora: datetime) -> bytes:
    """El archivo `.silice-clave`: nombre, RIF, clave pública (base64), huella y fecha."""
    return _canonico(
        {
            "formato": FORMATO_CLAVE,
            "version_formato": 1,
            "nombre": nombre,
            "rif": rif,
            "clave_publica": base64.b64encode(publica).decode("ascii"),
            "huella": huella_corta(publica),
            "fecha": ahora.isoformat(timespec="seconds"),
        }
    )


def leer_clave_publica(datos: bytes) -> ClavePublicaLeida:
    """Lee un `.silice-clave` con el lector estricto. La huella es la que CALCULA el sistema."""
    documento = leer_json(datos)
    if not isinstance(documento, dict) or documento.get("formato") != FORMATO_CLAVE:
        raise JsonRechazado("no es un archivo de clave publica de Silice")
    try:
        publica = base64.b64decode(documento["clave_publica"], validate=True)
        nombre, rif = str(documento["nombre"]).strip(), str(documento.get("rif", "")).strip()
    except (KeyError, ValueError) as error:
        raise JsonRechazado("archivo de clave publica incompleto o dañado") from error
    if len(publica) != 32 or not nombre:
        raise JsonRechazado("la clave publica debe ser Ed25519 de 32 bytes y llevar nombre")
    return ClavePublicaLeida(
        nombre=nombre,
        rif=rif,
        publica=publica,
        huella=huella_completa(publica),
        huella_corta=huella_corta(publica),
        huella_corta_declarada=str(documento.get("huella", "")),
    )


def crear_aviso_revocacion(privada: bytes, motivo: str, ahora: datetime) -> bytes:
    """El aviso de revocación firmado con la propia clave (dominio de revocación)."""
    publica = publica_de(privada)
    cuerpo = {
        "formato": FORMATO_REVOCACION,
        "version_formato": 1,
        "huella": huella_completa(publica),
        "clave_publica": base64.b64encode(publica).decode("ascii"),
        "motivo": motivo,
        "fecha": ahora.isoformat(timespec="seconds"),
    }
    firma = firmar(privada, DOMINIO_REVOCACION, _canonico(cuerpo))
    return _canonico({**cuerpo, "firma": base64.b64encode(firma).decode("ascii")})


def leer_aviso_revocacion(datos: bytes) -> tuple[bytes, str, bool]:
    """`(clave pública, motivo, firma válida)`. La validez se comprueba con la clave que TRAE el
    aviso; el llamador además exige que sea una clave que tiene registrada."""
    documento = leer_json(datos)
    if not isinstance(documento, dict) or documento.get("formato") != FORMATO_REVOCACION:
        raise JsonRechazado("no es un aviso de revocacion de Silice")
    try:
        publica = base64.b64decode(documento["clave_publica"], validate=True)
        firma = base64.b64decode(documento["firma"], validate=True)
    except (KeyError, ValueError) as error:
        raise JsonRechazado("aviso de revocacion incompleto o dañado") from error
    cuerpo = {k: v for k, v in documento.items() if k != "firma"}
    valida = verificar(publica, DOMINIO_REVOCACION, _canonico(cuerpo), firma)
    return publica, str(documento.get("motivo", "")), valida
