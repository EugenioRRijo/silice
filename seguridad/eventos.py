"""El registro de accesos (`evento_acceso`): solo-agregar y sin secretos (spec S3 §7.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from seguridad.modelo import EventoAcceso

TIPOS = (
    "entrada", "fallo", "bloqueo", "salida", "expiracion", "cambio de clave", "alta", "baja",
    "alta de clave", "cambio de roles", "desbloqueo", "restablecimiento", "firma",
    "paquete exportado", "clave de api", "retiro", "revocacion", "codigo de instalacion",
    "empresa", "clave registrada",
    # S4 §8.3: la contraseña no abrió el respaldo cifrado de la clave de IA (ruta, sesión 1)
    "clave de ia no reactivada",
)


def registrar(
    session: Session,
    tipo: str,
    ahora: datetime,
    *,
    login: str = "",
    usuario_id: int | None = None,
    ip: str = "",
    detalle: str = "",
) -> EventoAcceso:
    """Agrega un evento. `detalle` no lleva secretos: lo escribe quien llama, y una prueba
    busca contraseñas y fichas en toda la tabla."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo de evento desconocido: {tipo!r}")
    evento = EventoAcceso(
        fecha_hora=ahora, login_intentado=login, usuario_id=usuario_id, ip_cliente=ip,
        tipo=tipo, detalle=detalle,
    )
    session.add(evento)
    session.flush()
    return evento


def ultimos(session: Session, cuantos: int = 200) -> list[EventoAcceso]:
    return list(
        session.scalars(select(EventoAcceso).order_by(EventoAcceso.id.desc()).limit(cuantos))
    )
