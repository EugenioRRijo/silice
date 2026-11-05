"""Pendientes de todas las carpetas (rediseño F3, T1; spec §8 bis «Pendientes»).

Corre las fuentes de la mesa (`aplicacion.mesa.pendientes`) en cada carpeta, abierta en **solo
lectura** (`motor_solo_lectura`: sin migrar ni crear `-wal`/`-shm`) y cerrada al terminar, y une
el resultado en una sola lista con su urgencia. Sin textos ni cifras nuevos: el texto y la acción
son los de la fuente.

Urgencia por grupo (D-F3-1): «aprobar» y «compras» bloquean; «precios» y «calidad» avisan. Orden:
lo que bloquea primero; dentro de cada urgencia, la carpeta de la empresa (`None`), luego las
demás por nombre, luego el grupo en el orden de `GRUPOS` y por último el orden de cada fuente.
Las fuentes no dan fecha, así que no se inventa «lo más antiguo arriba».

Una carpeta sin archivo (la de la empresa en la demostración) no tiene pendientes: se salta sin
contarla. Una carpeta ilegible (no SQLite, sin las tablas de las fuentes o con datos que una
fuente no puede leer) se omite, se cuenta en `carpetas_omitidas` y queda en el registro; nunca
tumba la lista.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from aplicacion import mesa
from aplicacion.mesa import Siguiente
from aplicacion.proyectos import leer_cada_carpeta

__all__ = [
    "URGENCIA_DEL_GRUPO",
    "Alcance",
    "PendienteDeObra",
    "PendientesDeTodas",
    "Urgencia",
    "pendientes_de_las_carpetas",
]

_registro = logging.getLogger(__name__)

Urgencia = Literal["bloquea", "aviso"]
#: `todo`: la cuenta que edita ve todo; `por_aprobar`: la que revisa, lo que espera dictamen.
Alcance = Literal["todo", "por_aprobar"]

URGENCIA_DEL_GRUPO: dict[str, Urgencia] = {
    "aprobar": "bloquea",
    "compras": "bloquea",
    "precios": "aviso",
    "calidad": "aviso",
}
_ORDEN_DE_URGENCIA = {"bloquea": 0, "aviso": 1}
#: La página de «espera dictamen» («devuelta» abre la Hoja; «aprobada sin entregar», la entrega).
_PAGINA_POR_APROBAR = "aprobar"
_GRUPO_POR_APROBAR = "aprobar"


@dataclass(frozen=True)
class PendienteDeObra:
    """Un pendiente con su obra y su carpeta. `carpeta` es el nombre que acepta
    `POST /v1/casos/actual`; `None`, la carpeta de la empresa."""

    carpeta: str | None
    obra_id: int
    obra: str
    grupo: str
    urgencia: Urgencia
    texto: str
    accion: Siguiente


@dataclass(frozen=True)
class PendientesDeTodas:
    items: tuple[PendienteDeObra, ...]
    carpetas_omitidas: int


def pendientes_de_las_carpetas(
    carpetas: list[tuple[str | None, Path]], hoy: date, *, alcance: Alcance
) -> PendientesDeTodas:
    """Los pendientes de cada carpeta (`(nombre, ruta)`) en el orden descrito arriba. Con
    `alcance="por_aprobar"` quedan solo los de `accion.pagina == "aprobar"`."""
    items: list[PendienteDeObra] = []
    leidas, omitidas = leer_cada_carpeta(
        carpetas,
        lambda sesion: mesa.pendientes(sesion, hoy),
        registro=_registro,
        que="los pendientes",
    )
    for nombre, grupos in leidas:
        for grupo in grupos:
            urgencia = URGENCIA_DEL_GRUPO.get(grupo.clave, "aviso")
            items.extend(
                PendienteDeObra(
                    carpeta=nombre,
                    obra_id=int(p.obra),
                    obra=p.obra_nombre,
                    grupo=grupo.clave,
                    urgencia=urgencia,
                    texto=p.texto,
                    accion=p.accion,
                )
                for p in grupo.items
                if alcance == "todo"
                or (grupo.clave == _GRUPO_POR_APROBAR and p.accion.pagina == _PAGINA_POR_APROBAR)
            )
    items.sort(key=lambda i: _ORDEN_DE_URGENCIA[i.urgencia])  # estable: conserva el resto del orden
    return PendientesDeTodas(tuple(items), omitidas)
