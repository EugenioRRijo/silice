"""Notificaciones persistentes por persona durante 30 días (C11, servidor).

Cada persona ve y toca solo las suyas (tabla `notificacion` en `instalacion.db`). Las funciones de
este módulo solo hacen `flush()`, nunca `commit()`: la transacción pertenece a quien llama (en la
API, la dependencia de sesión de `instalacion.db`).

Reglas:
- Retención de 30 días exactos: las notificaciones con `creada < ahora - 30 días` se descartan y se
  borran para esa cuenta; las de exactamente 30 días (`creada == ahora - 30 días`) se conservan.
- Orden: las más recientes primero (`creada` descendente, `id` descendente).
- Tope: máximo 200 notificaciones por persona (al agregar se podan las sobrantes más antiguas y al
  listar también se aplica el límite).
- Seguridad en `enlace_ruta`: solo rutas internas que empiecen por «/», sin «//», sin «\\», sin
  esquema ni caracteres de control, y de hasta 300 caracteres.
- C11b: la que crea el servidor por un evento lleva `clave_evento` (hasta 255 caracteres), única
  por persona en la base (`ux_notificacion_usuario_clave`); `existe_clave` dice si ya está. Las
  reglas de quién la recibe viven en `aplicacion/avisos_por_evento.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from seguridad.modelo import Notificacion

__all__ = [
    "DIAS_RETENCION",
    "GRAVEDADES",
    "MAXIMO_NOTIFICACIONES",
    "MAX_DETALLE",
    "MAX_ENLACE_RUTA",
    "MAX_ENLACE_TEXTO",
    "MAX_TITULO",
    "RETENCION",
    "MAX_CLAVE_EVENTO",
    "DatosNotificacion",
    "ItemNotificacion",
    "agregar",
    "contar_sin_leer",
    "existe_clave",
    "listar",
    "marcar_leidas",
    "validar_ruta",
]

GRAVEDADES: tuple[str, ...] = ("listo", "info", "advertencia", "error")
DIAS_RETENCION = 30
RETENCION = timedelta(days=DIAS_RETENCION)
MAXIMO_NOTIFICACIONES = 200
MAX_TITULO = 200
MAX_DETALLE = 1000
MAX_ENLACE_TEXTO = 120
MAX_ENLACE_RUTA = 300
MAX_CLAVE_EVENTO = 255

_MENSAJE_RUTA_INSEGURA = (
    "La ruta del enlace debe ser interna (empezar por «/», sin «//» ni esquema)."
)


@dataclass(frozen=True, slots=True)
class DatosNotificacion:
    """Datos validados al crear una notificación para una persona."""

    gravedad: str
    titulo: str
    detalle: str = ""
    enlace_texto: str = ""
    enlace_ruta: str = ""


@dataclass(frozen=True, slots=True)
class ItemNotificacion:
    """Una notificación almacenada de una persona."""

    id: int
    gravedad: str
    titulo: str
    detalle: str
    enlace_texto: str
    enlace_ruta: str
    creada: datetime
    leida: bool


def _a_item(fila: Notificacion) -> ItemNotificacion:
    return ItemNotificacion(
        id=fila.id,
        gravedad=fila.gravedad,
        titulo=fila.titulo,
        detalle=fila.detalle,
        enlace_texto=fila.enlace_texto,
        enlace_ruta=fila.enlace_ruta,
        creada=fila.creada,
        leida=bool(fila.leida),
    )


def validar_ruta(ruta: str) -> str:
    """Comprueba que `ruta` sea una ruta interna segura de hasta 300 caracteres.

    Rechaza esquemas (`http:`, `https:`, `javascript:`, `data:`), rutas de red (`//...`), barras
    invertidas (`\\`), caracteres de control y rutas que no empiecen por «/».
    """
    if any(ord(c) < 32 or ord(c) == 127 for c in ruta):
        raise ValueError(_MENSAJE_RUTA_INSEGURA)
    limpia = ruta.strip()
    if len(limpia) > MAX_ENLACE_RUTA:
        raise ValueError(f"La ruta del enlace no puede superar los {MAX_ENLACE_RUTA} caracteres.")
    if not limpia.startswith("/") or "//" in limpia or "\\" in limpia:
        raise ValueError(_MENSAJE_RUTA_INSEGURA)
    partes = urlsplit(limpia)
    if partes.scheme or partes.netloc or ":" in partes.path:
        raise ValueError(_MENSAJE_RUTA_INSEGURA)
    return limpia


def _validar_datos(datos: DatosNotificacion) -> tuple[str, str, str, str, str]:
    gravedad = datos.gravedad.strip()
    if gravedad not in GRAVEDADES:
        raise ValueError("La gravedad debe ser listo, info, advertencia o error.")
    titulo = datos.titulo.strip()
    if not titulo:
        raise ValueError("Indique un título para la notificación.")
    if len(titulo) > MAX_TITULO:
        raise ValueError(f"El título no puede superar los {MAX_TITULO} caracteres.")
    detalle = datos.detalle.strip()
    if len(detalle) > MAX_DETALLE:
        raise ValueError("El detalle no puede superar los 1 000 caracteres.")
    enlace_texto = datos.enlace_texto.strip()
    enlace_ruta_bruta = datos.enlace_ruta
    if bool(enlace_texto) != bool(enlace_ruta_bruta.strip()):
        raise ValueError("Indique tanto el texto como la ruta del enlace.")
    if enlace_texto:
        if len(enlace_texto) > MAX_ENLACE_TEXTO:
            raise ValueError(
                f"El texto del enlace no puede superar los {MAX_ENLACE_TEXTO} caracteres."
            )
        enlace_ruta = validar_ruta(enlace_ruta_bruta)
    else:
        enlace_ruta = ""
    return gravedad, titulo, detalle, enlace_texto, enlace_ruta


def _purgar_vencidas(sesion: Session, usuario_id: int, ahora: datetime) -> None:
    """Borra las notificaciones de `usuario_id` estrictamente anteriores a `ahora - 30 días`."""
    corte = ahora - RETENCION
    sesion.execute(
        delete(Notificacion).where(
            Notificacion.usuario_id == usuario_id,
            Notificacion.creada < corte,
        )
    )
    sesion.flush()


def _podar_excedente(sesion: Session, usuario_id: int, recien: int) -> None:
    """Conserva como máximo `MAXIMO_NOTIFICACIONES` para `usuario_id`. Poda primero las que creó
    el front (`clave_evento` nula), las más viejas antes; solo si no alcanzan, las que creó el
    servidor por un evento: así los `POST` del front no empujan fuera un aviso del servidor (como
    el obligatorio `por_dictaminar`; revisión de seguridad T5, n.o 5). La recién creada (`recien`)
    nunca se poda."""
    total = sesion.scalar(
        select(func.count()).select_from(Notificacion).where(Notificacion.usuario_id == usuario_id)
    )
    exceso = (total or 0) - MAXIMO_NOTIFICACIONES
    if exceso <= 0:
        return
    sobrantes = list(
        sesion.scalars(
            select(Notificacion.id)
            .where(Notificacion.usuario_id == usuario_id, Notificacion.id != recien)
            .order_by(
                Notificacion.clave_evento.is_not(None),
                Notificacion.creada.asc(),
                Notificacion.id.asc(),
            )
            .limit(exceso)
        )
    )
    if sobrantes:
        sesion.execute(delete(Notificacion).where(Notificacion.id.in_(sobrantes)))
        sesion.flush()


def listar(
    sesion: Session,
    usuario_id: int,
    ahora: datetime,
    *,
    limite: int = MAXIMO_NOTIFICACIONES,
) -> list[ItemNotificacion]:
    """Descarta y borra las de más de 30 días y devuelve las vigentes de `usuario_id`, las más
    nuevas primero, con tope `MAXIMO_NOTIFICACIONES`."""
    _purgar_vencidas(sesion, usuario_id, ahora)
    tope = max(1, min(limite, MAXIMO_NOTIFICACIONES))
    filas = sesion.scalars(
        select(Notificacion)
        .where(Notificacion.usuario_id == usuario_id)
        .order_by(Notificacion.creada.desc(), Notificacion.id.desc())
        .limit(tope)
    )
    return [_a_item(fila) for fila in filas]


def agregar(
    sesion: Session,
    usuario_id: int,
    datos: DatosNotificacion,
    ahora: datetime,
    *,
    clave_evento: str | None = None,
) -> ItemNotificacion:
    """Valida, purga vencidas, guarda la notificación de `usuario_id` y aplica el tope de 200.

    Con `clave_evento` (C11b) la base no admite otra con la misma clave para esa persona: una
    repetida es un `IntegrityError` al hacer `flush` (quien llama decide si lo absorbe)."""
    gravedad, titulo, detalle, enlace_texto, enlace_ruta = _validar_datos(datos)
    if clave_evento is not None and not 0 < len(clave_evento) <= MAX_CLAVE_EVENTO:
        raise ValueError(f"La clave del evento debe tener de 1 a {MAX_CLAVE_EVENTO} caracteres.")
    _purgar_vencidas(sesion, usuario_id, ahora)
    fila = Notificacion(
        usuario_id=usuario_id,
        gravedad=gravedad,
        titulo=titulo,
        detalle=detalle,
        enlace_texto=enlace_texto,
        enlace_ruta=enlace_ruta,
        creada=ahora,
        leida=False,
        clave_evento=clave_evento,
    )
    sesion.add(fila)
    sesion.flush()
    _podar_excedente(sesion, usuario_id, fila.id)
    return _a_item(fila)


def existe_clave(sesion: Session, usuario_id: int, clave_evento: str) -> bool:
    """Si `usuario_id` ya tiene una notificación con `clave_evento` (leída o no)."""
    return (
        sesion.scalar(
            select(Notificacion.id).where(
                Notificacion.usuario_id == usuario_id,
                Notificacion.clave_evento == clave_evento,
            )
        )
        is not None
    )


def marcar_leidas(
    sesion: Session,
    usuario_id: int,
    *,
    ids: Sequence[int] | None = None,
    todas: bool = False,
) -> int:
    """Marca como leídas las notificaciones indicadas (o todas) de `usuario_id`.

    Devuelve cuántas cambiaron de no leída a leída. Nunca toca las de otra persona.
    """
    if todas and ids is not None:
        raise ValueError("Indique los identificadores o «todas», pero no ambos.")
    if not todas and ids is None:
        raise ValueError("Indique qué notificaciones marcar como leídas.")
    if todas:
        resultado = sesion.execute(
            update(Notificacion)
            .where(Notificacion.usuario_id == usuario_id, Notificacion.leida.is_(False))
            .values(leida=True)
        )
        sesion.flush()
        return int(resultado.rowcount or 0)
    assert ids is not None
    if any(ident <= 0 for ident in ids):
        raise ValueError("Cada identificador de notificación debe ser un entero positivo.")
    unicos = sorted(set(ids))
    if not unicos:
        return 0
    resultado = sesion.execute(
        update(Notificacion)
        .where(
            Notificacion.usuario_id == usuario_id,
            Notificacion.id.in_(unicos),
            Notificacion.leida.is_(False),
        )
        .values(leida=True)
    )
    sesion.flush()
    return int(resultado.rowcount or 0)


def contar_sin_leer(sesion: Session, usuario_id: int, ahora: datetime) -> int:
    """Cuántas notificaciones vigentes (últimos 30 días) tiene `usuario_id` sin leer."""
    corte = ahora - RETENCION
    total = sesion.scalar(
        select(func.count(Notificacion.id)).where(
            Notificacion.usuario_id == usuario_id,
            Notificacion.creada >= corte,
            Notificacion.leida.is_(False),
        )
    )
    return int(total or 0)
