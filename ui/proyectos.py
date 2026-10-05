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

Sin Streamlit y sin `ui.caso`; lo vigila `tests/unit/test_arquitectura.py`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select

from core import models
from core.budget import crear_proyecto
from core.catalog import abrir_sesion, crear_motor
from core.contracts import Severidad


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


def crear_proyecto_nuevo(ruta: Path, nombre: str) -> str:
    """Crea el proyecto y devuelve su nombre limpio. `ProyectoInvalido` si el nombre queda vacio,
    ya existe (sin distinguir mayusculas) o el caso no existe."""
    limpio = nombre.strip()
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
                crear_proyecto(sesion, limpio)
            except ValueError as error:  # el nucleo repite las dos reglas; por si cambian
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
