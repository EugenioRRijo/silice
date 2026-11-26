"""La actividad de una cuenta, como la página de actividad de GitHub (C10; solo lectura).

Junta, por día, lo que hizo una cuenta con datos que **ya se guardan**; no escribe nada ni crea
tablas. De dónde sale cada tipo de evento:

- `version_guardada`: `eslabon_version` (la carpeta abierta), `usuario` y `fecha_hora`.
- `version_enviada`: `mp_indice_aprobacion` (`instalacion.db`), `enviado_por` y `enviado_el`.
- `dictamen`: `mp_indice_aprobacion` (`instalacion.db`), `dictamen_por` y `dictamen_el`.
- `auditoria`: `auditoria_libro` (`instalacion.db`), `usuario` y `fecha_hora`.

Las versiones guardadas viven en cada carpeta de trabajo y no hay una vista común a todas (como
con las aprobaciones, `aplicacion.indice_aprobaciones`): se cuentan las de la carpeta que se pasa
en `caso`; sin carpeta no se cuentan. El obra y el código de la versión del texto salen de
`proyecto.nombre` y `presupuesto.codigo`; el archivo de la auditoría, de `nombre_archivo`.

La persona se reconoce por su `<login>` (los textos guardados son `Nombre <login>`), así que un
cambio de nombre no la oculta; un texto sin `<login>` se compara completo
(`aplicacion.revision.login_de`).

`armar` es pura: recibe los eventos ya leídos y los vuelve días, cifras y lista (lo más reciente
primero, con un tope).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import DateTime, Integer, String, column, select, table
from sqlalchemy.orm import Session

from aplicacion.revision import login_de
from aplicacion.tablas_indice_aprobacion import FilaIndiceAprobacion
from core import models
from core.models.cadena import EslabonVersion
from seguridad.cuentas import normalizar_login
from seguridad.modelo import Usuario

__all__ = [
    "LIMITE_EVENTOS",
    "TIPOS",
    "Actividad",
    "Cifras",
    "DiaConActividad",
    "Evento",
    "actividad_de",
    "armar",
    "cuenta_existe",
]

VERSION_GUARDADA = "version_guardada"
VERSION_ENVIADA = "version_enviada"
DICTAMEN = "dictamen"
AUDITORIA = "auditoria"
#: Los tipos de evento, en el orden de las cifras.
TIPOS = (VERSION_GUARDADA, VERSION_ENVIADA, DICTAMEN, AUDITORIA)
#: Cuántos eventos de la lista devuelve como máximo (las cifras y los días cuentan todos).
LIMITE_EVENTOS = 500

#: `auditoria_libro` (de `fusion.historial_modelo`): `aplicacion` no importa `fusion`
#: (`tests/unit/test_arquitectura.py`), así que se declaran aquí solo las columnas que se leen.
_AUDITORIA_LIBRO = table(
    "auditoria_libro",
    column("usuario", String),
    column("fecha_hora", DateTime),
    column("nombre_archivo", String),
    column("errores", Integer),
)

_DICTAMENES = {
    "aprobada": "aprobó",
    "aprobada_con_observaciones": "aprobó con observaciones",
    "devuelta": "devolvió",
}


@dataclass(frozen=True, slots=True)
class Evento:
    """Una cosa que hizo la cuenta: cuándo, de qué tipo, en qué obra o archivo y el texto corto."""

    fecha_hora: datetime
    tipo: str
    obra: str
    archivo: str
    texto: str


@dataclass(frozen=True, slots=True)
class DiaConActividad:
    fecha: date
    cuantos: int


@dataclass(frozen=True, slots=True)
class Cifras:
    versiones_guardadas: int
    versiones_enviadas: int
    dictamenes: int
    auditorias: int


@dataclass(frozen=True, slots=True)
class Actividad:
    """`dias`: solo los días con actividad, del más antiguo al más nuevo. `eventos`: lo más
    reciente primero, hasta el tope; `recortado` dice si hubo más que los devueltos."""

    dias: tuple[DiaConActividad, ...]
    cifras: Cifras
    eventos: tuple[Evento, ...]
    recortado: bool


def cuenta_existe(instalacion: Session, login: str) -> bool:
    """Si hay una cuenta con ese `login` (sin importar mayúsculas ni espacios en los bordes)."""
    normal = normalizar_login(login)
    return (
        instalacion.scalars(select(Usuario.id).where(Usuario.login == normal)).first() is not None
    )


def armar(
    eventos: Iterable[Evento],
    desde: date,
    hasta: date,
    *,
    limite_eventos: int = LIMITE_EVENTOS,
) -> Actividad:
    """Los días, las cifras y la lista de los `eventos` que caen entre `desde` y `hasta`, ambos
    días incluidos. `ValueError` si `desde` es posterior a `hasta`."""
    if desde > hasta:
        raise ValueError("La fecha «desde» no puede ser posterior a «hasta».")
    dentro = [e for e in eventos if desde <= e.fecha_hora.date() <= hasta]
    por_dia = Counter(e.fecha_hora.date() for e in dentro)
    por_tipo = Counter(e.tipo for e in dentro)
    ordenados = sorted(
        dentro, key=lambda e: (e.fecha_hora, TIPOS.index(e.tipo), e.texto), reverse=True
    )
    return Actividad(
        dias=tuple(DiaConActividad(dia, por_dia[dia]) for dia in sorted(por_dia)),
        cifras=Cifras(
            versiones_guardadas=por_tipo[VERSION_GUARDADA],
            versiones_enviadas=por_tipo[VERSION_ENVIADA],
            dictamenes=por_tipo[DICTAMEN],
            auditorias=por_tipo[AUDITORIA],
        ),
        eventos=tuple(ordenados[:limite_eventos]),
        recortado=len(ordenados) > limite_eventos,
    )


def actividad_de(
    instalacion: Session,
    usuario: str,
    desde: date,
    hasta: date,
    *,
    caso: Session | None = None,
) -> Actividad:
    """Lo que hizo la cuenta `usuario` (su login) entre `desde` y `hasta`, ambos incluidos. Solo
    lee. `caso` es la sesión de la carpeta de trabajo abierta: sin ella no se cuentan las
    versiones guardadas."""
    if desde > hasta:
        raise ValueError("La fecha «desde» no puede ser posterior a «hasta».")
    login = normalizar_login(usuario)
    inicio = datetime.combine(desde, time.min)
    fin = datetime.combine(hasta + timedelta(days=1), time.min)
    eventos: list[Evento] = []
    if caso is not None:
        eventos += _versiones_guardadas(caso, login, inicio, fin)
    eventos += _aprobaciones(instalacion, login, inicio, fin)
    eventos += _auditorias(instalacion, login, inicio, fin)
    return armar(eventos, desde, hasta)


def _es_de(login: str, guardado: str | None) -> bool:
    """Si el texto guardado (`Nombre <login>`) es de la cuenta `login`."""
    if not guardado:
        return False
    propio = login_de(guardado)
    if propio is not None:
        return normalizar_login(propio) == login
    return normalizar_login(guardado) == login


def _versiones_guardadas(
    caso: Session, login: str, inicio: datetime, fin: datetime
) -> list[Evento]:
    filas = caso.execute(
        select(
            EslabonVersion.usuario,
            EslabonVersion.fecha_hora,
            models.Presupuesto.codigo,
            models.Proyecto.nombre,
        )
        .join(models.Presupuesto, models.Presupuesto.id == EslabonVersion.presupuesto_id)
        .join(models.Proyecto, models.Proyecto.id == EslabonVersion.proyecto_id)
        .where(EslabonVersion.fecha_hora >= inicio, EslabonVersion.fecha_hora < fin)
    )
    return [
        Evento(el, VERSION_GUARDADA, obra, "", f"guardó la versión {codigo} de {obra}")
        for quien, el, codigo, obra in filas
        if _es_de(login, quien)
    ]


def _aprobaciones(
    instalacion: Session, login: str, inicio: datetime, fin: datetime
) -> list[Evento]:
    eventos: list[Evento] = []
    filas = instalacion.scalars(
        select(FilaIndiceAprobacion).where(
            (FilaIndiceAprobacion.enviado_el >= inicio) & (FilaIndiceAprobacion.enviado_el < fin)
            | (FilaIndiceAprobacion.dictamen_el >= inicio)
            & (FilaIndiceAprobacion.dictamen_el < fin)
        )
    )
    for fila in filas:
        de = f"la versión {fila.version} de {fila.obra}"
        if inicio <= fila.enviado_el < fin and _es_de(login, fila.enviado_por):
            eventos.append(
                Evento(fila.enviado_el, VERSION_ENVIADA, fila.obra, "", f"envió {de} a aprobación")
            )
        verbo = _DICTAMENES.get(fila.estado)
        cierre = fila.dictamen_el
        if (
            verbo is not None
            and cierre is not None
            and inicio <= cierre < fin
            and _es_de(login, fila.dictamen_por)
        ):
            eventos.append(Evento(cierre, DICTAMEN, fila.obra, "", f"{verbo} {de}"))
    return eventos


def _auditorias(instalacion: Session, login: str, inicio: datetime, fin: datetime) -> list[Evento]:
    t = _AUDITORIA_LIBRO.c
    filas = instalacion.execute(
        select(t.usuario, t.fecha_hora, t.nombre_archivo, t.errores).where(
            t.fecha_hora >= inicio, t.fecha_hora < fin
        )
    )
    return [
        Evento(el, AUDITORIA, "", archivo, f"auditó {archivo}: {_errores(errores)}")
        for quien, el, archivo, errores in filas
        if _es_de(login, quien)
    ]


def _errores(cuantos: int) -> str:
    if cuantos == 0:
        return "sin errores"
    return f"{cuantos} error" if cuantos == 1 else f"{cuantos} errores"
