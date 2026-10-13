"""El asistente tal como lo tiene ESTA instalacion: configuracion, clave y proveedores disponibles.

Une `operacion.config` (carpeta de datos, 0.6.0), `seguridad` (0.8.0) y los modulos del asistente.
Las importaciones de esos paquetes son diferidas: este modulo se carga sin ellos y la pantalla solo
lo usa cuando el asistente esta activo.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from asistente.clave import ClaveDeIA, almacen_del_sistema, es_bucle_local
from asistente.configuracion import NOMBRE_DEL_ARCHIVO, leer
from asistente.fabrica import Oferta, proveedores
from asistente.proveedores.ollama_local import version_a_tupla

CONFIG_IA = Path(__file__).with_name("config_ia.json")
_CLAVE: ClaveDeIA | None = None


def ruta_de_configuracion() -> Path:
    from operacion.config import carpeta_datos

    return carpeta_datos() / NOMBRE_DEL_ARCHIVO


def clave_de_la_instalacion(es_local: Callable[[str | None], bool] = es_bucle_local) -> ClaveDeIA:
    """La clave de IA de la empresa, UNA por proceso: descifrada vive solo en su memoria (§8.3).

    `es_local` decide si el cliente es del propio equipo; la pantalla de Administracion puede pasar
    `seguridad.red.es_local` (S3), que `asistente` no importa.
    """
    global _CLAVE
    if _CLAVE is None:
        from operacion.config import carpeta_datos
        from seguridad import secretos

        _CLAVE = ClaveDeIA(
            almacen=almacen_del_sistema(),
            secretos=secretos,
            ruta_respaldo=carpeta_datos() / "ia_clave.cifrada",
            es_local=es_local,
        )
    return _CLAVE


def version_minima_ollama(ruta: Path = CONFIG_IA) -> tuple[int, ...]:
    return version_a_tupla(json.loads(ruta.read_text(encoding="utf-8"))["version_minima_ollama"])


def prefijos_de_maprex() -> tuple[str, ...]:
    return leer(ruta_de_configuracion()).prefijos_de_maprex


def proveedores_de_la_instalacion() -> dict[str, Oferta]:
    """Apagado (de fabrica): sin tocar la clave, `seguridad` ni `keyring`; la pantalla no cambia."""
    configuracion = leer(ruta_de_configuracion())
    if not configuracion.activo:
        return proveedores(configuracion, None, (0,))
    return proveedores(configuracion, clave_de_la_instalacion(), version_minima_ollama())
