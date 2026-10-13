"""Lo que el administrador de la instalación hace con el asistente (S4 §3.1, §8.3), sin Streamlit.

Activar el asistente (apagado de fábrica: excepción declarada a RNF-08), elegir proveedor y modelo,
fijar el tope de costo y registrar la clave de IA de la empresa. TODO exige el rol de administrador
y registrar o cambiar la clave, además, un cliente del propio equipo (RV-15). La pestaña de
`ui/paginas/administracion.py` solo pinta y llama a estas funciones; quién es administrador lo
decide ella con la matriz de roles de S3 y lo pasa en `es_administrador`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path

from asistente.clave import ClaveDeIA, ClaveNoRegistrable
from asistente.configuracion import ConfiguracionIA, guardar, leer

AVISO_DE_NUBE = (
    "Con el modo en la nube activo, el pedido y el resumen del borrador viajan al proveedor "
    "(sin precios, montos ni nombres de proyecto, empresa o usuarios). Es una excepción declarada "
    "a la ejecución local; el modo local no envía nada fuera del equipo."
)


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
) -> ConfiguracionIA:
    """Guarda la configuración; un tope no numérico o no positivo se rechaza con `ValueError`
    y no toca el archivo."""
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


def olvidar_clave(clave: ClaveDeIA, empresa_id: str, *, es_administrador: bool) -> None:
    _exigir(es_administrador)
    clave.olvidar(empresa_id)


def cargar_clave_guardada(clave: ClaveDeIA, empresa_id: str) -> None:
    """Si el proceso arrancó sin la clave en memoria, la trae del almacén de credenciales.

    Sin permiso que exigir: no cambia nada guardado ni muestra la clave. Si no hay clave en el
    almacén (o solo existe el respaldo cifrado, que pide contraseña), no hace nada.
    """
    if clave.vigente is not None:
        return
    try:
        clave.activar(empresa_id)
    except ClaveNoRegistrable:
        return
