"""La puerta de los módulos activables (plan vial, Tarea 19; D-V-4).

`requiere_modulo("vial")` es una dependencia de FastAPI para el `dependencies=[...]` de un router:
si la instalación apagó ese módulo, responde 404 con `MENSAJE_APAGADO` y la ruta no corre. No
borra nada (los datos siguen en su base) y, al encender el módulo, la misma petición vuelve a
funcionar.

Va **después** del acceso: sin sesión sigue siendo 401 y sin permiso, 403, así que el estado de los
módulos no se anuncia a quien no entró. Lee `instalacion.db` (donde vive el estado), no el caso.
`CUALQUIER_ROL` es la puerta de entrada de un router que no tiene una acción propia en el router
(el vial declara la suya en cada ruta).
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from api.dependencias import SesionInstalacionDep
from api.sesion_web import exigir_clave_o_sesion
from aplicacion.modulos import MENSAJE_APAGADO, MODULOS, NOMBRES, modulos_activos

#: Sesión de cualquier rol (o clave de API): lo que se exige antes de decir que un módulo
#: está apagado.
CUALQUIER_ROL = exigir_clave_o_sesion(None)

__all__ = ["CUALQUIER_ROL", "requiere_modulo"]


def requiere_modulo(clave: str) -> Callable[..., None]:
    """Dependencia que corta con 404 (D-V-4) si el módulo `clave` está apagado."""
    if clave not in MODULOS:
        raise ValueError(f"No existe el módulo {clave!r}.")
    detalle = MENSAJE_APAGADO.format(nombre=NOMBRES[clave])

    def dependencia(instalacion: SesionInstalacionDep) -> None:
        if clave not in modulos_activos(instalacion):
            raise HTTPException(status_code=404, detail=detalle)

    dependencia.__name__ = f"requiere_modulo_{clave}"
    return dependencia
