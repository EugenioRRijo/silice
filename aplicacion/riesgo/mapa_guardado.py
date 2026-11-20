"""El mapa de series que «Riesgo de la obra» recuerda (mejora de la DS-81; DS-90 a DS-93).

- **La clave** es la versión (DS-90): cada versión recuerda el último mapa que se usó con ella. Una
  versión que todavía no tiene el suyo toma el último guardado en **otra versión de la misma obra**
  (una versión nueva suele traer los mismos insumos), y se dice de cuál. Un mapa propio vacío manda
  sobre el de las otras: la persona decidió no usar series.
- **Se guarda** aparte del cálculo (DS-91): la pantalla lo manda después de una proyección o una
  comprobación que salió bien. Solo inserción, como los tramos viales: guardar otro mapa es otra
  fila y manda el último; guardar el mismo que ya era el último de la versión no escribe nada.
- **Al precargar** (DS-92) se deja fuera, y se dice, la pareja cuyo insumo ya no está en la versión
  o cuya serie ya no se ofrece. Una serie que se ofrece pero aún no tiene historia sí se precarga:
  la elección sigue valiendo y la proyección dice qué falta y dónde se carga (DS-89).

No valida los insumos al guardar (eso pediría recalcular el presupuesto con el bloqueo de escritura
tomado): los filtra al leer. Las series sí, contra las que admite la moneda (`series_admitidas`).
`guardar_mapa` confirma; si algo falla, deshace todo.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.tablas_riesgo import (
    LARGO_USUARIO,
    GuardadoDeMapa,
    SerieDeInsumo,
    crear_esquema_riesgo,
    hay_tablas_de_riesgo,
)
from core import models

__all__ = [
    "SIN_INSUMO",
    "SIN_SERIE",
    "Descartado",
    "MapaGuardado",
    "MapaPrecargado",
    "guardar_mapa",
    "precargar",
    "ultimo_mapa",
]

#: Motivos por los que una pareja guardada no se precarga.
SIN_INSUMO = "insumo"  # la versión ya no tiene ese insumo
SIN_SERIE = "serie"  # la serie ya no se ofrece


@dataclass(frozen=True)
class MapaGuardado:
    mapa: dict[str, str]
    version: str  # el código de la versión en que se guardó
    usuario: str
    fecha_hora: datetime


@dataclass(frozen=True)
class Descartado:
    insumo: str
    serie: str
    motivo: str  # `SIN_INSUMO` o `SIN_SERIE`


@dataclass(frozen=True)
class MapaPrecargado:
    mapa: dict[str, str]
    de_version: str
    descartados: tuple[Descartado, ...]


def _mapa_de(sesion: Session, guardado_id: int) -> dict[str, str]:
    filas = sesion.execute(
        select(SerieDeInsumo.insumo, SerieDeInsumo.serie)
        .where(SerieDeInsumo.guardado_id == guardado_id)
        .order_by(SerieDeInsumo.id)
    ).all()
    return {insumo: serie for insumo, serie in filas}


def _ultimo_de_la_version(sesion: Session, version_id: int) -> GuardadoDeMapa | None:
    return sesion.scalars(
        select(GuardadoDeMapa)
        .where(GuardadoDeMapa.version_id == version_id)
        .order_by(GuardadoDeMapa.fecha_hora.desc(), GuardadoDeMapa.id.desc())
    ).first()


def ultimo_mapa(sesion: Session, version_id: int) -> MapaGuardado | None:
    """El último mapa guardado de la versión; sin él, el último de otra versión de la misma obra;
    sin ninguno (o sin las tablas), `None`."""
    if not hay_tablas_de_riesgo(sesion):
        return None
    fila = sesion.execute(
        select(GuardadoDeMapa, models.Presupuesto.codigo)
        .join(models.Presupuesto, models.Presupuesto.id == GuardadoDeMapa.version_id)
        .where(GuardadoDeMapa.version_id == version_id)
        .order_by(GuardadoDeMapa.fecha_hora.desc(), GuardadoDeMapa.id.desc())
    ).first()
    if fila is None:
        proyecto_id = sesion.scalar(
            select(models.Presupuesto.proyecto_id).where(models.Presupuesto.id == version_id)
        )
        fila = sesion.execute(
            select(GuardadoDeMapa, models.Presupuesto.codigo)
            .join(models.Presupuesto, models.Presupuesto.id == GuardadoDeMapa.version_id)
            .where(models.Presupuesto.proyecto_id == proyecto_id)
            .order_by(GuardadoDeMapa.fecha_hora.desc(), GuardadoDeMapa.id.desc())
        ).first()
    if fila is None:
        return None
    guardado, codigo = fila
    return MapaGuardado(
        _mapa_de(sesion, guardado.id), codigo, guardado.usuario, guardado.fecha_hora
    )


def precargar(
    guardado: MapaGuardado, insumos: Collection[str], series: Collection[str]
) -> MapaPrecargado:
    """Lo que se precarga del mapa guardado en una versión con esos `insumos` (descripciones y
    códigos de componentes) y esas `series` ofrecidas, y lo que se deja fuera, en el orden en que se
    guardó."""
    vigentes, descartados = {}, []
    for insumo, serie in guardado.mapa.items():
        if insumo not in insumos:
            descartados.append(Descartado(insumo, serie, SIN_INSUMO))
        elif serie not in series:
            descartados.append(Descartado(insumo, serie, SIN_SERIE))
        else:
            vigentes[insumo] = serie
    return MapaPrecargado(vigentes, guardado.version, tuple(descartados))


def guardar_mapa(
    sesion: Session,
    version_id: int,
    mapa: Mapping[str, str],
    *,
    series_admitidas: Collection[str],
    usuario: str,
    ahora: datetime,
) -> bool:
    """Guarda `mapa` como el último de la versión y confirma. False (y nada escrito) si es el mismo
    que ya era su último. `ValueError` si una serie no está en `series_admitidas` o el usuario es
    demasiado largo; en cualquier fallo no queda nada."""
    try:
        for serie in mapa.values():
            if serie not in series_admitidas:
                raise ValueError(
                    f"La serie «{serie[:40]}» no se ofrece para esta versión: "
                    "elija una de la lista."
                )
        if len(usuario) > LARGO_USUARIO:
            raise ValueError(f"el usuario pasa de {LARGO_USUARIO} caracteres")
        if not hay_tablas_de_riesgo(sesion):
            crear_esquema_riesgo(sesion.connection())
        anterior = _ultimo_de_la_version(sesion, version_id)
        if anterior is not None and _mapa_de(sesion, anterior.id) == dict(mapa):
            sesion.rollback()
            return False
        guardado = GuardadoDeMapa(version_id=version_id, usuario=usuario, fecha_hora=ahora)
        sesion.add(guardado)
        sesion.flush()
        sesion.add_all(
            SerieDeInsumo(guardado_id=guardado.id, insumo=insumo, serie=serie)
            for insumo, serie in mapa.items()
        )
        sesion.commit()
    except BaseException:
        sesion.rollback()
        raise
    return True
