"""Leer y fijar la fecha de entrega al cliente de una obra (Lote G5; especificación
`docs/especificaciones/2026-11-26-notificaciones-por-evento.md` §4).

La fecha es opcional (`None` si no se ha fijado o si se quita) y no puede estar en el pasado al
fijarla (`fecha_entrega < ahora.date()`). Ninguna función confirma: escriben con `flush` y quien
llama confirma la transacción.

Cada cambio deja rastro en el registro de accesos de la instalación (`evento_acceso`, tipo «fecha
de entrega»: revisión de seguridad T5, hallazgo 2) con la obra, el valor anterior y el nuevo
(`registrar_cambio`). Quién puede fijarla no cambia aquí.
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
from seguridad import eventos

__all__ = [
    "MENSAJE_FECHA_EN_EL_PASADO",
    "TIPO_EVENTO",
    "CambioDeEntrega",
    "EntregaDeLaObra",
    "EntregaInvalida",
    "FechaDeEntregaEnElPasado",
    "ObraNoExiste",
    "cambiar_entrega",
    "detalle_del_cambio",
    "entregas_de_la_carpeta",
    "fijar_entrega",
    "leer_entrega",
    "registrar_cambio",
]

MENSAJE_FECHA_EN_EL_PASADO = "La fecha de entrega al cliente no puede estar en el pasado."
#: El tipo del evento de acceso que deja cada cambio (`seguridad.eventos.TIPOS`).
TIPO_EVENTO = "fecha de entrega"
_SIN_FECHA = "sin fecha"


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


@dataclass(frozen=True, slots=True)
class CambioDeEntrega:
    """Lo que hizo un `cambiar_entrega`: la obra (`nombre`), la fecha que tenía y cómo quedó."""

    nombre: str
    anterior: date | None
    entrega: EntregaDeLaObra


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
    return cambiar_entrega(
        sesion, proyecto, fecha_entrega, responsable=responsable, ahora=ahora
    ).entrega


def cambiar_entrega(
    sesion: Session,
    proyecto: str,
    fecha_entrega: date | None,
    *,
    responsable: str,
    ahora: datetime,
) -> CambioDeEntrega:
    """`fijar_entrega` que además devuelve el nombre de la obra y la fecha que tenía antes, para
    dejar el rastro del cambio (`registrar_cambio`). Mismas reglas y errores. Solo `flush`."""
    obra = _obra(sesion, proyecto)
    quien = _responsable(responsable)
    if fecha_entrega is not None and fecha_entrega < ahora.date():
        raise FechaDeEntregaEnElPasado(MENSAJE_FECHA_EN_EL_PASADO)
    codigo = str(obra.id)
    sin_cambio = EntregaDeLaObra(codigo, None, None, None)
    if not hay_tabla_entrega(sesion):
        if fecha_entrega is None:
            return CambioDeEntrega(obra.nombre, None, sin_cambio)
        crear_esquema_entrega(sesion.connection())
    fila = sesion.get(EntregaDeObra, codigo)
    anterior = None if fila is None else fila.fecha_entrega
    if fila is None:
        if fecha_entrega is None:
            return CambioDeEntrega(obra.nombre, None, sin_cambio)
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
    entrega = EntregaDeLaObra(
        proyecto_codigo=codigo,
        fecha_entrega=fecha_entrega,
        actualizada=ahora,
        actualizada_por=quien,
    )
    return CambioDeEntrega(obra.nombre, anterior, entrega)


def _texto_de(fecha: date | None) -> str:
    return _SIN_FECHA if fecha is None else fecha.isoformat()


def detalle_del_cambio(cambio: CambioDeEntrega, carpeta: str | None) -> str:
    """El detalle del evento: `obra <código> «<nombre>» en la carpeta <carpeta>: antes <fecha>;
    ahora <fecha>` (`sin fecha` si no tenía o se quitó). Sin secretos."""
    donde = "la carpeta de trabajo" if carpeta is None else f"la carpeta {carpeta}"
    return (
        f"obra {cambio.entrega.proyecto_codigo} «{cambio.nombre}» en {donde}: "
        f"antes {_texto_de(cambio.anterior)}; ahora {_texto_de(cambio.entrega.fecha_entrega)}"
    )


def registrar_cambio(
    instalacion: Session,
    cambio: CambioDeEntrega,
    *,
    carpeta: str | None,
    login: str,
    usuario_id: int | None,
    ip: str,
    ahora: datetime,
) -> None:
    """Agrega a `instalacion` el evento «fecha de entrega» del `cambio`. Solo `flush`."""
    eventos.registrar(
        instalacion,
        TIPO_EVENTO,
        ahora,
        login=login[:60],
        usuario_id=usuario_id,
        ip=ip,
        detalle=detalle_del_cambio(cambio, carpeta),
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
