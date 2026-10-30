"""Proyectos del caso abierto, sin Streamlit (RF-63, spec del sprint final §9.7 y §10).

Lo que la herramienta **Proyecto** y el boton **Auditar** de la barra superior necesitan de la base:
crear un proyecto con nombre unico y no vacio, listar los que hay, y la version vigente con el
resumen de su informe de auditoria. Cada funcion abre la base en `ruta` y la cierra (el motor no
va a la sesion; ver `ui.caso`), y **ninguna crea el archivo**: un caso con una errata en la ruta
daria una base vacia en silencio.

La **version vigente** de un proyecto es, mientras no exista el modelo de versiones editables de
SF3, el ultimo presupuesto guardado (el de mayor `id`) que el usuario no descarto (UC-02 7a). Cuando
SF3 aporte la suya, esta funcion es el unico punto que cambia.

El nombre se compara sin distinguir mayusculas ni espacios sobrantes: «Torre B» y «torre b» son el
mismo proyecto para quien lo busca en una lista, aunque la restriccion unica de la base (que
distingue mayusculas) no los confunda.

Sin Streamlit ni nada de `ui/`; lo vigila `tests/unit/test_arquitectura.py`. Vivia en
`ui/proyectos.py` (que hoy lo reexporta) hasta la sesion 2b (RM-1): la API lo usa para
`GET /v1/proyectos`.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core import models
from core.budget import crear_proyecto
from core.budget.moneda import declarar_moneda
from core.catalog import abrir_sesion, crear_motor
from core.catalog.moneda import MONEDAS
from core.contracts import Severidad
from core.contracts.dominio import Dominio
from operacion.base_datos import motor_solo_lectura

_registro = logging.getLogger(__name__)

#: Las monedas que ofrece la barra al crear un proyecto (sin valor por defecto en la interfaz).
MONEDAS_DEL_PROYECTO = MONEDAS
#: Quien declara la moneda al crear desde la barra: en la 0.6.0 no hay cuentas (S3 las trae).
RESPONSABLE_DE_LA_INTERFAZ = "interfaz (sin cuentas hasta S3)"


class ProyectoInvalido(ValueError):  # noqa: N818
    """El proyecto no se pudo crear; el mensaje dice que paso y como arreglarlo."""


@dataclass(frozen=True, slots=True)
class VersionVigente:
    """La version vigente de un proyecto: el codigo de su presupuesto y su fecha."""

    codigo: str
    fecha: date


@dataclass(frozen=True, slots=True)
class ResumenAuditoria:
    """Hallazgos del informe de la version vigente, contados por severidad."""

    version: VersionVigente
    por_severidad: dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.por_severidad.values())


def _url(ruta: Path) -> str:
    return f"sqlite:///{ruta.as_posix()}"


def listar_proyectos(ruta: Path) -> list[str]:
    """Los nombres de los proyectos del caso, en orden alfabetico; vacia si el caso no existe."""
    if not ruta.exists():
        return []
    motor = crear_motor(_url(ruta))
    try:
        with abrir_sesion(motor) as sesion:
            nombres = sesion.scalars(select(models.Proyecto.nombre)).all()
    finally:
        motor.dispose()
    return sorted(nombres, key=str.casefold)


MENSAJE_NOMBRE_VACIO = "Escriba un nombre para la obra: no puede quedar vacío."
MENSAJE_MONEDA = "Elija la moneda: Bs o USD."
MENSAJE_TIPO_DE_OBRA = "El tipo de obra no es uno de los de la lista."


class ProyectoRepetido(ProyectoInvalido):
    """Ya hay un proyecto con ese nombre (sin distinguir mayúsculas): la API lo dice con un 409."""


def _limpiar_nombre(nombre: str) -> str:
    limpio = " ".join(nombre.split())  # sin espacios sobrantes ni dobles
    if not limpio:
        raise ProyectoInvalido(MENSAJE_NOMBRE_VACIO)
    return limpio


def crear_proyecto_en_sesion(
    sesion: Session,
    nombre: str,
    moneda: str | None,
    dominio: str,
    descripcion: str,
    responsable: str,
    antes_de_confirmar: Callable[[Session, models.Proyecto], None] | None = None,
) -> models.Proyecto:
    """Crea el proyecto en la base de `sesion` y confirma, todo o nada (BCP-3, diseño §5.1).

    Normaliza el nombre, compara sin distinguir mayúsculas (`casefold`, en Python: `lower()` de
    SQLite solo conoce el ASCII), crea el proyecto con `core.budget.crear_proyecto` y, con
    `moneda`, la declara en `moneda_proyecto` firmada por `responsable` (RF-82); si algo falla se
    deshace todo y no queda el proyecto. `ProyectoRepetido` si el nombre ya existe (también si dos
    peticiones lo crean a la vez y la restricción única de la base gana); `ProyectoInvalido` si el
    nombre queda vacío, la moneda no es Bs ni USD o el tipo de obra no es uno de la lista. Quien
    llama con una sesión de escritura (`BEGIN IMMEDIATE`) serializa la comparación y el alta.
    `antes_de_confirmar(sesion, proyecto)` (MOD-3a: la ficha de la obra) corre con el proyecto ya
    con `id` y antes del `commit`, en la misma transacción: si falla, tampoco queda el proyecto.
    """
    limpio = _limpiar_nombre(nombre)
    if moneda is not None and moneda not in MONEDAS_DEL_PROYECTO:
        raise ProyectoInvalido(MENSAJE_MONEDA)
    if dominio != "" and dominio not in {d.value for d in Dominio}:
        raise ProyectoInvalido(MENSAJE_TIPO_DE_OBRA)
    try:
        for otro in sesion.scalars(select(models.Proyecto)):
            if otro.nombre.casefold() == limpio.casefold():
                raise ProyectoRepetido(
                    f"Ya existe una obra llamada «{otro.nombre}»: elija otro nombre o abra esa."
                )
        try:
            proyecto = crear_proyecto(sesion, limpio, descripcion, dominio)
            if moneda is not None:
                declarar_moneda(sesion, proyecto, moneda, responsable=responsable)
            if antes_de_confirmar is not None:
                antes_de_confirmar(sesion, proyecto)
        except ValueError as error:  # el núcleo repite las reglas; por si cambian
            raise ProyectoInvalido(str(error)) from error
        sesion.commit()
    except IntegrityError:  # dos peticiones a la vez con el mismo nombre
        sesion.rollback()
        raise ProyectoRepetido(
            f"Ya existe una obra llamada «{limpio}»: elija otro nombre o abra esa."
        ) from None
    except BaseException:
        sesion.rollback()
        raise
    return proyecto


def crear_proyecto_nuevo(
    ruta: Path,
    nombre: str,
    moneda: str | None = None,
    responsable: str = RESPONSABLE_DE_LA_INTERFAZ,
) -> str:
    """Crea el proyecto y devuelve su nombre limpio. Con `moneda`, la declara en `moneda_proyecto`
    (UC-01 paso 1, S1); sin ella el proyecto queda como antes (USD por defecto de `elaborar`).
    `ProyectoInvalido` si el nombre queda vacio, ya existe (sin distinguir mayusculas), la moneda
    no es Bs ni USD o el caso no existe. `responsable` firma la declaración de la moneda (RF-82):
    la barra pasa el usuario de la sesión con el acceso encendido."""
    limpio = _limpiar_nombre(nombre)
    if not ruta.exists():
        raise ProyectoInvalido(
            f"La carpeta de trabajo {ruta} no existe todavía: abra o cree una carpeta de trabajo "
            "antes de crear una obra."
        )
    motor = crear_motor(_url(ruta))
    try:
        with abrir_sesion(motor) as sesion:
            crear_proyecto_en_sesion(sesion, limpio, moneda, "", "", responsable)
    finally:
        motor.dispose()
    return limpio


def resolver_proyecto(sesion: Session, referencia: str) -> models.Proyecto | None:
    """El proyecto al que apunta `referencia`, o `None` si no existe (V-11).

    La interfaz nueva guarda en la cabecera el `codigo` que da `GET /v1/proyectos` (el `id` como
    texto), pero las rutas historicas reciben el nombre. Se acepta cualquiera de los dos:

    1. si `referencia` son solo digitos ASCII y hay un proyecto con ese `id`, es ese proyecto;
    2. si no, el proyecto cuyo nombre es **exactamente** `referencia`.

    Si un nombre es un numero que coincide con el `id` de otro proyecto, **el codigo gana**: es
    la unica lectura sin ambiguedad (el codigo es el que ofrece `GET /v1/proyectos`); ese proyecto
    sigue alcanzable por su propio codigo. No escribe.
    """
    if referencia.isascii() and referencia.isdigit():
        porcodigo = sesion.get(models.Proyecto, int(referencia))
        if porcodigo is not None:
            return porcodigo
    return sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == referencia)
    ).first()


def _vigente(sesion, nombre: str) -> models.Presupuesto | None:
    descartados = select(models.DescarteVersion.presupuesto_id)
    return sesion.scalar(
        select(models.Presupuesto)
        .join(models.Proyecto)
        .where(models.Proyecto.nombre == nombre, models.Presupuesto.id.not_in(descartados))
        .order_by(models.Presupuesto.id.desc())
        .limit(1)
    )


@dataclass(frozen=True, slots=True)
class ProyectoDelCaso:
    """Un proyecto con su version vigente, para el selector de la interfaz nueva
    (`GET /v1/proyectos`). Sin version vigente, los tres ultimos campos son `None`."""

    id: int
    nombre: str
    version_id: int | None
    version_codigo: str | None
    version_fecha: date | None


def proyectos_del_caso(sesion: Session) -> list[ProyectoDelCaso]:
    """Los proyectos de la base de `sesion` en orden alfabetico (como `listar_proyectos`), cada
    uno con su version vigente. No escribe. La API la llama con la sesion del caso de la
    peticion (RM-2), que no es necesariamente el del proceso."""
    filas = []
    for proyecto in sesion.scalars(select(models.Proyecto)):
        vigente = _vigente(sesion, proyecto.nombre)
        filas.append(
            ProyectoDelCaso(
                id=proyecto.id,
                nombre=proyecto.nombre,
                version_id=None if vigente is None else vigente.id,
                version_codigo=None if vigente is None else vigente.codigo,
                version_fecha=None if vigente is None else vigente.fecha,
            )
        )
    return sorted(filas, key=lambda fila: fila.nombre.casefold())


def version_vigente(ruta: Path, nombre: str) -> VersionVigente | None:
    """La version vigente del proyecto, o `None` si no tiene ninguna (o no existe)."""
    if not ruta.exists():
        return None
    motor = crear_motor(_url(ruta))
    try:
        with abrir_sesion(motor) as sesion:
            modelo = _vigente(sesion, nombre)
            return None if modelo is None else VersionVigente(modelo.codigo, modelo.fecha)
    finally:
        motor.dispose()


def resumen_auditoria(ruta: Path, nombre: str) -> ResumenAuditoria | None:
    """Los hallazgos del informe de la version vigente por severidad; `None` sin version."""
    if not ruta.exists():
        return None
    motor = crear_motor(_url(ruta))
    try:
        with abrir_sesion(motor) as sesion:
            modelo = _vigente(sesion, nombre)
            if modelo is None:
                return None
            cuenta = Counter(h.severidad for h in modelo.hallazgos)
            return ResumenAuditoria(
                VersionVigente(modelo.codigo, modelo.fecha),
                {s.name: cuenta.get(int(s), 0) for s in Severidad},
            )
    finally:
        motor.dispose()


@dataclass(frozen=True, slots=True)
class ObraDeCarpeta:
    """Una obra con la carpeta que la guarda. `carpeta` es el nombre que acepta
    `POST /v1/casos/actual`; `None` es la carpeta de la empresa (la del proceso)."""

    carpeta: str | None
    obra_id: int
    obra: str
    version_codigo: str | None


def carpetas_con_archivo(
    carpetas: list[tuple[str | None, Path]],
) -> list[tuple[str | None, Path]]:
    """Las carpetas cuyo archivo existe. Una sin archivo (la de la empresa en la demostración, que
    aún no se creó) no tiene obras ni pendientes: no es un fallo y no se avisa. Una corrupta sí
    existe y la tratan los lectores.

    Cuando la lista la arma `_carpetas_visibles` con `CAMBIAR_CASO`, las demás carpetas ya vienen
    filtradas de `listar_casos` (que solo devuelve archivos `.db` existentes) y este filtro solo
    puede quitar la de la empresa (`None`). Sin `CAMBIAR_CASO` la carpeta abierta no sale de
    `listar_casos`; por eso se aplica a toda la lista, sin depender de quién la armó."""
    return [(nombre, ruta) for nombre, ruta in carpetas if Path(ruta).is_file()]


def obras_de_las_carpetas(carpetas: list[tuple[str | None, Path]]) -> list[ObraDeCarpeta]:
    """Las obras de cada carpeta (`(nombre, ruta)`), abiertas una a una en **solo lectura**
    (`motor_solo_lectura`: URI `mode=ro`, sin migrar ni crear `-wal`/`-shm`) y cerradas al
    terminar. Orden: la carpeta de la empresa (`None`), luego las demás por nombre, y dentro de
    cada una las obras por nombre sin distinguir mayúsculas. La de archivo ausente no tiene obras:
    se salta sin aviso. Se omite (y queda en el registro) la
    carpeta que no se puede leer: archivo no SQLite, tabla o columna que falta. Una más
    nueva que abre sin error se lista; abrirla dará el error de `preparar_base`."""
    filas: list[ObraDeCarpeta] = []
    for nombre, ruta in sorted(
        carpetas_con_archivo(carpetas), key=lambda c: (c[0] is not None, (c[0] or "").casefold())
    ):
        motor = motor_solo_lectura(ruta)
        try:
            with abrir_sesion(motor) as sesion:
                filas.extend(
                    ObraDeCarpeta(nombre, p.id, p.nombre, p.version_codigo)
                    for p in proyectos_del_caso(sesion)
                )
        except SQLAlchemyError:
            _registro.warning("Se omite la carpeta «%s»: no se pudo leer.", ruta.name)
        finally:
            motor.dispose()
    return filas
