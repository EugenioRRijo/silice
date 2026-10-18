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

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget import crear_proyecto
from core.budget.moneda import declarar_moneda
from core.catalog import abrir_sesion, crear_motor
from core.catalog.moneda import MONEDAS
from core.contracts import Severidad

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
    limpio = " ".join(nombre.split())  # sin espacios sobrantes ni dobles
    if not limpio:
        raise ProyectoInvalido("Escriba un nombre para el proyecto: no puede quedar vacio.")
    if not ruta.exists():
        raise ProyectoInvalido(
            f"El caso {ruta} no existe todavia: abra o siembre un caso en el Inicio antes de "
            "crear un proyecto."
        )
    motor = crear_motor(_url(ruta))
    try:
        with abrir_sesion(motor) as sesion:
            # En Python: `lower()` de SQLite solo conoce el ASCII y «CLINICA» no es «clinica».
            existe = any(
                otro.casefold() == limpio.casefold()
                for otro in sesion.scalars(select(models.Proyecto.nombre))
            )
            if existe:
                raise ProyectoInvalido(
                    f"Ya existe un proyecto llamado «{limpio}»: elija otro nombre o abra ese."
                )
            try:
                proyecto = crear_proyecto(sesion, limpio)
                if moneda is not None:
                    declarar_moneda(sesion, proyecto, moneda, responsable=responsable)
            except ValueError as error:  # el nucleo repite las reglas; por si cambian
                raise ProyectoInvalido(str(error)) from error
            sesion.commit()
    finally:
        motor.dispose()
    return limpio


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
