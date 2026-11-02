"""«Solo desde el propio equipo»: el criterio único para la interfaz clásica y la API (RF-98; spec
S5 §8.2; RM-4 de la sesión 2b).

Firmar, generar o exportar la clave de firma, registrar la clave de IA, crear claves de API y
cambiar la carpeta de datos se permiten solo desde el propio equipo y mientras no haya eventos de
seguridad perdidos sin revisar (SEG-12). Vivía en `ui/cliente.py` (que lo reexporta y solo añade
cómo lee Streamlit la IP); la API lo usa con `request.client.host` en
`api.sesion_web.exigir_equipo_propio`.

«El propio equipo» es el bucle local o, con la red local encendida en `silice.toml`, la IP de la
interfaz elegida (que solo tiene el servidor: `operacion.red.es_cliente_local`). Sin IP legible,
es el propio equipo solo con la red local apagada: nadie más puede llegar.
"""

from __future__ import annotations

from operacion import config, eventos_perdidos, red

MENSAJE_REMOTO = (
    "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."
)
MENSAJE_PENDIENTE = (
    "Se restauró un respaldo y hay eventos de seguridad perdidos sin revisar. El administrador "
    "debe revisarlos (Administración, pestaña Instalación) antes de esta operación."
)


def ip_es_local(ip: str | None) -> bool:
    """¿Esa IP es el propio equipo? Con la red local encendida, el bucle local o la IP elegida;
    sin poder leerla, local solo si la red está apagada (nadie más puede llegar)."""
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    if ip is None:
        return not ajustes.red_local
    return red.es_cliente_local(ip, ajustes.direccion if ajustes.red_local else "")


def operacion_sensible_permitida(ip: str | None) -> tuple[bool, str]:
    """`(True, "")` si una operación sensible puede hacerse desde `ip`; si no, `(False, motivo)`
    con un mensaje fijo (el remoto manda sobre el de eventos pendientes)."""
    if not ip_es_local(ip):
        return False, MENSAJE_REMOTO
    if eventos_perdidos.bloqueadas():
        return False, MENSAJE_PENDIENTE
    return True, ""
