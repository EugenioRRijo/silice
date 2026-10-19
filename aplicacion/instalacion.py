"""Pestaña «Instalación» de Administración sin Streamlit: respaldos y eventos de seguridad perdidos
(RF-98; spec S5 §5.2 y §6.5; RM-1 de la sesión 2b).

Movido de `ui/paginas/instalacion.py`, que lo reexporta: la página clásica y
`api/rutas/admin_instalacion.py` leen lo mismo de aquí. Solo lee la carpeta de respaldos y los
archivos de eventos perdidos; lo
único que escribe es el juego de respaldo nuevo (`respaldar_todo`) y la marca «revisado».
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from operacion import config, eventos_perdidos


@dataclass(frozen=True, slots=True)
class JuegoResumen:
    nombre: str
    motivo: str
    bases: int
    carpeta: Path


@dataclass(frozen=True, slots=True)
class EventoPerdido:
    """Un archivo de eventos perdidos sin revisar: sus diferencias y cuántos eventos de acceso."""

    nombre: str
    diferencias: tuple[str, ...]
    eventos: int
    archivo: Path


def juegos_de_respaldo(entorno: Mapping[str, str] | None = None) -> list[JuegoResumen]:
    carpeta = config.carpeta_respaldos(entorno)
    if not carpeta.is_dir():
        return []
    juegos = []
    for ruta in sorted(carpeta.iterdir(), reverse=True):
        try:
            ficha = json.loads((ruta / "ficha.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        juegos.append(
            JuegoResumen(
                ruta.name, str(ficha.get("motivo", "?")), len(ficha.get("bases", [])), ruta
            )
        )
    return juegos


def zip_del_juego(carpeta: Path) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zip_:
        for archivo in sorted(p for p in carpeta.rglob("*") if p.is_file() and not p.is_symlink()):
            zip_.write(archivo, archivo.relative_to(carpeta).as_posix())
    return memoria.getvalue()


def eventos_sin_revisar(entorno: Mapping[str, str] | None = None) -> list[EventoPerdido]:
    """Los archivos de eventos perdidos pendientes, con lo que la pantalla muestra."""
    resultado = []
    for archivo in eventos_perdidos.pendientes(entorno):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        if not isinstance(datos, dict):
            datos = {}
        diferencias = datos.get("diferencias")
        lineas = []
        for dif in diferencias if isinstance(diferencias, list) else []:
            if isinstance(dif, dict):
                lineas.append(f"{dif.get('tipo')}: {dif.get('tabla')} {dif.get('etiqueta')}")
        eventos = datos.get("eventos")
        resultado.append(
            EventoPerdido(
                archivo.name,
                tuple(lineas),
                len(eventos) if isinstance(eventos, list) else 0,
                archivo,
            )
        )
    return resultado
