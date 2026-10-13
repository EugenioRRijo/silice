"""Dobles de `keyring` y de `seguridad.secretos` para las pruebas de la clave de IA (S4 §8.3).

`SecretosFalsos` sigue la interfaz REAL de `seguridad.secretos` (bitacora 0.9.0, T13: `cifrar`
devuelve un `SecretoCifrado`; `descifrar(cifrado, contrasena, huella_publica)`; la contrasena pasa
por `exigir_contrasena_de_clave`), no la supuesta por el plan. Es reversible y comprueba la
contrasena y el dato asociado para probar el flujo: NO es criptografia. La prueba con el modulo
real esta en `tests/integration/test_clave_ia_secretos.py`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


class KeyringError(Exception):
    """Con el nombre de la base de `keyring.errors`: `asistente.clave` la detecta por nombre."""


class PasswordDeleteError(KeyringError):
    """Como `keyring.errors.PasswordDeleteError`: borrar lo que no estaba."""


class AlmacenFalso:
    """El almacen de credenciales en memoria; `cae=True` simula el almacen ausente."""

    def __init__(self, *, cae: bool = False) -> None:
        self.datos: dict[tuple[str, str], str] = {}
        self.cae = cae
        self.lecturas = 0

    def _revisar(self) -> None:
        if self.cae:
            raise KeyringError("sin almacen")

    def get_password(self, servicio: str, usuario: str) -> str | None:
        self._revisar()
        self.lecturas += 1
        return self.datos.get((servicio, usuario))

    def set_password(self, servicio: str, usuario: str, clave: str) -> None:
        self._revisar()
        self.datos[(servicio, usuario)] = clave

    def delete_password(self, servicio: str, usuario: str) -> None:
        self._revisar()
        if (servicio, usuario) not in self.datos:
            raise PasswordDeleteError("no habia nada que borrar")
        del self.datos[(servicio, usuario)]


class AlmacenRoto(AlmacenFalso):
    """Un almacen que falla con un error que NO es de `keyring` (no debe tragarse)."""

    def get_password(self, servicio: str, usuario: str) -> str | None:
        raise RuntimeError("fallo inesperado del almacen")

    def set_password(self, servicio: str, usuario: str, clave: str) -> None:
        raise RuntimeError("fallo inesperado del almacen")


@dataclass(frozen=True, slots=True)
class SecretoCifradoFalso:
    kdf: str
    sal: bytes
    nonce: bytes
    cifrado: bytes


class ContrasenaCorta(ValueError):  # noqa: N818
    """La politica del doble: al menos 12 caracteres, como `seguridad.secretos.MINIMO_CLAVE`."""


def _sello(contrasena: str, huella_publica: str) -> bytes:
    return hashlib.sha256(f"{contrasena}\x00{huella_publica}".encode()).digest()


class SecretosFalsos:
    """La forma de `seguridad.secretos` que usa `asistente.clave` (el modulo se inyecta)."""

    SecretoCifrado = SecretoCifradoFalso

    def __init__(self) -> None:
        self.politica_vista: list[str] = []

    def exigir_contrasena_de_clave(self, contrasena: str) -> None:
        self.politica_vista.append(contrasena)
        if len(contrasena) < 12:
            raise ContrasenaCorta("La contraseña de la clave debe tener al menos 12 caracteres.")

    def cifrar(self, secreto: bytes, contrasena: str, huella_publica: str) -> SecretoCifradoFalso:
        return SecretoCifradoFalso(
            "falso",
            _sello(contrasena, huella_publica),
            b"\x00" * 12,
            bytes(b ^ 0x5A for b in secreto),
        )

    def descifrar(
        self, cifrado: SecretoCifradoFalso, contrasena: str, huella_publica: str
    ) -> bytes:
        if cifrado.sal != _sello(contrasena, huella_publica):
            raise ValueError("contrasena erronea")
        return bytes(b ^ 0x5A for b in cifrado.cifrado)
