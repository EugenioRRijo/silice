"""Lo que el administrador de la instalación hace con el asistente (S4 §3.1, §8.3), sin Streamlit.

Activar el asistente (apagado de fábrica: excepción declarada a RNF-08), elegir proveedor y modelo,
fijar el tope de costo y registrar (o reactivar desde su respaldo cifrado) la clave de IA de la
empresa. TODO exige el rol de administrador y registrar, reactivar o cambiar la clave, además, un
cliente del propio equipo (RV-15). La pestaña de `ui/paginas/administracion.py` solo pinta y
llama a estas funciones; quién es administrador lo decide ella con la matriz de roles de S3 y lo
pasa en `es_administrador`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path

from asistente.clave import ClaveDeIA, ClaveNoRegistrable
from asistente.configuracion import ConfiguracionIA, guardar, leer
from asistente.instalacion import cargar_clave_guardada

AVISO_DE_NUBE = (
    "Con el modo en la nube activo, el pedido y el resumen del borrador viajan al proveedor "
    "(sin precios, montos ni nombres de proyecto, empresa o usuarios). Es una excepción declarada "
    "a la ejecución local; el modo local no envía nada fuera del equipo."
)


#: Los textos de la pestaña «Asistente de IA»: los muestran la clásica
#: (`ui/paginas/administracion.py`) y la interfaz nueva por `api/rutas/admin_asistente.py` (T6 de
#: la migración final); viven aquí una sola vez.
ETIQUETAS_DE_PROVEEDOR = {
    "claude": "Claude (en la nube, con la clave de la empresa)",
    "ollama": "Ollama (local, en este equipo)",
}
SIN_EXTRA_IA = (
    "Falta el componente del asistente de IA en este equipo. Instálelo con «uv sync --extra ia» "
    "y vuelva a abrir Sílice."
)
CONFIGURACION_GUARDADA = "Configuración del asistente guardada."
CONFIGURACION_NO_GUARDADA = (
    "No se pudo guardar la configuración en la carpeta de datos: revise que exista y que "
    "se pueda escribir en ella."
)
CLAVE_NO_GUARDADA = (
    "No se pudo guardar la clave: el almacén de credenciales o la carpeta de datos no "
    "responden. Pruebe de nuevo o indique una contraseña para el respaldo cifrado."
)
RESPALDO_NO_LEIDO = (
    "No se pudo leer el respaldo cifrado de la clave en la carpeta de datos: revise que "
    "exista y que se pueda leer."
)
CLAVE_OLVIDADA = "La clave de IA se olvidó: ya no está en este equipo."
#: El evento de seguridad por un intento fallido de reactivar (S3 §7.4): sin contraseña ni clave.
EVENTO_REACTIVAR_FALLIDA = "clave de ia no reactivada"
DETALLE_REACTIVAR_FALLIDA = "la contraseña no abrió el respaldo cifrado de la clave de IA"


def clave_registrada_aviso(mostrada: str) -> str:
    return f"Clave de IA registrada ({mostrada})."


def clave_reactivada_aviso(mostrada: str) -> str:
    return f"Clave de IA reactivada ({mostrada})."


class SinPermiso(PermissionError):  # noqa: N818
    """La acción es del administrador de la instalación."""


def _exigir(es_administrador: bool) -> None:
    if not es_administrador:
        raise SinPermiso("Solo el administrador de la instalación configura el asistente.")


@dataclass(frozen=True, slots=True)
class EstadoDelAsistente:
    configuracion: ConfiguracionIA
    clave_registrada: str | None  # solo los últimos 4 caracteres
    aviso: str


def estado(ruta: Path, clave: ClaveDeIA) -> EstadoDelAsistente:
    configuracion = leer(ruta)
    return EstadoDelAsistente(configuracion, clave.mostrada(), AVISO_DE_NUBE)


def _tope(texto: str) -> Decimal:
    try:
        tope = Decimal(texto.strip().replace(",", "."))
    except ArithmeticError:
        raise ValueError(
            f"El tope de costo {texto!r} no es un número: escriba, por ejemplo, 2,50."
        ) from None
    if not tope.is_finite():
        raise ValueError(f"El tope de costo {texto!r} no es un número: escriba, por ejemplo, 2,50.")
    if tope <= 0:
        raise ValueError("El tope de costo debe ser mayor que cero: escriba, por ejemplo, 2,50.")
    return tope


def configurar(
    ruta: Path,
    *,
    es_administrador: bool,
    activo: bool,
    proveedor: str,
    modelo_claude: str,
    modelo_local: str,
    anfitrion_ollama: str,
    tope_usd: str,
    clave: ClaveDeIA | None = None,
) -> ConfiguracionIA:
    """Guarda la configuración; un tope no numérico o no positivo se rechaza con `ValueError`
    y no toca el archivo.

    Al desactivar el asistente, la clave de IA sale de la memoria del proceso (§8.3); sigue en el
    almacén de credenciales y vuelve a cargarse al activarlo.
    """
    _exigir(es_administrador)
    nueva = replace(
        leer(ruta),
        activo=activo,
        proveedor=proveedor,
        modelo_claude=modelo_claude.strip(),
        modelo_local=modelo_local.strip(),
        anfitrion_ollama=anfitrion_ollama.strip(),
        tope_usd=_tope(tope_usd),
    )
    guardar(ruta, nueva)
    if not activo and clave is not None:
        clave.desactivar()
    return nueva


def registrar_clave(
    clave: ClaveDeIA,
    empresa_id: str,
    texto: str,
    *,
    es_administrador: bool,
    ip_cliente: str | None,
    contrasena_respaldo: str | None = None,
) -> str:
    """Registra la clave de IA de la empresa y devuelve lo que la pantalla puede mostrar."""
    _exigir(es_administrador)
    return clave.registrar(
        empresa_id, texto, ip_cliente=ip_cliente, contrasena_respaldo=contrasena_respaldo
    )


APAGADO_NO_REACTIVA = "Active el asistente antes de reactivar la clave de IA."


def reactivar_clave(
    clave: ClaveDeIA,
    empresa_id: str,
    contrasena: str,
    *,
    ruta: Path,
    es_administrador: bool,
    ip_cliente: str | None,
) -> str:
    """Trae la clave de IA desde su respaldo cifrado (almacén de credenciales caído) con la
    contraseña; solo el administrador, solo desde el propio equipo y solo con el asistente
    activo en la configuración de `ruta` (apagado, la clave no vuelve a la memoria, §8.3).
    Devuelve sus 4 últimos caracteres."""
    _exigir(es_administrador)
    if not leer(ruta).activo:
        raise ClaveNoRegistrable(APAGADO_NO_REACTIVA)
    return clave.reactivar(empresa_id, contrasena, ip_cliente=ip_cliente)


def olvidar_clave(clave: ClaveDeIA, empresa_id: str, *, es_administrador: bool) -> None:
    _exigir(es_administrador)
    clave.olvidar(empresa_id)


@dataclass(frozen=True, slots=True)
class VistaDeLaPestana:
    """Lo que la pestaña muestra de la clave, con el extra `ia` instalado."""

    configuracion: ConfiguracionIA
    clave_registrada: str | None  # solo los últimos 4 caracteres
    #: Hay una guardada, pero no se carga mientras el asistente esté apagado (§8.3).
    clave_guardada: bool
    #: Solo queda el respaldo cifrado: su contraseña la trae de vuelta (`reactivar_clave`).
    pide_contrasena: bool


def _sin_fallar(pregunta: Callable[[], bool]) -> bool:
    """Un almacén que falla cuenta como «no»: el backend de keyring en Windows falla de muchas
    formas y no debe tumbar la pestaña."""
    try:
        return pregunta()
    except Exception:  # noqa: BLE001
        return False


def vista_de_la_pestana(ruta: Path, clave: ClaveDeIA, empresa_id: str) -> VistaDeLaPestana:
    """Con el asistente activo trae la clave guardada a la memoria (apagado, no: §8.3) y dice qué
    mostrar: la clave enmascarada, si hay una guardada sin cargar o si solo queda el respaldo."""
    if leer(ruta).activo:
        cargar_clave_guardada(clave, empresa_id)
    visto = estado(ruta, clave)
    configuracion, registrada = visto.configuracion, visto.clave_registrada
    guardada = (
        registrada is None
        and not configuracion.activo
        and _sin_fallar(lambda: clave.hay_guardada(empresa_id))
    )
    pide = (
        registrada is None
        and configuracion.activo
        and _sin_fallar(lambda: clave.pide_contrasena(empresa_id))
    )
    return VistaDeLaPestana(configuracion, registrada, guardada, pide)
