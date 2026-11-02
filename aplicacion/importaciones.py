"""El registro de importaciones de la obra (rediseño del front, F4, Tarea 10).

Archivos y planos (Tarea 11) muestra qué se importó a la obra: nombre, fecha y hora, quién y qué
produjo, **sin guardar copia del archivo**. Dos cosas entran al registro: el plano que se fusiona
con el espacio del borrador y el cómputo que se lleva a la Hoja (`POST /v1/hoja/llevar` con
`archivo`).

Cómo vive una importación (pregunta abierta 5 del plan):

* Al fusionar o llevar, `anotar` la deja en el borrador vivo (`BorradorVivo.importaciones`), en
  memoria, como «sin guardar». No se escribe nada en la base.
* Al guardar la versión, `registrar_al_guardar` inserta una fila por cada una, con la versión que
  la guardó, **en la misma transacción** que la versión (`con_la_version` engancha el insert al
  `commit` de `hoja.guardar_version` sin tocar `aplicacion/hoja.py`): si algo falla, no queda ni
  la versión ni el registro (C2).
* Si el borrador se descarta, vence o se olvida, las importaciones se van con él: no llegaron a
  ninguna versión y no dejan rastro.

`importaciones_de_la_obra` junta las guardadas de la obra y las de sus borradores vivos aún sin
guardar, de la más nueva a la más vieja. Leer no escribe ni crea la tabla.

Sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from aplicacion.tablas_importaciones import (
    ImportacionGuardada,
    crear_esquema_importaciones,
    hay_tabla_de_importaciones,
)
from core import models

if TYPE_CHECKING:
    from aplicacion.hoja_borradores import BorradorVivo

__all__ = [
    "MAX_NOMBRE",
    "ImportacionDeObra",
    "TipoDeImportacion",
    "anotar",
    "con_la_version",
    "importaciones_de_la_obra",
    "nombre_de_archivo",
    "nueva",
    "registrar_al_guardar",
    "resumen_de_computo",
    "resumen_de_plano",
]

TipoDeImportacion = Literal["plano", "computo"]

MAX_NOMBRE = 255
#: Un nombre de archivo, no una ruta: sin barras, sin «:» (unidad de Windows) ni controles.
_NO_ES_NOMBRE = re.compile(r"[/\\:\x00-\x1f\x7f]")


@dataclass(frozen=True, slots=True)
class ImportacionDeObra:
    """Una importación de la obra: lo que el registro muestra."""

    tipo: TipoDeImportacion
    archivo: str  # solo el nombre, nunca una ruta
    fecha_hora: datetime  # la del servidor
    usuario: str
    resumen: str  # «33 filas en el espacio» / «18 partidas llevadas»
    version: str | None  # la versión que la guardó; None = sigue en un borrador sin guardar
    guardada: bool


def nombre_de_archivo(valor: str) -> str:
    """El nombre tal cual si es un nombre de archivo; `ValueError` (sin eco) si trae una ruta, un
    componente `.`/`..`, caracteres de control, queda en blanco o pasa de `MAX_NOMBRE`."""
    if (
        not valor.strip()
        or len(valor) > MAX_NOMBRE
        or _NO_ES_NOMBRE.search(valor)
        or valor.strip() in {".", ".."}
    ):
        raise ValueError("no es un nombre de archivo")
    return valor


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def resumen_de_plano(*, filas: int, sin_reconocer: int) -> str:
    """«34 filas en el espacio; 2 sin reconocer» (lo no reconocido solo si lo hay)."""
    texto = f"{_plural(filas, 'fila', 'filas')} en el espacio"
    return f"{texto}; {sin_reconocer} sin reconocer" if sin_reconocer else texto


def resumen_de_computo(partidas: int) -> str:
    """«18 partidas llevadas»."""
    return f"{_plural(partidas, 'partida llevada', 'partidas llevadas')}"


def nueva(
    tipo: TipoDeImportacion,
    archivo: str,
    usuario: str,
    resumen: str,
    *,
    ahora: datetime | None = None,
) -> ImportacionDeObra:
    """Una importación recién hecha: sin guardar, con la fecha y hora del servidor."""
    return ImportacionDeObra(
        tipo=tipo,
        archivo=nombre_de_archivo(archivo),
        fecha_hora=ahora or datetime.now(),
        usuario=usuario,
        resumen=resumen,
        version=None,
        guardada=False,
    )


def anotar(vivo: BorradorVivo, imp: ImportacionDeObra) -> BorradorVivo:
    """Suma `imp` a las importaciones del borrador y lo devuelve. Quien llama tiene el cerrojo del
    borrador (lo toma ya para cambiarlo)."""
    vivo.importaciones = (*vivo.importaciones, imp)
    return vivo


def registrar_al_guardar(sesion: Session, vivo: BorradorVivo, version_id: int) -> None:
    """Inserta una fila por cada importación del borrador, con la versión `version_id` (el `id` del
    presupuesto que lo guardó). **Sin `commit`**: viaja en la transacción de la versión. Sin
    importaciones no toca la base; sin la tabla (base sin migrar) la crea."""
    if not vivo.importaciones:
        return
    if not hay_tabla_de_importaciones(sesion):
        crear_esquema_importaciones(sesion.connection())
    sesion.add_all(
        ImportacionGuardada(
            version_id=version_id,
            tipo=i.tipo,
            archivo=i.archivo,
            fecha_hora=i.fecha_hora,
            usuario=i.usuario,
            resumen=i.resumen,
        )
        for i in vivo.importaciones
    )
    sesion.flush()


@contextmanager
def con_la_version(sesion: Session, vivo: BorradorVivo) -> Iterator[None]:
    """Mientras dura, el `commit` de la sesión escribe antes las importaciones del borrador con la
    versión que ese `commit` confirma (la primera presupuesto nueva de la obra), en la misma
    transacción. `hoja.guardar_version` y `crear_primera_version` confirman por su cuenta: este
    gancho evita tocarlas. Si el insert falla, falla el `commit` y ellas deshacen todo."""
    if not vivo.importaciones:
        yield
        return
    proyecto = sesion.scalar(
        select(models.Proyecto.id).where(models.Proyecto.nombre == vivo.proyecto)
    )
    ultimo = (
        sesion.scalar(
            select(func.max(models.Presupuesto.id)).where(
                models.Presupuesto.proyecto_id == proyecto
            )
        )
        or 0
    )
    hecho = False

    def antes_de_confirmar(s: Session) -> None:
        nonlocal hecho
        if hecho:
            return
        s.flush()  # la versión nueva ya tiene su id
        nueva_version = s.scalar(
            select(func.max(models.Presupuesto.id)).where(
                models.Presupuesto.proyecto_id == proyecto, models.Presupuesto.id > ultimo
            )
        )
        if nueva_version is None:  # un commit anterior a la versión (p. ej. la conversión)
            return
        hecho = True
        registrar_al_guardar(s, vivo, nueva_version)

    event.listen(sesion, "before_commit", antes_de_confirmar)
    try:
        yield
    finally:
        event.remove(sesion, "before_commit", antes_de_confirmar)


def importaciones_de_la_obra(
    sesion: Session, proyecto: str, vivos: Iterable[BorradorVivo]
) -> list[ImportacionDeObra]:
    """Las importaciones de la obra `proyecto` (su nombre): las guardadas, con su versión, y las de
    los borradores `vivos` de esa obra que aún no se guardaron, de la más nueva a la más vieja.
    Solo lee: sin la tabla (base sin migrar) no hay guardadas."""
    lista: list[ImportacionDeObra] = []
    if hay_tabla_de_importaciones(sesion):
        filas = sesion.execute(
            select(ImportacionGuardada, models.Presupuesto.codigo)
            .join(models.Presupuesto, models.Presupuesto.id == ImportacionGuardada.version_id)
            .join(models.Proyecto, models.Proyecto.id == models.Presupuesto.proyecto_id)
            .where(models.Proyecto.nombre == proyecto)
        )
        lista += [
            ImportacionDeObra(
                tipo=f.tipo,  # type: ignore[arg-type]
                archivo=f.archivo,
                fecha_hora=f.fecha_hora,
                usuario=f.usuario,
                resumen=f.resumen,
                version=codigo,
                guardada=True,
            )
            for f, codigo in filas
        ]
    for vivo in vivos:
        if vivo.proyecto == proyecto and vivo.guardado_como is None:
            lista += vivo.importaciones
    return sorted(lista, key=lambda i: i.fecha_hora, reverse=True)
