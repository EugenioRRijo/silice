"""El modo entrega para la API (`SILICE_MODO_ENTREGA`; punto 7 de la ola 0a, sesión 2b).

Duplica a propósito `ui.app.modo_entrega_activo`: la API no importa `ui/` y `ui/entorno.py` solo
usa la biblioteca estándar (no puede importar esta capa). Desde la 0.7.0 no hay alias que leer
(`ui.entorno.ALIAS_ANTERIORES` está vacío), así que la regla es la misma: encendido solo con el
valor exacto `"1"`. `tests/unit/test_aplicacion_entorno.py` compara las dos funciones.

`url_clasica` es la dirección de la interfaz Streamlit, para que el menú de la interfaz nueva
enlace las páginas que aún no se migraron: la IP en que el lanzador arrancó las dos interfaces
(`SILICE_DIRECCION`, la misma de la API) si es una IPv4 privada, o el bucle local, y el puerto de
Streamlit de `silice.toml`. No dice nada que no sea público en la red local.
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping

from operacion import config

VARIABLE_MODO_ENTREGA = "SILICE_MODO_ENTREGA"
VALOR_MODO_ENTREGA = "1"
VARIABLE_DIRECCION = "SILICE_DIRECCION"  # la fija el lanzador (`operacion.lanzador`)
BUCLE_LOCAL = "127.0.0.1"


def modo_entrega_activo(entorno: Mapping[str, str] | None = None) -> bool:
    """True si `SILICE_MODO_ENTREGA` vale exactamente `"1"` (en `entorno` o en el del proceso)."""
    fuente = os.environ if entorno is None else entorno
    return fuente.get(VARIABLE_MODO_ENTREGA) == VALOR_MODO_ENTREGA


def _direccion_publicable(texto: str) -> str:
    """La IP si es IPv4 privada y no la «todas las interfaces»; si no, el bucle local (el mismo
    criterio que `api.proteccion.anfitriones_permitidos`)."""
    try:
        ip = ipaddress.ip_address(texto.strip())
    except ValueError:
        return BUCLE_LOCAL
    if ip.version == 4 and ip.is_private and not ip.is_unspecified and not ip.is_loopback:
        return str(ip)
    return BUCLE_LOCAL


def url_clasica(entorno: Mapping[str, str] | None = None) -> str:
    """`http://<ip>:<puerto>/` de la interfaz Streamlit de esta instalación. `entorno` solo
    sustituye a `SILICE_DIRECCION`; el puerto sale siempre del `silice.toml` del proceso."""
    fuente = os.environ if entorno is None else entorno
    direccion = _direccion_publicable(fuente.get(VARIABLE_DIRECCION, ""))
    ajustes = config.cargar_ajustes(config.ruta_ajustes())  # los del proceso
    return f"http://{direccion}:{ajustes.puerto}/"
