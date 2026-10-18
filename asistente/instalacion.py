"""El asistente tal como lo tiene ESTA instalacion: configuracion, clave y proveedores disponibles.

Une `operacion.config` (carpeta de datos, 0.6.0), `seguridad` (0.8.0) y los modulos del asistente.
Las importaciones de esos paquetes son diferidas: este modulo se carga sin ellos y la pantalla solo
lo usa cuando el asistente esta activo.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from asistente.clave import (
    ClaveDeIA,
    ClaveNoRegistrable,
    almacen_del_sistema,
    enmascarar,
    es_bucle_local,
)
from asistente.configuracion import NOMBRE_DEL_ARCHIVO, PROVEEDORES, leer
from asistente.fabrica import Oferta, proveedores
from asistente.proveedores.base import FALTA_EL_COMPONENTE
from asistente.proveedores.ollama_local import version_a_tupla

if TYPE_CHECKING:
    from asistente.orquestador import Topes

CONFIG_IA = Path(__file__).with_name("config_ia.json")
#: Una sola empresa propia por instalacion (S3, RV-6): bajo este id vive la clave de IA.
EMPRESA_DE_LA_CLAVE = "empresa-propia"
_registro = logging.getLogger(__name__)
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


def cargar_clave_guardada(clave: ClaveDeIA, empresa_id: str = EMPRESA_DE_LA_CLAVE) -> None:
    """Si el proceso arranco sin la clave en memoria, la trae del almacen de credenciales.

    Silenciosa: no cambia nada guardado ni muestra la clave. Sin clave en el almacen, o con solo el
    respaldo cifrado (su contrasena la pide Administracion, `reactivar`), no hace nada. Otro
    error del almacen (en Windows, el backend puede fallar de muchas formas) se anota enmascarado
    en el registro y no llega a la pantalla.
    """
    if clave.vigente is not None:
        return
    try:
        clave.activar(empresa_id)
    except ClaveNoRegistrable:
        return  # nada guardado, o solo el respaldo cifrado: es lo normal, no se anota
    except Exception as error:  # noqa: BLE001
        _registro.warning("No se pudo cargar la clave de IA guardada: %s", enmascarar(str(error)))


def version_minima_ollama(ruta: Path = CONFIG_IA) -> tuple[int, ...]:
    return version_a_tupla(json.loads(ruta.read_text(encoding="utf-8"))["version_minima_ollama"])


def prefijos_de_maprex() -> tuple[str, ...]:
    return leer(ruta_de_configuracion()).prefijos_de_maprex


def topes_de_la_instalacion() -> Topes:
    """Los topes de una sesion: los del orquestador, con el costo que fijo el administrador."""
    from asistente.orquestador import Topes

    return Topes(costo=leer(ruta_de_configuracion()).tope_usd)


def proveedor_por_defecto() -> str:
    """El proveedor que el administrador eligio por defecto (el panel lo preselecciona)."""
    return leer(ruta_de_configuracion()).proveedor


def proveedores_de_la_instalacion() -> dict[str, Oferta]:
    """Apagado (de fabrica): sin tocar la clave, `seguridad` ni `keyring`; la pantalla no cambia.

    Sin el extra `ia` (keyring, anthropic u ollama) ningun proveedor esta disponible y el motivo
    dice como instalarlo: la hoja no se cae.
    """
    configuracion = leer(ruta_de_configuracion())
    if not configuracion.activo:
        return proveedores(configuracion, None, (0,))
    try:
        clave = clave_de_la_instalacion()
        cargar_clave_guardada(clave)
        return proveedores(configuracion, clave, version_minima_ollama())
    except ImportError:
        return {n: (None, FALTA_EL_COMPONENTE) for n in PROVEEDORES}
