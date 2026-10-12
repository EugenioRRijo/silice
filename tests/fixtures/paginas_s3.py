"""Entrar a las páginas de S3 con `AppTest`: instalación temporal, reloj e IP inyectados."""

from __future__ import annotations

from pathlib import Path

from seguridad import sesiones
from seguridad.modelo import Usuario
from tests.fixtures.instalacion import AHORA, administrador, persona
from ui import sesion as ui_sesion
from ui.sesion import CLAVE_FICHA


def preparar(
    monkeypatch, carpeta: Path, *roles: str, ip: str = "127.0.0.1", login: str = "luis"
) -> str:
    """Enciende el acceso sobre una `instalacion.db` nueva en `carpeta`, crea al administrador y,
    si `roles` no es `("administrador",)`, una cuenta `login` con esos roles; abre la sesión de la
    cuenta que corresponde y devuelve su ficha."""
    monkeypatch.setenv("SILICE_ACCESO", "1")
    monkeypatch.setenv("SILICE_DATOS", str(carpeta))
    monkeypatch.setenv("SILICE_INSTALACION", str(carpeta / "instalacion.db"))
    monkeypatch.setattr(ui_sesion, "ahora", lambda: AHORA)
    monkeypatch.setattr(ui_sesion, "ip_del_cliente", lambda: ip)
    ui_sesion.limpiar_motores()
    with ui_sesion.instalacion() as bd:
        admin = administrador(bd, carpeta)
        if tuple(roles) == ("administrador",):
            usuario = admin
        else:
            usuario = persona(bd, admin, login, roles)
            usuario.debe_cambiar_clave = False
            bd.commit()
        return sesiones.abrir(bd, bd.get(Usuario, usuario.id), AHORA)


def con_ficha(at, ficha: str):
    at.session_state[CLAVE_FICHA] = ficha
    return at
