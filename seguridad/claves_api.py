"""Claves de API para herramientas externas (spec S3 §10; DA-S3-8; SEG-15).

La clave se muestra UNA vez como `<identificador>.<secreto>`: el identificador público de 8
caracteres va aparte del secreto, que conserva sus 256 bits. La base guarda solo el SHA-256 del
secreto (Argon2 en cada petición de la API sería lento y no aporta: el secreto es aleatorio).
La comparación es de tiempo constante.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from seguridad import eventos
from seguridad.modelo import ClaveApi

ALFABETO_IDENTIFICADOR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
LONGITUD_IDENTIFICADOR = 8
CABECERA = "X-Silice-Clave"
RENOVACION_MINIMA = timedelta(minutes=1)


def _huella(secreto: str) -> str:
    return hashlib.sha256(secreto.encode("utf-8")).hexdigest()


def crear(session: Session, nombre: str, actor: str, ahora: datetime) -> tuple[str, ClaveApi]:
    """`(clave en claro, fila)`. La clave en claro no se guarda y no se puede recuperar."""
    if not nombre.strip():
        raise ValueError("La clave de API necesita un nombre (por ejemplo, el plugin que la usa).")
    while True:
        identificador = "".join(
            secrets.choice(ALFABETO_IDENTIFICADOR) for _ in range(LONGITUD_IDENTIFICADOR)
        )
        existente = select(ClaveApi.id).where(ClaveApi.identificador == identificador)
        if session.scalar(existente) is None:
            break
    secreto = secrets.token_urlsafe(32)
    fila = ClaveApi(
        nombre=nombre.strip(),
        identificador=identificador,
        huella_secreto=_huella(secreto),
        creada=ahora,
        creada_por=actor,
        revocada=False,
    )
    session.add(fila)
    session.flush()
    eventos.registrar(session, "clave de api", ahora, detalle=f"creada {identificador}; {actor}")
    session.commit()
    return f"{identificador}.{secreto}", fila


def verificar(session: Session, presentada: str | None, ahora: datetime) -> ClaveApi | None:
    """La fila de la clave si es vigente; `None` si falta, está mal formada, es desconocida o
    fue revocada. No distingue entre esos casos hacia afuera."""
    if not presentada or presentada.count(".") != 1:
        return None
    identificador, secreto = presentada.split(".")
    fila = session.scalar(select(ClaveApi).where(ClaveApi.identificador == identificador))
    esperada = fila.huella_secreto if fila is not None else _huella("relleno")
    coincide = hmac.compare_digest(esperada, _huella(secreto))
    if fila is None or fila.revocada or not coincide:
        return None
    if fila.ultimo_uso is None or ahora - fila.ultimo_uso >= RENOVACION_MINIMA:
        fila.ultimo_uso = ahora
        session.commit()
    return fila


def revocar(session: Session, clave_id: int, actor: str, ahora: datetime) -> None:
    fila = session.get(ClaveApi, clave_id)
    if fila is None:
        raise LookupError("No hay una clave de API con ese número.")
    fila.revocada = True
    eventos.registrar(session, "clave de api", ahora, detalle=f"revocada {fila.identificador}")
    session.commit()


def etiqueta(fila: ClaveApi) -> str:
    """Lo que la API pone como `usuario` de lo que cree: `api:<identificador>` (S3 §6.2)."""
    return f"api:{fila.identificador}"
