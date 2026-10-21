"""El modo entrega para la API (`SILICE_MODO_ENTREGA`; punto 7 de la ola 0a, sesión 2b).

Aquí viven también los nombres de las variables de entorno de Sílice y sus alias anteriores (plan
de la 0.6.0, tarea A1; movido de `ui/entorno.py` en el retiro de Streamlit, F5). Durante el
prototipo el producto se llamó AREN.IA (hoy Sílice) y sus variables llevaban ese prefijo. Desde la
0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`; `ARENIA_CASO` y `ARENIA_MODO_ENTREGA` se
aceptaron como alias hasta la 0.6.0 inclusive y **ya no se aceptan desde la 0.7.0**:
`ALIAS_ANTERIORES` quedó vacío (`tests/unit/test_entorno_silice.py` lo exige en cuanto
`pyproject.toml` pasa de la 0.6.0). Por eso el modo entrega se enciende solo con el valor exacto
`"1"`.

Regla de `leer_variable`: manda la variable nueva si tiene texto; si falta o está en blanco, su
alias (hoy ninguno); si ninguna, `None`.

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

VARIABLE_CASO = "SILICE_CASO"
VARIABLE_MODO_ENTREGA = "SILICE_MODO_ENTREGA"
VALOR_MODO_ENTREGA = "1"
VARIABLE_DIRECCION = "SILICE_DIRECCION"  # la fija el lanzador (`operacion.lanzador`)
BUCLE_LOCAL = "127.0.0.1"

#: Última versión que acepta los nombres anteriores.
ULTIMA_VERSION_CON_ALIAS = "0.6.0"

#: Nombre nuevo -> nombre anterior aceptado como alias hasta `ULTIMA_VERSION_CON_ALIAS`.
#: Retirados en la 0.7.0 (eran `ARENIA_CASO` y `ARENIA_MODO_ENTREGA`).
ALIAS_ANTERIORES: dict[str, str] = {}


def leer_variable(entorno: Mapping[str, str], nombre: str) -> str | None:
    """El valor de `nombre` en `entorno` o, si falta o está en blanco, el de su alias anterior.

    `None` si ninguna de las dos tiene texto.
    """
    for candidato in (nombre, ALIAS_ANTERIORES.get(nombre)):
        if candidato is None:
            continue
        valor = entorno.get(candidato)
        if valor is not None and valor.strip():
            return valor
    return None


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
