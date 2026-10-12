"""Proveedor guionado: reproduce turnos grabados (doble de prueba, S4 §10.1). Sin red.

Mismo guion, mismas propuestas, mismo orden, mismo registro. Guarda lo que recibe (`recibidos`)
para que las pruebas comprueben el historial y las herramientas enviadas.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from asistente.proveedores.base import (
    Disponibilidad,
    EsquemaHerramienta,
    FinTurno,
    LlamadaHerramienta,
    Mensaje,
    Turno,
    Uso,
)

ElementoDeGuion = Turno | Exception


class ProveedorGuionado:
    def __init__(
        self,
        guion: Sequence[ElementoDeGuion],
        *,
        nombre: str = "guionado",
        modelo: str = "guion-1",
        envia_fuera_del_equipo: bool = False,
    ) -> None:
        self.nombre = nombre
        self.modelo = modelo
        self.envia_fuera_del_equipo = envia_fuera_del_equipo
        self._guion = list(guion)
        self.recibidos: list[tuple[str, tuple[Mensaje, ...], tuple[EsquemaHerramienta, ...]]] = []

    def disponible(self) -> Disponibilidad:
        return Disponibilidad(True)

    def turno(
        self,
        sistema: str,
        mensajes: Sequence[Mensaje],
        herramientas: Sequence[EsquemaHerramienta],
    ) -> Turno:
        self.recibidos.append((sistema, tuple(mensajes), tuple(herramientas)))
        if not self._guion:
            raise AssertionError("el guion se agoto: el orquestador pidio un turno de mas")
        siguiente = self._guion.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


def turno_de_json(datos: Mapping[str, object]) -> Turno:
    """Un `Turno` desde su grabacion JSON (`tests/fixtures/asistente/grabaciones/*.json`)."""
    uso = datos.get("uso") or {}
    return Turno(
        texto=str(datos.get("texto", "")),
        llamadas=tuple(
            LlamadaHerramienta(str(c["id"]), str(c["nombre"]), dict(c["argumentos"]))
            for c in datos.get("llamadas", [])  # type: ignore[union-attr]
        ),
        fin=FinTurno(datos["fin"]),
        uso=Uso(**uso),  # type: ignore[arg-type]
        modelo_que_respondio=str(datos.get("modelo", "guion-1")),
    )


def guion_desde_archivo(ruta: Path) -> list[Turno]:
    return [turno_de_json(t) for t in json.loads(ruta.read_text(encoding="utf-8"))]
