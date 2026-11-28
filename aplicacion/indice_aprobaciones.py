"""El índice de aprobaciones de la instalación: «Por aprobar» de todas las carpetas (MP-4, Tarea
18; choque 14 del plan de montar un presupuesto).

Las aprobaciones viven en cada carpeta de trabajo y no hay transacción común entre una carpeta y
`instalacion.db`. Por eso la carpeta es la fuente de verdad y este índice es su reflejo:

- `leer_reflejo(caso, sesion_caso)` lee de la carpeta las filas de su índice (una por envío,
  desde su rastro, `aplicacion.aprobaciones.envios`) sin escribir nada, y
  `escribir_reflejo(sesion_ins, reflejo)` **reescribe** con ellas las de esa carpeta (solo `flush`:
  la transacción de la instalación es de quien llama). Al enviar y al dictaminar, la ruta lee el
  reflejo con lo escrito y antes del `commit` de la carpeta (leerla tras él abriría otro `BEGIN
  IMMEDIATE`, DS-57) y lo escribe después, en una transacción corta y propia de la instalación:
  nunca retiene las dos bases a la vez (DS-69). Como dos peticiones pueden escribir fuera de orden,
  las filas del índice dicen cuántos eventos del rastro reflejan (`Reflejo.eventos`: cada una es
  un envío y su cierre, si lo tiene; el rastro solo crece) y un reflejo con menos no las pisa.
- `reflejar(sesion_ins, caso, sesion_caso)` lee y escribe sin esa guarda: es la reposición de
  `GET /v1/aprobaciones/pendientes`, `/mias` y `/resumen`, que toma antes el bloqueo de la
  instalación y luego lee la carpeta (así el que escribe después lee una carpeta más nueva). Si un
  reflejo se perdió (falló antes o después de confirmar la carpeta) o la carpeta se restauró a un
  respaldo anterior, ahí se repone.
- `pendientes(sesion_ins)`: lo que espera dictamen en todas las carpetas, lo más antiguo primero.
- `de_quien(sesion_ins, usuario, limite)`: lo último que envió una cuenta (reconocida por su
  `<login>`, con `aprobaciones.misma_cuenta`), lo más reciente primero.

El total de cada envío es Σ `partida_presupuestada.total` de su versión, sumado en `Decimal`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from aplicacion import aprobaciones
from aplicacion.tablas_indice_aprobacion import FilaIndiceAprobacion
from core import models

__all__ = [
    "LIMITE_MIAS",
    "AlReflejar",
    "FilaIndice",
    "Reflejo",
    "de_quien",
    "escribir_reflejo",
    "leer_reflejo",
    "pendientes",
    "reflejar",
]

#: Cuántas filas trae «Mis versiones en aprobación» por omisión.
LIMITE_MIAS = 20


@dataclass(frozen=True, slots=True)
class FilaIndice:
    caso: str
    envio_id: int
    proyecto: str  # el código de la obra en su carpeta (el `id` como texto)
    obra: str  # el nombre de la obra
    version: str
    total: Decimal
    moneda: str
    estado: str  # en_aprobacion | retirada | aprobada | aprobada_con_observaciones | devuelta
    enviado_por: str
    enviado_el: datetime
    dictamen_por: str | None
    dictamen_el: datetime | None
    nota: str  # la del envío
    notas: str  # las del dictamen
    armo: bool  # quien dictaminó es quien guardó la versión (falso sin dictamen)


@dataclass(frozen=True, slots=True)
class Reflejo:
    """Las filas del índice de la carpeta `caso`, leídas de su rastro en un momento dado."""

    caso: str
    filas: tuple[FilaIndice, ...]

    @property
    def eventos(self) -> int:
        """Cuántos eventos del rastro refleja: el marcador de frescura (`_eventos`)."""
        return _eventos(self.filas)


def _eventos(filas: Iterable[FilaIndice]) -> int:
    """Un evento por envío y otro por su cierre (retiro o dictamen), si lo tiene. El rastro solo
    crece y cada escritura le añade al menos uno: más eventos es una carpeta más nueva."""
    return sum(1 if fila.estado == "en_aprobacion" else 2 for fila in filas)


def leer_reflejo(caso: str, sesion_caso: Session) -> Reflejo:
    """Las filas del índice de la carpeta `caso` con los envíos de `sesion_caso`. Solo lee."""
    obras: dict[int, models.Proyecto | None] = {}
    versiones: dict[tuple[int, str], tuple[Decimal, str]] = {}
    filas = []
    for registrado in aprobaciones.envios(sesion_caso):
        if registrado.proyecto_id not in obras:
            obras[registrado.proyecto_id] = sesion_caso.get(models.Proyecto, registrado.proyecto_id)
        obra = obras[registrado.proyecto_id]
        clave = (registrado.proyecto_id, registrado.version)
        if clave not in versiones:
            versiones[clave] = aprobaciones.total_y_moneda(sesion_caso, *clave)
        total, moneda = versiones[clave]
        dictamen = registrado.estado not in ("en_aprobacion", "retirada")
        filas.append(
            FilaIndice(
                caso=caso,
                envio_id=registrado.id,
                proyecto=str(registrado.proyecto_id),
                obra="" if obra is None else obra.nombre,
                version=registrado.version,
                total=total,
                moneda=moneda,
                estado=registrado.estado,
                enviado_por=registrado.por,
                enviado_el=registrado.el,
                dictamen_por=registrado.cerrado_por if dictamen else None,
                dictamen_el=registrado.cerrado_el if dictamen else None,
                nota=registrado.nota,
                notas=registrado.notas,
                armo=registrado.armo if dictamen else False,
            )
        )
    return Reflejo(caso, tuple(filas))


#: El gancho de `escribir_reflejo` (C11b): recibe las filas de la carpeta antes y después.
AlReflejar = Callable[[Sequence[FilaIndice], Sequence[FilaIndice]], None]


def escribir_reflejo(
    sesion_ins: Session,
    reflejo: Reflejo,
    *,
    forzar: bool = False,
    al_reflejar: AlReflejar | None = None,
) -> bool:
    """Reescribe las filas de `reflejo.caso` con las de `reflejo` (solo `flush`) y dice si lo hizo.
    Sin `forzar`, no escribe si el índice ya refleja más eventos de esa carpeta: es un reflejo
    viejo que llegó tarde. Quien llama toma antes el bloqueo de la instalación, para que la
    comparación y la escritura no se separen. Si escribe, llama a `al_reflejar(antes, después)`
    con las filas de la carpeta (C11b: los avisos por evento, `aplicacion.avisos_por_evento`)."""
    antes = tuple(
        _fila(f)
        for f in sesion_ins.scalars(
            select(FilaIndiceAprobacion).where(FilaIndiceAprobacion.caso == reflejo.caso)
        )
    )
    if not forzar and _eventos(antes) > reflejo.eventos:
        return False
    sesion_ins.execute(
        delete(FilaIndiceAprobacion).where(FilaIndiceAprobacion.caso == reflejo.caso)
    )
    for fila in reflejo.filas:
        sesion_ins.add(
            FilaIndiceAprobacion(
                caso=fila.caso,
                envio_id=fila.envio_id,
                proyecto=fila.proyecto,
                obra=fila.obra,
                version=fila.version,
                total=fila.total,
                moneda=fila.moneda,
                estado=fila.estado,
                enviado_por=fila.enviado_por,
                enviado_el=fila.enviado_el,
                dictamen_por=fila.dictamen_por,
                dictamen_el=fila.dictamen_el,
                nota=fila.nota,
                notas=fila.notas,
                armo=fila.armo,
            )
        )
    sesion_ins.flush()
    if al_reflejar is not None:
        al_reflejar(antes, reflejo.filas)
    return True


def reflejar(
    sesion_ins: Session, caso: str, sesion_caso: Session, *, al_reflejar: AlReflejar | None = None
) -> None:
    """Reescribe las filas de la carpeta `caso` con los envíos de `sesion_caso`, sin guarda de
    frescura (la reposición de las lecturas; solo `flush`)."""
    escribir_reflejo(
        sesion_ins, leer_reflejo(caso, sesion_caso), forzar=True, al_reflejar=al_reflejar
    )


def pendientes(sesion_ins: Session) -> list[FilaIndice]:
    """Los envíos que esperan dictamen, de todas las carpetas, lo más antiguo primero."""
    filas = sesion_ins.scalars(
        select(FilaIndiceAprobacion)
        .where(FilaIndiceAprobacion.estado == "en_aprobacion")
        .order_by(FilaIndiceAprobacion.enviado_el, FilaIndiceAprobacion.caso)
    )
    return [_fila(f) for f in filas]


def de_quien(sesion_ins: Session, usuario: str, limite: int = LIMITE_MIAS) -> list[FilaIndice]:
    """Los últimos `limite` envíos de la cuenta de `usuario` («Nombre <login>»), de todas las
    carpetas, lo más reciente primero."""
    filas = sesion_ins.scalars(
        select(FilaIndiceAprobacion).order_by(
            FilaIndiceAprobacion.enviado_el.desc(), FilaIndiceAprobacion.id.desc()
        )
    )
    suyas = []
    for fila in filas:
        if aprobaciones.misma_cuenta(usuario, fila.enviado_por):
            suyas.append(_fila(fila))
            if len(suyas) == limite:
                break
    return suyas


def _fila(fila: FilaIndiceAprobacion) -> FilaIndice:
    return FilaIndice(
        caso=fila.caso,
        envio_id=fila.envio_id,
        proyecto=fila.proyecto,
        obra=fila.obra,
        version=fila.version,
        total=fila.total,
        moneda=fila.moneda,
        estado=fila.estado,
        enviado_por=fila.enviado_por,
        enviado_el=fila.enviado_el,
        dictamen_por=fila.dictamen_por,
        dictamen_el=fila.dictamen_el,
        nota=fila.nota,
        notas=fila.notas,
        armo=fila.armo,
    )
