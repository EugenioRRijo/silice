"""¿El cliente es el propio equipo? (spec S3 §5.6; maestro §4.7, RV-15).

`es_local` acepta solo direcciones de bucle local. La IP la da `st.context.ip_address` (la
interfaz la entrega ya como `str | None`, ver `ui/sesion.py`). Si no hay IP, las operaciones
sensibles se permiten únicamente con la red local apagada: con la red encendida y sin IP, no.
El filtro de IP privadas NO es un control (un túnel o proxy local lo anula): el control real es
la sesión y la clave de API (S3 §12).
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping

VARIABLE_RED_LOCAL = "SILICE_RED_LOCAL"
VALOR_ENCENDIDA = "1"


def red_local_activa(entorno: Mapping[str, str] | None = None) -> bool:
    """True si el administrador encendió la red local (apagada por defecto)."""
    entorno = os.environ if entorno is None else entorno
    return entorno.get(VARIABLE_RED_LOCAL) == VALOR_ENCENDIDA


def es_bucle_local(ip: str | None) -> bool:
    """True solo para `127.0.0.0/8` y `::1` (y `::ffff:127.x`); texto malo o vacío, False."""
    if not ip:
        return False
    try:
        direccion = ipaddress.ip_address(ip.strip().split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(direccion, ipaddress.IPv6Address) and direccion.ipv4_mapped is not None:
        direccion = direccion.ipv4_mapped
    return direccion.is_loopback


def es_local(ip: str | None, *, red_local_encendida: bool) -> bool:
    """El cliente es el propio equipo (o no se sabe y no hay red local que lo ponga en duda)."""
    if ip is None or not ip.strip():
        return not red_local_encendida
    return es_bucle_local(ip)
