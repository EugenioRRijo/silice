"""Quién entró y qué puede hacer, en la interfaz (spec S3 §5.1, §5.3 y §5.6; RF-80, RF-81).

Cada pestaña del navegador es una sesión de Streamlit con su `st.session_state`; las sesiones
comparten el proceso, así que **nada por usuario** vive en variables de módulo ni en cachés. La
ficha de sesión (un secreto de 256 bits) vive solo en `st.session_state[CLAVE_FICHA]`; la base de
la instalación guarda su SHA-256. En cada ejecución del guion se vuelve a validar y a leer los
roles de la base.

**Interruptor de transición (RP8-4).** `SILICE_ACCESO=1` activa el acceso; sin ella, `sesion_actual`
devuelve un usuario de desarrollo con todos los roles y nada pide entrar. Así S3-1 puede fusionarse
antes de la 0.7.0 sin cambiar la interfaz de nadie; la compuerta GS3 cambia `VALOR_POR_DEFECTO` a
`"1"`. La suite fija `SILICE_ACCESO=0` y las pruebas de S3 lo encienden.

Excepciones declaradas a «nada por usuario en el proceso» (S3 §4.4): el motor de la base de la
instalación (un pool de conexiones por ruta), el semáforo de Argon2 y el freno global.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime

import streamlit as st
from sqlalchemy.orm import Session

from operacion.instalacion import cerrar_motores, sesion_de_instalacion
from seguridad import sesiones
from seguridad.permisos import ROL_DE_LO_SENSIBLE, Accion, Rol, Sensible, permitido
from seguridad.sesiones import SesionActiva
from ui import cliente
from ui.texto_seguro import texto_seguro

__all__ = [
    "CLAVE_FICHA",
    "MENSAJE_SIN_PERMISO",
    "MENSAJE_SOLO_LOCAL",
    "VALOR_POR_DEFECTO",
    "acceso_activo",
    "caja_de_responsable",
    "ahora",
    "exigir",
    "exigir_local",
    "instalacion",
    "limpiar_motores",
    "ip_del_cliente",
    "puede",
    "responsable_actual",
    "responsable_de_la_hoja",
    "sesion_actual",
]

VARIABLE_ACCESO = "SILICE_ACCESO"
VALOR_POR_DEFECTO = "0"  # la compuerta GS3 lo pasa a "1" (RP8-4)
CLAVE_FICHA = "silice_sesion"  # no es de widget
CLAVE_BORRADOR_DE = "silice_borrador_de"
CLAVE_AVISO = "silice_aviso_acceso"
CLAVES_DE_SISTEMA = (CLAVE_FICHA, CLAVE_BORRADOR_DE, CLAVE_AVISO)
MENSAJE_SIN_PERMISO = "Su cuenta no tiene permiso para esta pantalla o acción."
MENSAJE_SOLO_LOCAL = "Esta operación solo se hace en el equipo donde está instalado Sílice."
MENSAJE_SIN_ENTRAR = "Entre con su usuario y contraseña."

#: Con el acceso apagado, quien trabaja es esta persona de desarrollo, con todos los roles.
DESARROLLO = SesionActiva(
    huella_ficha="", usuario_id=0, login="desarrollo", nombre="Desarrollo",
    roles=frozenset(Rol), debe_cambiar_clave=False, restablecida_por_admin=False,
)


def acceso_activo(entorno: Mapping[str, str] | None = None) -> bool:
    entorno = os.environ if entorno is None else entorno
    return entorno.get(VARIABLE_ACCESO, VALOR_POR_DEFECTO) == "1"


def ahora() -> datetime:
    """El reloj de la interfaz; las pruebas lo sustituyen."""
    return datetime.now()


def limpiar_motores() -> None:
    """Solo para las pruebas: cierra los pools de las bases de instalación abiertas."""
    cerrar_motores()


@contextmanager
def instalacion() -> Iterator[Session]:
    """Una sesión de SQLAlchemy sobre `instalacion.db` (la crea y la migra si hace falta)."""
    with sesion_de_instalacion() as sesion:
        yield sesion


def ip_del_cliente() -> str | None:
    """La IP del navegador, como la lee `ui.cliente` (el bucle local llega como `127.0.0.1`);
    `None` si no se pudo leer. Se conserva aquí porque las pruebas de S3 la sustituyen."""
    return cliente.ip_del_cliente()


def sesion_actual() -> SesionActiva | None:
    """La sesión vigente de esta pestaña, o `None`. Valida la ficha y lee los roles de la base."""
    if not acceso_activo():
        return DESARROLLO
    ficha = st.session_state.get(CLAVE_FICHA)
    if not ficha:
        return None
    with instalacion() as bd:
        return sesiones.validar(bd, ficha, ahora())


def responsable_actual() -> str:
    """`Nombre <login>`: lo que la hoja y las pantallas de S1 y S2 escriben como responsable."""
    sesion = sesion_actual()
    if sesion is None:
        raise PermissionError(MENSAJE_SIN_ENTRAR)
    return sesion.usuario


def responsable_de_la_hoja(escrito: str = "") -> str:
    """Quién responde por un cambio de la hoja o de las pantallas de S1 y S2 (RF-82). Con el
    acceso encendido es SIEMPRE el usuario de la sesión, diga lo que diga `escrito` (el cuadro
    «Responsable» ya no existe); con el acceso apagado (transición, RP8-4), lo escrito."""
    return responsable_actual() if acceso_activo() else escrito


def caja_de_responsable(rotulo: str = "Responsable", *, key: str | None = None, contenedor=st):
    """El cuadro «Responsable» de la pantalla. Con el acceso encendido no hay cuadro: muestra
    «Responsable: Ana Pérez» y devuelve al usuario de la sesión; con el acceso apagado, el
    cuadro de siempre. `contenedor` es `st` o una columna."""
    if acceso_activo():
        quien = responsable_actual()
        contenedor.caption(f"{rotulo.strip()}: {texto_seguro(quien)}")
        return quien
    return contenedor.text_input(rotulo, key=key)


def puede(accion: Accion) -> bool:
    sesion = sesion_actual()
    return sesion is not None and permitido(sesion.roles, accion)


def exigir(accion: Accion) -> SesionActiva:
    """Primera línea de `render()` de cada página y de cada función de `ui/` que ejecuta una
    acción: sin sesión o sin el rol, avisa en lenguaje llano y detiene el guion (RF-80)."""
    sesion = sesion_actual()
    if sesion is None:
        st.error(MENSAJE_SIN_ENTRAR)
        st.stop()
    if not permitido(sesion.roles, accion):
        st.error(MENSAJE_SIN_PERMISO)
        st.stop()
    return sesion


def exigir_local(sensible: Sensible) -> SesionActiva:
    """Como `exigir`, y además el cliente debe ser el propio equipo (firmar, clave de firma,
    claves de API...). Rechaza con el mensaje de 21j."""
    sesion = exigir(ROL_DE_LO_SENSIBLE[sensible])
    permitida, motivo = cliente.operacion_sensible_permitida()
    if not permitida:
        st.error(motivo)
        st.stop()
    return sesion
