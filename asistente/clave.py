"""La clave de IA de la empresa (S4 §8.3, RNF-18 c). Se llama asi para no confundirla con la clave
de firma Ed25519 de S3: es la clave de API del proveedor de IA.

* La registra solo el administrador y solo desde un cliente del propio equipo (IP de bucle local):
  por la red local sin TLS viajaria en claro (RV-15).
* Se guarda con `keyring` (en Windows, el Administrador de credenciales) bajo el servicio
  `silice-ia` y el id de la empresa propia: POR USUARIO DE WINDOWS y fuera de los respaldos (RV-24).
* Respaldo si el almacen no esta disponible: se cifra con `seguridad.secretos` (Argon2id -> AES-GCM)
  con una contrasena propia; este modulo NO reimplementa el cifrado.
* Descifrada vive solo en la memoria del proceso (un atributo de ESTE objeto): nunca en
  `st.session_state`, en disco ni en variables de entorno. Se borra al desactivar o al cambiarla.
* La pantalla muestra solo los ultimos 4 caracteres; los registros la enmascaran.
"""

from __future__ import annotations

import base64
import binascii
import ipaddress
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

SERVICIO = "silice-ia"
ASOCIADO = "silice-ia-clave-v1:"
_PATRON_CLAVE = re.compile(r"sk-ant-[A-Za-z0-9_\-]+")
NO_ABRE_EL_RESPALDO = "La contraseña no abre el respaldo de la clave de IA."
#: Lo que da un respaldo que no se puede leer (JSON danado, campos ausentes o base64 roto).
_RESPALDO_ILEGIBLE = (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, binascii.Error)


class ClaveNoRegistrable(Exception):  # noqa: N818
    """No se pudo registrar o activar la clave; el mensaje es apto para mostrar."""


class AlmacenDeClaves(Protocol):
    def get_password(self, servicio: str, usuario: str) -> str | None: ...

    def set_password(self, servicio: str, usuario: str, clave: str) -> None: ...

    def delete_password(self, servicio: str, usuario: str) -> None: ...


class Secretos(Protocol):
    """La forma de `seguridad.secretos` (S3-1) que usa S4: el modulo mismo se inyecta.

    `cifrar` devuelve un `SecretoCifrado(kdf, sal, nonce, cifrado)`; `huella_publica` es el dato
    asociado del AES-GCM (aqui, el servicio mas la empresa). La contrasena la valida la politica
    de la clave de S3 (`exigir_contrasena_de_clave`).
    """

    SecretoCifrado: type
    #: La contrasena o el dato asociado no son los del cifrado (`cryptography`, reexportada).
    InvalidTag: type[Exception]

    def cifrar(self, secreto: bytes, contrasena: str, huella_publica: str) -> Any: ...

    def descifrar(self, cifrado: Any, contrasena: str, huella_publica: str) -> bytes: ...

    def exigir_contrasena_de_clave(self, contrasena: str) -> None: ...


def es_bucle_local(ip: str | None) -> bool:
    """True solo para una IP de bucle local (`127.0.0.0/8` o `::1`): la misma regla que
    `seguridad.red.es_local` (S3), que `asistente` no importa (maestro §3.1, RV-22)."""
    if not ip:
        return False
    try:
        return ipaddress.ip_address(ip.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def ultimos_cuatro(clave: str) -> str:
    return "…" + clave[-4:]


def enmascarar(texto: str) -> str:
    """Reemplaza toda clave de IA que aparezca en `texto` (registros, mensajes de error)."""
    return _PATRON_CLAVE.sub(lambda m: "sk-ant-…" + m.group(0)[-4:], texto)


class FiltroDeSecretos(logging.Filter):
    """Enmascara las claves en el mensaje de cada registro; se instala en los manejadores."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = enmascarar(record.getMessage())
        record.args = ()
        return True


def _es_error_de_almacen(error: Exception) -> bool:
    return any(c.__name__ == "KeyringError" for c in type(error).__mro__)


def _serializar(cifrado: Any) -> bytes:
    """El respaldo en disco: JSON con sal, nonce y cifrado en base64 (nunca la clave)."""
    datos = {
        "kdf": cifrado.kdf,
        "sal": base64.b64encode(cifrado.sal).decode(),
        "nonce": base64.b64encode(cifrado.nonce).decode(),
        "cifrado": base64.b64encode(cifrado.cifrado).decode(),
    }
    return json.dumps(datos, sort_keys=True).encode()


def _deserializar(secretos: Secretos, crudo: bytes) -> Any:
    datos = json.loads(crudo)
    return secretos.SecretoCifrado(
        datos["kdf"],
        base64.b64decode(datos["sal"]),
        base64.b64decode(datos["nonce"]),
        base64.b64decode(datos["cifrado"]),
    )


class ClaveDeIA:
    def __init__(
        self,
        *,
        almacen: AlmacenDeClaves,
        secretos: Secretos,
        ruta_respaldo: Path,
        es_local: Callable[[str | None], bool],
    ) -> None:
        self._almacen = almacen
        self._secretos = secretos
        self._ruta = ruta_respaldo
        self._es_local = es_local
        self._en_memoria: str | None = None

    def __repr__(self) -> str:  # nunca la clave
        return f"ClaveDeIA(activa={self._en_memoria is not None})"

    @property
    def vigente(self) -> str | None:
        """La clave descifrada, solo para construir el proveedor; nunca se muestra."""
        return self._en_memoria

    def mostrada(self) -> str | None:
        return None if self._en_memoria is None else ultimos_cuatro(self._en_memoria)

    def registrar(
        self,
        empresa_id: str,
        clave: str,
        *,
        ip_cliente: str | None,
        contrasena_respaldo: str | None = None,
    ) -> str:
        """Guarda la clave y la deja activa. Devuelve lo que la pantalla puede mostrar."""
        if not self._es_local(ip_cliente):
            raise ClaveNoRegistrable("La clave de IA solo se registra desde el propio equipo.")
        if not clave.strip():
            raise ClaveNoRegistrable("Escriba la clave de IA de la empresa.")
        try:
            self._almacen.set_password(SERVICIO, empresa_id, clave)
            self._ruta.unlink(missing_ok=True)
        except Exception as error:  # noqa: BLE001
            if not _es_error_de_almacen(error):
                raise
            if not contrasena_respaldo:
                raise ClaveNoRegistrable(
                    "El almacen de credenciales del sistema no esta disponible: indique una "
                    "contrasena para guardar la clave cifrada."
                ) from None
            self._secretos.exigir_contrasena_de_clave(contrasena_respaldo)
            cifrado = self._secretos.cifrar(
                clave.encode(), contrasena_respaldo, ASOCIADO + empresa_id
            )
            self._ruta.write_bytes(_serializar(cifrado))
        self._en_memoria = clave
        return ultimos_cuatro(clave)

    def activar(self, empresa_id: str, contrasena_respaldo: str | None = None) -> None:
        """Carga la clave del almacen o del respaldo cifrado a la memoria del proceso."""
        clave: str | None = None
        try:
            clave = self._almacen.get_password(SERVICIO, empresa_id)
        except Exception as error:  # noqa: BLE001
            if not _es_error_de_almacen(error):
                raise
        if clave is None and self._ruta.exists():
            if not contrasena_respaldo:
                raise ClaveNoRegistrable("Escriba la contrasena de la clave de IA guardada.")
            cifrado = _deserializar(self._secretos, self._ruta.read_bytes())
            clave = self._secretos.descifrar(
                cifrado, contrasena_respaldo, ASOCIADO + empresa_id
            ).decode()
        if clave is None:
            raise ClaveNoRegistrable("No hay una clave de IA registrada para esta empresa.")
        self._en_memoria = clave

    def pide_contrasena(self, empresa_id: str) -> bool:
        """True si la clave no esta en memoria, no esta en el almacen (o este falla) y queda el
        respaldo cifrado: lo unico que la trae de vuelta es su contrasena."""
        if self._en_memoria is not None or not self._ruta.exists():
            return False
        try:
            return self._almacen.get_password(SERVICIO, empresa_id) is None
        except Exception as error:  # noqa: BLE001
            if not _es_error_de_almacen(error):
                raise
            return True

    def reactivar(self, empresa_id: str, contrasena: str, *, ip_cliente: str | None) -> str:
        """Carga la clave desde el respaldo cifrado con su contrasena; solo desde el propio equipo.

        La contrasena erronea (`InvalidTag`) y el respaldo ilegible dan un mensaje fijo, sin la
        contrasena ni traza; la contrasena vacia, el de `activar`. Devuelve lo que se puede mostrar.
        """
        if not self._es_local(ip_cliente):
            raise ClaveNoRegistrable("La clave de IA solo se reactiva desde el propio equipo.")
        try:
            self.activar(empresa_id, contrasena)
        except (self._secretos.InvalidTag, *_RESPALDO_ILEGIBLE):
            raise ClaveNoRegistrable(NO_ABRE_EL_RESPALDO) from None
        mostrada = self.mostrada()  # activar la deja en memoria o lanza
        if mostrada is None:
            raise ClaveNoRegistrable("No hay una clave de IA registrada para esta empresa.")
        return mostrada

    def hay_guardada(self, empresa_id: str) -> bool:
        """True si hay una clave en el almacen o en el respaldo cifrado; no la deja en memoria."""
        if self._ruta.exists():
            return True
        try:
            return self._almacen.get_password(SERVICIO, empresa_id) is not None
        except Exception as error:  # noqa: BLE001
            if not _es_error_de_almacen(error):
                raise
            return False

    def desactivar(self) -> None:
        self._en_memoria = None

    def olvidar(self, empresa_id: str) -> None:
        """Borra la clave del almacen, del respaldo y de la memoria (cambiarla = registrar otra)."""
        self._en_memoria = None
        self._ruta.unlink(missing_ok=True)
        try:
            self._almacen.delete_password(SERVICIO, empresa_id)
        except Exception as error:  # noqa: BLE001
            if not _es_error_de_almacen(error) and type(error).__name__ != "PasswordDeleteError":
                raise


def almacen_del_sistema() -> Any:
    """El modulo `keyring` (cumple `AlmacenDeClaves`); importacion diferida del extra `ia`."""
    import keyring

    return keyring
