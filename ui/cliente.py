"""Quién llega a Sílice: «el propio equipo» y las operaciones sensibles (RF-98; spec S5 §8.2).

Firmar, generar o exportar la clave de firma, registrar la clave de IA, crear claves de API y
cambiar la carpeta de datos se permiten solo desde el propio equipo y mientras no haya eventos de
seguridad perdidos sin revisar (SEG-12). Sin TLS, la pantalla de acceso avisa al cliente remoto.

La IP sale de `st.context.ip_address`. En Streamlit 1.62 esa propiedad devuelve `None` cuando el
navegador llega por `127.0.0.1` o `::1` (o no hay contexto de cliente) y la IP del par TCP en los
demás casos; por eso aquí `None` se lee como «bucle local». «No se pudo leer» es otra cosa: la
excepción o un valor que no es texto, que se trata como remoto salvo con la red local apagada.
"""

from __future__ import annotations

import streamlit as st

from operacion import config, eventos_perdidos, red

MENSAJE_REMOTO = (
    "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."
)
MENSAJE_PENDIENTE = (
    "Se restauró un respaldo y hay eventos de seguridad perdidos sin revisar. El administrador "
    "debe revisarlos (Administración, pestaña Instalación) antes de esta operación."
)
BUCLE_LOCAL = "127.0.0.1"


def ip_del_cliente() -> str | None:
    """La IP del navegador. `st.context.ip_address` da `None` para el bucle local (se devuelve
    `127.0.0.1`); `None` aquí quiere decir que no se pudo leer."""
    try:
        ip = st.context.ip_address
    except (AttributeError, RuntimeError):
        return None
    if ip is None:
        return BUCLE_LOCAL
    return ip if isinstance(ip, str) else None


def ip_es_local(ip: str | None) -> bool:
    """¿Esa IP es el propio equipo? Con la red local encendida, el bucle local o la IP elegida;
    sin poder leerla, local solo si la red está apagada (nadie más puede llegar)."""
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    if ip is None:
        return not ajustes.red_local
    return red.es_cliente_local(ip, ajustes.direccion if ajustes.red_local else "")


def cliente_es_local() -> bool:
    return ip_es_local(ip_del_cliente())


def operacion_sensible_permitida() -> tuple[bool, str]:
    if not cliente_es_local():
        return False, MENSAJE_REMOTO
    if eventos_perdidos.bloqueadas():
        return False, MENSAJE_PENDIENTE
    return True, ""


def pintar_aviso_sin_cifrar(ip: str | None = None) -> bool:
    """Para la pantalla de acceso: avisa al cliente remoto que la conexión no está cifrada.
    Sin `ip`, la lee de Streamlit."""
    if ip_es_local(ip if ip is not None else ip_del_cliente()):
        return False
    st.warning(red.AVISO_ACCESO)
    return True
