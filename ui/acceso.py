"""Pantalla de acceso, primer administrador y barra de sesión (spec S3 §5.3, §5.5 y §5.7).

**Solo la importa `ui/app.py`** (como `ui/barra.py`). `exigir_sesion()` es lo primero que corre
`main()`: devuelve la sesión vigente o pinta el acceso y detiene el guion con `st.stop()`. Todo
mensaje de error es fijo (el mismo exista o no el usuario) y todo nombre que viene de la base
pasa por `texto_seguro` (RV-14). Una sesión que expira conserva el borrador de la pestaña
**marcado con su dueño**: el mismo usuario lo recupera al volver a entrar; otro lo descarta con
aviso (21d).
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from operacion.config import carpeta_datos
from operacion.red import AVISO_ACCESO
from seguridad import cuentas, sesiones
from seguridad.modelo import Sesion, Usuario
from seguridad.permisos import aviso_de_roles
from seguridad.sesiones import SesionActiva
from ui import cliente
from ui import sesion as ui_sesion
from ui.sesion import (
    CLAVE_AVISO,
    CLAVE_BORRADOR_DE,
    CLAVE_FICHA,
    CLAVES_DE_SISTEMA,
    DESARROLLO,
    acceso_activo,
)
from ui.texto_seguro import texto_seguro

__all__ = [
    "AVISO_EXPIRADA",
    "AVISO_OTRO_USUARIO",
    "AVISO_SIN_CIFRAR",
    "exigir_sesion",
    "pintar_sesion",
]

AVISO_SIN_CIFRAR = AVISO_ACCESO  # el texto y la regla de «cliente remoto» son de S5 (ui.cliente)
AVISO_EXPIRADA = "Su sesión se cerró por inactividad. Entre de nuevo: su borrador sigue aquí."
AVISO_OTRO_USUARIO = "Entró otra persona: el borrador de la sesión anterior se descartó."
TITULO_ACCESO = "Sílice: acceso"


def _ahora():
    return ui_sesion.ahora()  # por el módulo, para que las pruebas puedan sustituir el reloj


def _ip() -> str | None:
    return ui_sesion.ip_del_cliente()


def descartar_borrador() -> None:
    """Quita de la pestaña todo salvo lo que es del acceso (el borrador de otra persona)."""
    for clave in list(st.session_state):
        if clave not in CLAVES_DE_SISTEMA:
            del st.session_state[clave]


def _recordar_dueno(bd: Session, ficha: str) -> None:
    """La ficha ya no vale: el borrador de la pestaña queda a nombre de su dueño."""
    if st.session_state.get(CLAVE_BORRADOR_DE):
        return
    fila = bd.get(Sesion, sesiones.huella_de(ficha))
    usuario = bd.get(Usuario, fila.usuario_id) if fila is not None else None
    if usuario is not None:
        st.session_state[CLAVE_BORRADOR_DE] = usuario.login


def _iniciar(bd: Session, usuario: Usuario) -> None:
    dueno = st.session_state.get(CLAVE_BORRADOR_DE)
    if dueno and dueno != usuario.login:
        descartar_borrador()
        st.session_state[CLAVE_AVISO] = AVISO_OTRO_USUARIO
    else:
        st.session_state.pop(CLAVE_AVISO, None)
    st.session_state.pop(CLAVE_BORRADOR_DE, None)
    st.session_state[CLAVE_FICHA] = sesiones.abrir(bd, usuario, _ahora())
    st.rerun()


def _aviso_de_red() -> None:
    cliente.pintar_aviso_sin_cifrar(_ip())


def _formulario_de_entrada(bd: Session) -> None:
    with st.form("silice_acceso"):
        login = st.text_input("Usuario", key="acceso_login")
        contrasena = st.text_input("Contraseña", type="password", key="acceso_contrasena")
        enviar = st.form_submit_button("Entrar", type="primary")
    if not enviar:
        return
    try:
        usuario = cuentas.autenticar(bd, login, contrasena, _ahora(), ip=_ip() or "")
    except cuentas.ErrorDeAcceso as error:  # incluye CuentaBloqueada: mensajes fijos
        st.error(str(error))  # mensaje fijo de seguridad.cuentas: no lleva texto ajeno
        return
    _iniciar(bd, usuario)


def _formulario_primer_administrador(bd: Session) -> None:
    carpeta = carpeta_datos()
    cuentas.preparar_primera_vez(bd, carpeta, _ahora())
    st.subheader("Primera vez en este equipo")
    st.write(
        "No hay ninguna cuenta. Abra el archivo `codigo_instalacion.txt` de la carpeta de datos "
        "de Sílice, copie el código de 20 caracteres y cree la cuenta del administrador."
    )
    with st.form("silice_primer_administrador"):
        codigo = st.text_input("Código de instalación", key="acceso_codigo")
        login = st.text_input("Usuario", key="acceso_nuevo_login")
        nombre = st.text_input("Su nombre", key="acceso_nuevo_nombre")
        clave = st.text_input("Contraseña (10 a 128 caracteres)", type="password",
                              key="acceso_nueva_clave")
        repetida = st.text_input("Repita la contraseña", type="password", key="acceso_repetida")
        enviar = st.form_submit_button("Crear el administrador", type="primary")
    if not enviar:
        return
    if clave != repetida:
        st.error("Las dos contraseñas no coinciden.")
        return
    try:
        usuario = cuentas.reclamar_instalacion(
            bd, codigo, login, nombre, clave, _ahora(), carpeta, ip=_ip() or ""
        )
    except (cuentas.ErrorDeAcceso, cuentas.ContrasenaInvalida, ValueError) as error:
        st.error(str(error))  # mensaje fijo de seguridad.cuentas: no lleva texto ajeno
        return
    _iniciar(bd, usuario)


def _pantalla_de_acceso(bd: Session) -> None:
    st.title(TITULO_ACCESO)
    _aviso_de_red()
    aviso = st.session_state.get(CLAVE_AVISO)
    if aviso:
        st.info(aviso)
    if cuentas.hay_usuarios(bd):
        _formulario_de_entrada(bd)
    else:
        _formulario_primer_administrador(bd)


def _cambio_obligatorio(bd: Session, sesion: SesionActiva) -> None:
    st.title("Cambie su contraseña")
    st.write("Su contraseña es temporal: elija una propia para seguir.")
    with st.form("silice_cambio_de_clave"):
        actual = st.text_input("Contraseña actual", type="password", key="cambio_actual")
        nueva = st.text_input("Contraseña nueva (10 a 128 caracteres)", type="password",
                              key="cambio_nueva")
        repetida = st.text_input("Repita la nueva", type="password", key="cambio_repetida")
        enviar = st.form_submit_button("Cambiar", type="primary")
    if not enviar:
        return
    if nueva != repetida:
        st.error("Las dos contraseñas no coinciden.")
        return
    try:
        ficha = cuentas.cambiar_contrasena(bd, sesion.usuario_id, actual, nueva, _ahora())
    except (cuentas.ErrorDeAcceso, cuentas.ContrasenaInvalida) as error:
        st.error(str(error))  # mensaje fijo de seguridad.cuentas: no lleva texto ajeno
        return
    st.session_state[CLAVE_FICHA] = ficha  # la ficha nueva: la anterior se cerró
    st.rerun()


def exigir_sesion() -> SesionActiva:
    """La sesión vigente, o el acceso y `st.stop()`. Con el acceso apagado, la de desarrollo."""
    if not acceso_activo():
        return DESARROLLO
    with ui_sesion.instalacion() as bd:
        ficha = st.session_state.get(CLAVE_FICHA)
        activa = sesiones.validar(bd, ficha, _ahora())
        if activa is not None:
            if activa.debe_cambiar_clave:
                _cambio_obligatorio(bd, activa)
                st.stop()
            return activa
        if ficha:  # tenía ficha y ya no vale: expiró o se la cerraron
            _recordar_dueno(bd, ficha)
            st.session_state.pop(CLAVE_FICHA, None)
            st.session_state[CLAVE_AVISO] = AVISO_EXPIRADA
        _pantalla_de_acceso(bd)
    st.stop()


def pintar_sesion(sesion: SesionActiva) -> None:
    """«Sesión: Ana Pérez (arma) · Cerrar sesión» en la barra lateral."""
    if sesion is DESARROLLO:
        return
    roles = ", ".join(sorted(rol.value for rol in sesion.roles))
    with st.sidebar:
        st.caption(f"Sesión: {texto_seguro(sesion.nombre)} ({texto_seguro(roles)})")
        aviso = aviso_de_roles(sesion.roles)
        if aviso:
            st.caption(aviso)
        if st.button("Cerrar sesión", key="silice_cerrar_sesion"):
            with ui_sesion.instalacion() as bd:
                sesiones.cerrar(bd, st.session_state.get(CLAVE_FICHA, ""), "salida", _ahora())
            descartar_borrador()
            st.session_state.pop(CLAVE_FICHA, None)
            st.session_state.pop(CLAVE_BORRADOR_DE, None)
            st.rerun()
