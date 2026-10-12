"""Fichas de sesión sin servicios externos (spec S3 §5.3; DA-S3-1, DA-S3-8).

La ficha es un secreto aleatorio de 256 bits que solo vive en `st.session_state` del servidor;
la base guarda su SHA-256 (no hace falta Argon2: no es una contraseña elegida por una persona).
`validar` es lo que `exigir_sesion` corre en CADA ejecución del guion: busca la huella, comprueba
cierre, inactividad (30 min) y antigüedad (12 h), que la cuenta siga activa, y **lee los roles
de la base**: cambiar los roles de una cuenta cambia su menú en la ejecución siguiente.
El reloj (`ahora`) se inyecta; las cotas son exactas: 29:59 sigue, 30:00 expira.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from seguridad import eventos
from seguridad.modelo import Sesion, Usuario
from seguridad.permisos import Rol, roles_de

INACTIVIDAD = timedelta(minutes=30)
ANTIGUEDAD = timedelta(hours=12)
#: Como mucho una escritura por minuto para renovar la actividad (no cargar SQLite).
RENOVACION_MINIMA = timedelta(minutes=1)


@dataclass(frozen=True, slots=True)
class SesionActiva:
    huella_ficha: str
    usuario_id: int
    login: str
    nombre: str
    roles: frozenset[Rol]
    debe_cambiar_clave: bool
    restablecida_por_admin: bool

    @property
    def usuario(self) -> str:
        """`Nombre <login>`: el responsable que esta persona deja en todo lo que guarda (RF-82);
        es la forma que S4 lee de `st.session_state["silice_sesion"]`."""
        from seguridad.cuentas import texto_responsable

        return texto_responsable(self.nombre, self.login, self.restablecida_por_admin)


def huella_de(ficha: str) -> str:
    return hashlib.sha256(ficha.encode("utf-8")).hexdigest()


def abrir(session: Session, usuario: Usuario, ahora: datetime) -> str:
    """Una ficha NUEVA para `usuario` (al entrar y al cambiar la contraseña). Confirma."""
    ficha = secrets.token_urlsafe(32)
    session.add(
        Sesion(
            huella_ficha=huella_de(ficha), usuario_id=usuario.id, creada=ahora,
            ultima_actividad=ahora, cerrada=False, motivo_cierre="",
        )
    )
    session.commit()
    return ficha


def cerrar(session: Session, ficha: str, motivo: str, ahora: datetime) -> bool:
    """Cierra una ficha (salida, expiración). True si estaba abierta. Confirma."""
    fila = session.get(Sesion, huella_de(ficha))
    if fila is None or fila.cerrada:
        return False
    fila.cerrada, fila.motivo_cierre = True, motivo
    tipo = "expiracion" if motivo in {"inactividad", "antiguedad"} else "salida"
    eventos.registrar(session, tipo, ahora, usuario_id=fila.usuario_id, detalle=motivo)
    session.commit()
    return True


def cerrar_todas(session: Session, usuario_id: int, motivo: str) -> int:
    """Cierra todas las fichas abiertas de una cuenta (restablecer, desactivar, cambiar roles o
    contraseña). Hace `flush`, no `commit`: lo confirma quien llama junto con su cambio."""
    resultado = session.execute(
        update(Sesion)
        .where(Sesion.usuario_id == usuario_id, Sesion.cerrada.is_(False))
        .values(cerrada=True, motivo_cierre=motivo)
    )
    session.flush()
    return resultado.rowcount or 0


def validar(session: Session, ficha: str | None, ahora: datetime) -> SesionActiva | None:
    """La sesión vigente de `ficha`, o `None` si no existe, se cerró o expiró (y la cierra)."""
    if not ficha:
        return None
    fila = session.get(Sesion, huella_de(ficha))
    if fila is None or fila.cerrada:
        return None
    if ahora - fila.creada >= ANTIGUEDAD:
        cerrar(session, ficha, "antiguedad", ahora)
        return None
    if ahora - fila.ultima_actividad >= INACTIVIDAD:
        cerrar(session, ficha, "inactividad", ahora)
        return None
    usuario = session.scalar(select(Usuario).where(Usuario.id == fila.usuario_id))
    if usuario is None or not usuario.activo:
        cerrar(session, ficha, "cuenta desactivada", ahora)
        return None
    if ahora - fila.ultima_actividad >= RENOVACION_MINIMA:
        fila.ultima_actividad = ahora
        session.commit()
    return SesionActiva(
        huella_ficha=fila.huella_ficha,
        usuario_id=usuario.id,
        login=usuario.login,
        nombre=usuario.nombre,
        roles=roles_de(usuario.roles),
        debe_cambiar_clave=usuario.debe_cambiar_clave,
        restablecida_por_admin=usuario.restablecida_por_admin,
    )
