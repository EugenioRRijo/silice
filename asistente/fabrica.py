"""Los proveedores que la instalacion tiene disponibles, y por que no el otro (S4 §3.1 9a, 9b).

Nunca cambia de proveedor en silencio (RS4-5): ofrece los que estan disponibles y dice por que no
lo esta cada uno de los demas. El modo local con un anfitrion que no resuelve a bucle local se
trata como nube (`envia_fuera_del_equipo`) y la pantalla lo avisa.
"""

from __future__ import annotations

from asistente.clave import ClaveDeIA
from asistente.configuracion import ConfiguracionIA
from asistente.proveedores.base import ProveedorIA
from asistente.proveedores.claude import ProveedorClaude
from asistente.proveedores.ollama_local import ProveedorOllama

Oferta = tuple[ProveedorIA | None, str]


def proveedores(
    configuracion: ConfiguracionIA,
    clave: ClaveDeIA | None,
    version_minima_ollama: tuple[int, ...],
    **ollama,
) -> dict[str, Oferta]:
    """`{nombre: (proveedor, "")}` si esta disponible, `{nombre: (None, motivo)}` si no.

    El asistente apagado no ofrece ninguno.
    """
    if not configuracion.activo:
        motivo = "El asistente esta apagado: lo activa el administrador de la instalacion."
        return {n: (None, motivo) for n in ("claude", "ollama")}
    ofertas: dict[str, Oferta] = {}
    claude = ProveedorClaude(
        clave.vigente if clave is not None else None, modelo=configuracion.modelo_claude
    )
    ofertas["claude"] = _oferta(claude)
    if configuracion.modelo_local:
        local = ProveedorOllama(
            configuracion.modelo_local,
            anfitrion=configuracion.anfitrion_ollama,
            version_minima=version_minima_ollama,
            **ollama,
        )
        ofertas["ollama"] = _oferta(local)
    else:
        ofertas["ollama"] = (None, "No hay un modelo local configurado.")
    return ofertas


def _oferta(proveedor: ProveedorIA) -> Oferta:
    disponibilidad = proveedor.disponible()
    return (proveedor, "") if disponibilidad.disponible else (None, disponibilidad.motivo)
