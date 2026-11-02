"""El índice de aprobaciones de la instalación: «Por aprobar» de todas las carpetas (MP-4, Tarea
18; choque 14 del plan de montar un presupuesto).

Las aprobaciones viven en cada carpeta de trabajo y no hay transacción común entre una carpeta y
`instalacion.db`. Por eso la carpeta es la fuente de verdad y este índice es su reflejo:

- `reflejar(sesion_ins, caso, sesion_caso)` **reescribe** las filas de la carpeta `caso` desde su
  rastro (`aplicacion.aprobaciones.envios`): borra las suyas y escribe una por envío. Borra ANTES
  de leer la carpeta: el borrado toma el bloqueo de escritura de la instalación, así que dos
  reflejos de la misma carpeta se ordenan y el último lee la carpeta más nueva. Solo `flush`: la
  transacción de la instalación es de quien llama. Las rutas lo llaman después de confirmar la
  carpeta, y `GET /v1/aprobaciones/pendientes` lo llama con la carpeta abierta: si un reflejo se
  perdió (la instalación falló después de confirmar la carpeta), ahí se repone.
- `pendientes(sesion_ins)`: lo que espera dictamen en todas las carpetas, lo más antiguo primero.
- `de_quien(sesion_ins, usuario, limite)`: lo último que envió una cuenta (reconocida por su
  `<login>`, con `aprobaciones.misma_cuenta`), lo más reciente primero.

El total de cada envío es Σ `partida_presupuestada.total` de su versión, sumado en `Decimal`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from aplicacion import aprobaciones
from aplicacion.tablas_indice_aprobacion import FilaIndiceAprobacion
from core import models

__all__ = ["LIMITE_MIAS", "FilaIndice", "de_quien", "pendientes", "reflejar"]

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


def reflejar(sesion_ins: Session, caso: str, sesion_caso: Session) -> None:
    """Reescribe las filas de la carpeta `caso` con los envíos de `sesion_caso` (solo `flush`)."""
    sesion_ins.execute(delete(FilaIndiceAprobacion).where(FilaIndiceAprobacion.caso == caso))
    obras: dict[int, models.Proyecto | None] = {}
    versiones: dict[tuple[int, str], tuple[Decimal, str]] = {}
    for registrado in aprobaciones.envios(sesion_caso):
        if registrado.proyecto_id not in obras:
            obras[registrado.proyecto_id] = sesion_caso.get(models.Proyecto, registrado.proyecto_id)
        obra = obras[registrado.proyecto_id]
        clave = (registrado.proyecto_id, registrado.version)
        if clave not in versiones:
            versiones[clave] = aprobaciones.total_y_moneda(sesion_caso, *clave)
        total, moneda = versiones[clave]
        dictamen = registrado.estado not in ("en_aprobacion", "retirada")
        sesion_ins.add(
            FilaIndiceAprobacion(
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
    sesion_ins.flush()


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
