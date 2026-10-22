"""Primer arranque: el código de instalación y el regreso del acceso de un administrador (BCP-1).

Vive en `operacion/` y no en `aplicacion/` porque el lanzador (que nunca importa `aplicacion`) lo
llama antes de que exista la API. Tampoco importa FastAPI: la ruta (`api.rutas.primer_arranque`)
y la orden `python -m operacion restablecer-administrador` lo usan.

- `asegurar_codigo`: sin cuentas y sin `codigo_instalacion.txt`, emite un código nuevo (invalida
  los pendientes; `seguridad.cuentas.preparar_primera_vez` toma el bloqueo de escritura). Con
  cuentas, o con el archivo ya escrito, no hace nada: es idempotente. **Nunca se llama desde una
  petición**: un `GET` con efecto sería una trampa; lo llaman el lanzador y el gancho `lifespan`
  de la API.
- `emitir_restablecimiento`: un código de restablecimiento (caduca a las 24 h; cierra las sesiones
  de los administradores). Quien lo corre tiene el equipo.
- `estado`: lo único que la bienvenida puede saber antes de entrar (sin nombres ni rutas).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from operacion import config
from operacion.instalacion import cerrar_motores, sesion_de_instalacion
from seguridad import cuentas

__all__ = [
    "EstadoDeInstalacion",
    "asegurar_codigo",
    "asegurar_codigo_de_la_instalacion",
    "emitir_restablecimiento",
    "estado",
    "restablecer_administrador",
]


@dataclass(frozen=True, slots=True)
class EstadoDeInstalacion:
    sin_cuentas: bool
    archivo_presente: bool
    modo: str  # "producto" | "desarrollo"


def _archivo(carpeta: Path) -> Path:
    return carpeta / cuentas.NOMBRE_ARCHIVO_CODIGO


def asegurar_codigo(sesion: Session, carpeta: Path, ahora: datetime) -> bool:
    """True si emitió un código (no había cuentas ni archivo). Con cuentas o con el archivo
    presente no toca nada, ni siquiera el archivo de otra persona."""
    if _archivo(carpeta).is_file():
        return False
    return cuentas.preparar_primera_vez(sesion, carpeta, ahora) is not None


def emitir_restablecimiento(sesion: Session, carpeta: Path, ahora: datetime) -> tuple[str, Path]:
    """`(código, archivo)` del código de restablecimiento nuevo."""
    codigo = cuentas.emitir_codigo_de_restablecimiento(sesion, carpeta, ahora)
    return codigo, _archivo(carpeta)


def estado(sesion: Session, carpeta: Path) -> EstadoDeInstalacion:
    return EstadoDeInstalacion(
        sin_cuentas=not cuentas.hay_usuarios(sesion),
        archivo_presente=_archivo(carpeta).is_file(),
        modo="producto" if config.es_producto() else "desarrollo",
    )


def asegurar_codigo_de_la_instalacion(
    entorno: Mapping[str, str] | None = None, ahora: datetime | None = None
) -> bool:
    """`asegurar_codigo` sobre la `instalacion.db` y la carpeta de datos de `entorno` (el
    gancho del lanzador). Cierra los motores al terminar: el lanzador es un proceso largo y el
    servidor abre los suyos. El gancho `lifespan` de la API usa `asegurar_codigo` con la sesión
    del propio servidor, sin cerrar nada."""
    try:
        with sesion_de_instalacion(entorno) as sesion:
            return asegurar_codigo(sesion, config.carpeta_datos(entorno), ahora or datetime.now())
    finally:
        cerrar_motores()


def restablecer_administrador(
    entorno: Mapping[str, str] | None = None, ahora: datetime | None = None
) -> tuple[str, Path]:
    """Lo que hace `python -m operacion restablecer-administrador` (y el script): emite el código
    de restablecimiento y cierra los motores."""
    try:
        with sesion_de_instalacion(entorno) as sesion:
            return emitir_restablecimiento(
                sesion, config.carpeta_datos(entorno), ahora or datetime.now()
            )
    finally:
        cerrar_motores()
