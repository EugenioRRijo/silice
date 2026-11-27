"""Leer y fijar la fecha de entrega al cliente de una obra (Lote G5; especificación
`docs/especificaciones/2026-11-26-notificaciones-por-evento.md` §4).

La fecha es opcional (`None` si no se ha fijado o si se quita) y no puede estar en el pasado al
fijarla (`fecha_entrega < ahora.date()`). Ninguna función confirma: escriben con `flush` y quien
llama confirma la transacción.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.listas_para_armar import exigir_responsable
from aplicacion.proyectos import resolver_proyecto
from aplicacion.tablas_entrega import (
    LARGO_RESPONSABLE,
    EntregaDeObra,
    crear_esquema_entrega,
    hay_tabla_entrega,
)
from core import models

__all__ = [
    "MENSAJE_FECHA_EN_EL_PASADO",
    "EntregaDeLaObra",
    "EntregaInvalida",
    "FechaDeEntregaEnElPasado",
    "ObraNoExiste",
    "entregas_de_la_carpeta",
    "fijar_entrega",
    "leer_entrega",
]

MENSAJE_FECHA_EN_EL_PASADO = "La fecha de entrega al cliente no puede estar en el pasado."


class EntregaInvalida(ValueError):  # noqa: N818 (identificadores en español, NORMAS.md §3)
    """Lo pedido para la fecha de entrega de la obra no cumple una regla; el mensaje es para la
    persona."""


class FechaDeEntregaEnElPasado(EntregaInvalida):
    """La fecha de entrega al cliente es anterior al día de hoy (la API responde 422)."""


class ObraNoExiste(LookupError):  # noqa: N818
    """No hay ninguna obra con ese código o nombre en la carpeta (la API responde 404)."""


@dataclass(frozen=True, slots=True)
class EntregaDeLaObra:
    """La fecha de entrega al cliente de una obra (`None` si no tiene) y quién la actualizó."""

    proyecto_codigo: str
    fecha_entrega: date | None
    actualizada: datetime | None = None
    actualizada_por: str | None = None


def _obra(sesion: Session, proyecto: str) -> models.Proyecto:
    obra = resolver_proyecto(sesion, proyecto.strip())
    if obra is None:
        raise ObraNoExiste(f"No hay ninguna obra «{proyecto}» en esta carpeta de trabajo.")
    return obra


def _responsable(texto: str) -> str:
    limpio = exigir_responsable(texto)
    if len(limpio) > LARGO_RESPONSABLE:
        raise ValueError(
            f"quien actualiza (responsable) admite hasta {LARGO_RESPONSABLE} caracteres"
        )
    return limpio


def leer_entrega(sesion: Session, proyecto: str) -> EntregaDeLaObra:
    """Lee la fecha de entrega al cliente de `proyecto` (código o nombre). Sin tabla o sin fila,
    devuelve `fecha_entrega=None` sin escribir nada. `ObraNoExiste` si la obra no existe."""
    obra = _obra(sesion, proyecto)
    codigo = str(obra.id)
    if not hay_tabla_entrega(sesion):
        return EntregaDeLaObra(codigo, None, None, None)
    fila = sesion.get(EntregaDeObra, codigo)
    if fila is None:
        return EntregaDeLaObra(codigo, None, None, None)
    return EntregaDeLaObra(
        proyecto_codigo=codigo,
        fecha_entrega=fila.fecha_entrega,
        actualizada=fila.actualizada,
        actualizada_por=fila.actualizada_por,
    )


def fijar_entrega(
    sesion: Session,
    proyecto: str,
    fecha_entrega: date | None,
    *,
    responsable: str,
    ahora: datetime,
) -> EntregaDeLaObra:
    """Fija o quita (`None`) la fecha de entrega al cliente de `proyecto` (código o nombre).

    `FechaDeEntregaEnElPasado` si `fecha_entrega` es anterior a `ahora.date()`; `ObraNoExiste` si la
    obra no existe. Si la tabla aún no existe en la base, la crea al guardar. Solo `flush`."""
    obra = _obra(sesion, proyecto)
    quien = _responsable(responsable)
    if fecha_entrega is not None and fecha_entrega < ahora.date():
        raise FechaDeEntregaEnElPasado(MENSAJE_FECHA_EN_EL_PASADO)
    codigo = str(obra.id)
    if not hay_tabla_entrega(sesion):
        if fecha_entrega is None:
            return EntregaDeLaObra(codigo, None, None, None)
        crear_esquema_entrega(sesion.connection())
    fila = sesion.get(EntregaDeObra, codigo)
    if fila is None:
        if fecha_entrega is None:
            return EntregaDeLaObra(codigo, None, None, None)
        sesion.add(
            EntregaDeObra(
                proyecto_codigo=codigo,
                fecha_entrega=fecha_entrega,
                actualizada=ahora,
                actualizada_por=quien,
            )
        )
    else:
        fila.fecha_entrega = fecha_entrega
        fila.actualizada = ahora
        fila.actualizada_por = quien
    sesion.flush()
    return EntregaDeLaObra(
        proyecto_codigo=codigo,
        fecha_entrega=fecha_entrega,
        actualizada=ahora,
        actualizada_por=quien,
    )


def entregas_de_la_carpeta(sesion: Session) -> dict[int, EntregaDeLaObra]:
    """`{proyecto_id: entrega}` de las obras de la carpeta con fecha de entrega vigente, con cuándo
    se fijó (`actualizada`: un paquete exportado antes no es la entrega de esa fecha). Sin la
    tabla, devuelve `{}` sin escribir nada."""
    if not hay_tabla_entrega(sesion):
        return {}
    return {
        int(fila.proyecto_codigo): EntregaDeLaObra(
            proyecto_codigo=fila.proyecto_codigo,
            fecha_entrega=fila.fecha_entrega,
            actualizada=fila.actualizada,
            actualizada_por=fila.actualizada_por,
        )
        for fila in sesion.scalars(
            select(EntregaDeObra).where(EntregaDeObra.fecha_entrega.is_not(None))
        )
        if fila.fecha_entrega is not None and fila.proyecto_codigo.isdigit()
    }
