"""Especialidades y módulos activables por instalación (plan vial, Tarea 19; D-V-4).

Cuatro módulos: `produccion` (la arenera y el costo propio), `vial` (tramos y su conciliación),
`edificacion` y `riesgo` (proyección e informe de mejora). Por defecto **todos están activos**: una
instalación que nunca tocó nada se comporta como siempre. Apagar un módulo es un registro nuevo
(`modulo_cambio`), no borra ningún dato de la obra: la API deja de contestarlo (404 con
`MENSAJE_APAGADO`) y el marco deja de ofrecerlo; al encenderlo todo vuelve igual.

`core/` no conoce esto: quien corta es la API (`api/acceso_modulos.py`) y quien oculta, el marco.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion.tablas_modulos import FilaModulo

MODULOS = ("produccion", "vial", "edificacion", "riesgo")
#: Cómo se nombra cada módulo ante la persona (el `<nombre>` de D-V-4).
NOMBRES = {
    "produccion": "producción",
    "vial": "vial",
    "edificacion": "edificación",
    "riesgo": "riesgo",
}
#: D-V-4, tal cual: el detalle del 404 de un módulo apagado.
MENSAJE_APAGADO = "El módulo {nombre} está apagado en esta instalación."

__all__ = [
    "MENSAJE_APAGADO",
    "MODULOS",
    "NOMBRES",
    "CambioDeModulo",
    "EstadoDeModulo",
    "ModuloDesconocido",
    "cambios_de",
    "estado_de_los_modulos",
    "fijar_modulo",
    "modulos_activos",
    "nombre_de",
]


class ModuloDesconocido(ValueError):  # noqa: N818
    """La clave no es de ningún módulo de `MODULOS`."""


@dataclass(frozen=True)
class CambioDeModulo:
    activo: bool
    usuario: str
    registrado: datetime


@dataclass(frozen=True)
class EstadoDeModulo:
    clave: str
    nombre: str
    activo: bool
    cambiado_por: str | None
    cambiado_el: datetime | None


def nombre_de(clave: str) -> str:
    try:
        return NOMBRES[clave]
    except KeyError:
        raise ModuloDesconocido(f"No existe el módulo {clave!r}.") from None


def _ultimos(sesion: Session) -> dict[str, FilaModulo]:
    """La última fila de cada clave (el orden de `id` es el del registro)."""
    ultimos: dict[str, FilaModulo] = {}
    for fila in sesion.scalars(select(FilaModulo).order_by(FilaModulo.id)):
        ultimos[fila.clave] = fila
    return ultimos


def modulos_activos(sesion: Session) -> frozenset[str]:
    """Los módulos encendidos; sin ninguna fila, todos."""
    ultimos = _ultimos(sesion)
    return frozenset(c for c in MODULOS if c not in ultimos or ultimos[c].activo)


def estado_de_los_modulos(sesion: Session) -> list[EstadoDeModulo]:
    """Los cuatro en el orden de `MODULOS`, con quién y cuándo los cambió por última vez."""
    ultimos = _ultimos(sesion)
    return [
        EstadoDeModulo(
            clave=c,
            nombre=NOMBRES[c],
            activo=ultimos[c].activo if c in ultimos else True,
            cambiado_por=ultimos[c].usuario if c in ultimos else None,
            cambiado_el=ultimos[c].registrado if c in ultimos else None,
        )
        for c in MODULOS
    ]


def fijar_modulo(
    sesion: Session, clave: str, activo: bool, *, usuario: str, ahora: datetime
) -> None:
    """Registra el cambio (una fila nueva; solo `flush`, confirma quien llama)."""
    nombre_de(clave)
    sesion.add(FilaModulo(clave=clave, activo=activo, usuario=usuario, registrado=ahora))
    sesion.flush()


def cambios_de(sesion: Session, clave: str) -> list[CambioDeModulo]:
    """Todos los cambios de un módulo, del más antiguo al más reciente."""
    nombre_de(clave)
    filas = sesion.scalars(
        select(FilaModulo).where(FilaModulo.clave == clave).order_by(FilaModulo.id)
    )
    return [CambioDeModulo(f.activo, f.usuario, f.registrado) for f in filas]
