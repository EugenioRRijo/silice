"""Qué solicitud de cuenta retiene un login (C9a). Aparte de `solicitudes` para que
`cuentas.crear_usuario` lo consulte sin un ciclo de importaciones: este módulo solo depende del
modelo."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from seguridad.modelo import SolicitudCuenta


def vigente(solicitud: SolicitudCuenta, ahora: datetime) -> bool:
    """El código de una aprobada sirve mientras `ahora < vence`: a los 7 días exactos ya no. Es
    la misma cota para el canje y para el estado `vencida` al responder."""
    return solicitud.vence is not None and ahora < solicitud.vence


def estado_efectivo(solicitud: SolicitudCuenta, ahora: datetime) -> str:
    """El estado actual de la solicitud: una `aprobada` cuyo código venció es `vencida`."""
    if solicitud.estado == "aprobada" and not vigente(solicitud, ahora):
        return "vencida"
    return solicitud.estado


def viva(solicitud: SolicitudCuenta, ahora: datetime) -> bool:
    """Retiene su login: pendiente, o aprobada con el código aún vigente."""
    return solicitud.estado == "pendiente" or (
        solicitud.estado == "aprobada" and vigente(solicitud, ahora)
    )


def por_login(session: Session, login: str, *, releer: bool = False) -> SolicitudCuenta | None:
    consulta = select(SolicitudCuenta).where(SolicitudCuenta.login == login)
    if releer:
        consulta = consulta.execution_options(populate_existing=True)
    return session.scalar(consulta)


def retiene_login(session: Session, login: str, ahora: datetime) -> bool:
    """El login lo retiene una solicitud viva (pendiente, o aprobada con el código vigente). Lo
    consulta también `cuentas.crear_usuario`: el alta a mano no pisa una solicitud en curso."""
    previa = por_login(session, login, releer=True)
    return previa is not None and viva(previa, ahora)
